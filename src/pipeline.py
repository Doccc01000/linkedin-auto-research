from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from apify_client import ApifyClient, ApifySyncTimeoutError
from blotato_client import BlotatoClient
from config import ROOT_DIR, SETTINGS
from content_generator import generate_content
from notion_client import NotionAPIError, NotionClient
from utils import append_jsonl, sha256_text, utc_now_iso, write_json


ARTIFACTS_DIR = ROOT_DIR / "artifacts"
REPORTS_DIR = ROOT_DIR / "reports"
LOCAL_RUNS_FILE = ARTIFACTS_DIR / "content_runs.jsonl"
LOCAL_METRICS_FILE = ARTIFACTS_DIR / "linkedin_metrics.jsonl"


def _build_asset_markdown(content: Dict[str, Any]) -> str:
    asset = content["asset"]
    sections = []
    for sec in asset.get("sections", []):
        bullets = "\n".join([f"- {b}" for b in sec.get("bullets", [])])
        sections.append(f"## {sec.get('heading')}\n{bullets}")
    return (
        f"# {asset.get('title')}\n\n"
        f"{asset.get('subtitle')}\n\n"
        f"**Outcome:** {asset.get('outcome')}\n\n"
        + "\n\n".join(sections)
        + f"\n\n---\nCTA keyword: **{asset.get('cta_keyword')}**"
    )


def _build_linkedin_text(content: Dict[str, Any]) -> str:
    post = content["linkedin_post"]
    hashtags = " ".join(post.get("hashtags", []))
    paragraphs = "\n\n".join(post.get("body_paragraphs", []))
    return f"{post.get('hook')}\n\n{paragraphs}\n\n{post.get('cta')}\n\n{hashtags}".strip()


def _notion_rich_text(value: str) -> Dict[str, Any]:
    return {"rich_text": [{"text": {"content": value[:1900]}}]}


def _normalize(text: str) -> str:
    return "".join(ch.lower() for ch in text if ch.isalnum())


def _find_property_name(schema: Dict[str, Dict[str, Any]], aliases: List[str], prop_type: str) -> str:
    normalized_aliases = [_normalize(a) for a in aliases]
    for prop_name, conf in schema.items():
        if conf.get("type") == prop_type and _normalize(prop_name) in normalized_aliases:
            return prop_name
    for prop_name, conf in schema.items():
        if conf.get("type") == prop_type:
            return prop_name
    return ""


def _title_prop(value: str) -> Dict[str, Any]:
    return {"title": [{"text": {"content": value[:120]}}]}


def _build_notion_properties(schema: Dict[str, Dict[str, Any]], values: Dict[str, str]) -> Dict[str, Any]:
    properties: Dict[str, Any] = {}

    title_name = _find_property_name(schema, ["name", "title", "nom"], "title")
    if title_name:
        title_value = values.get("title", "Untitled")
        properties[title_name] = _title_prop(title_value)

    for semantic_key, aliases in {
        "type": ["type", "asset type", "content type", "format"],
        "status": ["status", "statut"],
        "cta_keyword": ["cta keyword", "keyword", "mot cle", "mot-clé"],
    }.items():
        value = values.get(semantic_key, "")
        if not value:
            continue
        select_name = _find_property_name(schema, aliases, "select")
        if select_name:
            properties[select_name] = {"select": {"name": value[:100]}}

    for semantic_key, aliases in {
        "asset_title": ["asset title", "lead magnet title", "titre asset"],
        "linkedin_post": ["linkedin post", "post", "post linkedin"],
        "topic": ["topic", "angle", "sujet"],
        "cta_keyword_text": ["cta keyword", "keyword", "mot cle", "mot-clé"],
    }.items():
        value = values.get(semantic_key, "")
        if not value:
            continue
        rich_name = _find_property_name(schema, aliases, "rich_text")
        if rich_name and rich_name not in properties:
            properties[rich_name] = _notion_rich_text(value)

    return properties


