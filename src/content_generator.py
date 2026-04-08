import json
import random
from typing import Any, Dict, List

import httpx

from config import ROOT_DIR, SETTINGS


def _read_examples() -> List[str]:
    ex_dir = ROOT_DIR / "example"
    posts = []
    for file_path in sorted(ex_dir.glob("*.md")):
        posts.append(file_path.read_text(encoding="utf-8").strip())
    return posts


def _build_prompt(audience: str, examples: List[str]) -> str:
    examples_block = "\n\n".join([f"[Example {i+1}]\n{txt}" for i, txt in enumerate(examples)])
    lead_type = random.choice(["guide", "framework", "prompt_pack"])
    topic = random.choice(
        [
            "US LLC vs UK LTD decision",
            "compliance checklist for non-residents",
            "bank account readiness",
            "launch in 7 days without surprises",
        ]
    )
    return f"""
You are a LinkedIn content strategist for non-resident founders.

Audience:
{audience}

Reference style signals (do not copy):
{examples_block}

Create exactly one lead magnet and one LinkedIn post.
Lead magnet type: {lead_type}
Topic: {topic}

Output valid JSON with keys:
- asset: type,title,subtitle,outcome,sections(list of heading+bullets),cta_keyword
- linkedin_post: hook,body_paragraphs(list),cta,hashtags(list)
- metadata: angle,topic,length_bucket
"""


def _fallback_content() -> Dict[str, Any]:
    return {
        "asset": {
            "type": "framework",
            "title": "US LLC vs UK LTD Decision Framework",
            "subtitle": "A practical path for non-resident founders",
            "outcome": "Pick the right structure and launch in days with fewer mistakes.",
            "sections": [
                {"heading": "Step 1 - Revenue model fit", "bullets": ["B2B invoices", "Marketplace constraints", "Banking compatibility"]},
                {"heading": "Step 2 - Compliance readiness", "bullets": ["State obligations", "Tax calendar", "Bookkeeping workflow"]},
                {"heading": "Step 3 - Launch checklist", "bullets": ["Formation docs", "Tax IDs", "Bank account application"]},
            ],
            "cta_keyword": "FRAMEWORK",
        },
        "linkedin_post": {
            "hook": "Most founders don’t fail on strategy. They fail on setup friction.",
            "body_paragraphs": [
                "If you are a non-resident founder, choosing US LLC vs UK LTD is less about hype and more about operations.",
                "Your structure impacts invoicing, banking approval, and compliance workload from day one.",
                "I built a practical framework to help you decide in under 30 minutes, without legal jargon.",
            ],
            "cta": "Comment FRAMEWORK and I will send it.",
            "hashtags": ["#GlobalFounders", "#USLLC", "#UKLTD", "#StartupOps", "#InternationalBusiness"],
        },
        "metadata": {"angle": "educational", "topic": "entity setup", "length_bucket": "900-1400"},
    }


def generate_content() -> Dict[str, Any]:
    audience = (ROOT_DIR / "audience-info.md").read_text(encoding="utf-8")
    examples = _read_examples()
    api_key = SETTINGS.anthropic_api_key
    if not api_key:
        return _fallback_content()

    prompt = _build_prompt(audience, examples)
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": SETTINGS.anthropic_model,
        "max_tokens": 1800,
        "temperature": 0.8,
        "system": "Return valid JSON only. No markdown fences.",
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        with httpx.Client(timeout=45) as client:
            res = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            res.raise_for_status()
            content = res.json().get("content", [])
            text = ""
            if isinstance(content, list) and content:
                text = str(content[0].get("text", ""))
            text = text.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.lower().startswith("json"):
                    text = text[4:].strip()
            return json.loads(text)
    except Exception:
        return _fallback_content()