def _create_notion_pages(notion: NotionClient, content: Dict[str, Any], linkedin_text: str) -> Dict[str, str]:
    if not notion.enabled or not SETTINGS.notion_lead_magnet_db_id or not SETTINGS.notion_runs_db_id:
        return {"asset_page_url": "", "run_page_url": ""}

    asset = content["asset"]
    asset_md = _build_asset_markdown(content)
    try:
        lead_schema = notion.get_database_properties(SETTINGS.notion_lead_magnet_db_id)
        run_schema = notion.get_database_properties(SETTINGS.notion_runs_db_id)

        lead_properties = _build_notion_properties(
            lead_schema,
            {
                "title": asset.get("title", "Lead Magnet"),
                "type": asset.get("type", ""),
                "cta_keyword": asset.get("cta_keyword", ""),
                "cta_keyword_text": asset.get("cta_keyword", ""),
            },
        )

        run_properties = _build_notion_properties(
            run_schema,
            {
                "title": f"Run {datetime.utcnow().date().isoformat()}",
                "status": "published" if not SETTINGS.dry_run else "draft",
                "asset_title": asset.get("title", ""),
                "linkedin_post": linkedin_text,
                "topic": str(content.get("metadata", {}).get("topic", "")),
            },
        )

        if not lead_properties or not run_properties:
            raise NotionAPIError("No compatible Notion properties found in one of the target databases.")

        asset_page = notion.create_page(
            SETTINGS.notion_lead_magnet_db_id,
            properties=lead_properties,
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": asset_md[:1900]}}]},
                }
            ],
        )
        notion_run = notion.create_page(
            SETTINGS.notion_runs_db_id,
            properties=run_properties,
        )
        return {"asset_page_url": asset_page.get("url", ""), "run_page_url": notion_run.get("url", "")}
    except Exception as exc:
        return {"asset_page_url": "", "run_page_url": "", "error": str(exc)}


def run_daily() -> Dict[str, Any]:
    content = generate_content()
    linkedin_text = _build_linkedin_text(content)
    asset_md = _build_asset_markdown(content)
    now = utc_now_iso()
    content_hash = sha256_text(linkedin_text + asset_md)

    post_submission: Dict[str, Any] = {}
    blotato = BlotatoClient(SETTINGS.blotato_api_key, SETTINGS.blotato_base_url)
    if blotato.enabled and SETTINGS.blotato_account_id and not SETTINGS.dry_run:
        try:
            post_submission = blotato.publish_linkedin_post(SETTINGS.blotato_account_id, linkedin_text)
        except Exception as exc:
            post_submission = {"error": str(exc)}
    else:
        post_submission = {"skipped": "missing_credentials_or_dry_run"}

    notion = NotionClient(SETTINGS.notion_api_token)
    notion_refs = _create_notion_pages(notion, content, linkedin_text)

    run_record = {
        "run_at": now,
        "content_hash": content_hash,
        "dry_run": SETTINGS.dry_run,
        "asset": content["asset"],
        "linkedin_post": content["linkedin_post"],
        "metadata": content.get("metadata", {}),
        "blotato": post_submission,
        "notion": notion_refs,
    }
    append_jsonl(LOCAL_RUNS_FILE, run_record)
    write_json(ARTIFACTS_DIR / f"daily_run_{datetime.utcnow().date().isoformat()}.json", run_record)
    (REPORTS_DIR / f"lead-magnet-{datetime.utcnow().date().isoformat()}.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / f"lead-magnet-{datetime.utcnow().date().isoformat()}.md").write_text(asset_md, encoding="utf-8")
    return run_record


def _extract_features_from_post(text: str) -> Dict[str, Any]:
    words = text.split()
    word_count = len(words)
    if word_count < 120:
        length_bucket = "short"
    elif word_count < 220:
        length_bucket = "medium"
    else:
        length_bucket = "long"
    hook_line = text.splitlines()[0] if text else ""
    hook_type = "question" if "?" in hook_line else "statement"
    hashtags = [token.strip(".,!?:;") for token in text.split() if token.startswith("#")]
    return {
        "word_count": word_count,
        "length_bucket": length_bucket,
        "hook_type": hook_type,
        "hashtags": hashtags,
        "hashtag_count": len(hashtags),
    }


def _score_post(item: Dict[str, Any]) -> float:
    # Actor payload does not include impressions in this response shape,
    # so we use an absolute weighted engagement score.
    reactions = int(item.get("reactions", 0) or 0)
    comments = int(item.get("comments", 0) or 0)
    shares = int(item.get("shares", 0) or 0)
    return round((1 * reactions) + (2 * comments) + (3 * shares), 5)


def _summarize_patterns(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_hook: Dict[str, List[float]] = {}
    by_length: Dict[str, List[float]] = {}
    for row in rows:
        features = row.get("features", {})
        score = row.get("score", 0.0)
        by_hook.setdefault(features.get("hook_type", "unknown"), []).append(score)
        by_length.setdefault(features.get("length_bucket", "unknown"), []).append(score)
    def _avg(values: List[float]) -> float:
        return round(sum(values) / len(values), 5) if values else 0.0
    return {
        "hook_performance": {k: _avg(v) for k, v in by_hook.items()},
        "length_performance": {k: _avg(v) for k, v in by_length.items()},
    }


def run_weekly() -> Dict[str, Any]:
    apify = ApifyClient(SETTINGS.apify_api_token)
    raw_metrics: List[Dict[str, Any]] = []
    if apify.enabled and SETTINGS.apify_actor_id_linkedin_metrics and SETTINGS.linkedin_profile_url:
        try:
            raw_metrics = apify.scrape_linkedin_metrics(
                SETTINGS.apify_actor_id_linkedin_metrics,
                [SETTINGS.linkedin_profile_url],
                timeout_seconds=280,
                limit=100,
                fields=["full_urn", "posted_at", "text", "url", "post_type", "stats", "author"],
            )
        except ApifySyncTimeoutError as exc:
            raw_metrics = [{"error": str(exc), "hint": "Consider async Apify run for long executions."}]
        except Exception as exc:
            raw_metrics = [{"error": str(exc)}]
    else:
        raw_metrics = [{"skipped": "missing_apify_credentials"}]

    enriched: List[Dict[str, Any]] = []
    for item in raw_metrics:
        text = str(item.get("text", ""))
        stats = item.get("stats") or {}
        posted_at = item.get("posted_at") or {}
        author = item.get("author") or {}
        row = {
            "captured_at": utc_now_iso(),
            "post_id": item.get("full_urn") or "",
            "post_url": item.get("url") or "",
            "post_type": item.get("post_type") or "unknown",
            "posted_at_ts": posted_at.get("timestamp"),
            "posted_at_date": posted_at.get("date"),
            "author_username": author.get("username", ""),
            "text": text,
            "impressions": 0,
            "reactions": stats.get("total_reactions", 0),
            "comments": stats.get("comments", 0),
            "shares": stats.get("reposts", 0),
        }
        row["features"] = _extract_features_from_post(text)
        row["score"] = _score_post(row)
        enriched.append(row)
        append_jsonl(LOCAL_METRICS_FILE, row)

    patterns = _summarize_patterns(enriched)
    strategy = {
        "week_generated_at": utc_now_iso(),
        "posts_analyzed": len(enriched),
        "patterns": patterns,
        "recommendations": [
            "Use top-performing hook type at least 2 times next week.",
            "Keep one post as experimentation slot with a different format/angle.",
            "Reuse highest-performing length bucket as your default baseline.",
        ],
    }
    report_path = REPORTS_DIR / f"weekly-strategy-{datetime.utcnow().date().isoformat()}.json"
    write_json(report_path, strategy)
    return strategy
