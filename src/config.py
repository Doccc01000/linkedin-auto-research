import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(ROOT_DIR / ".env")


@dataclass
class Settings:
    app_timezone: str = os.getenv("APP_TIMEZONE", "Europe/Paris")
    dry_run: bool = os.getenv("DRY_RUN", "true").lower() == "true"
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    notion_api_token: str = os.getenv("NOTION_API_TOKEN", "")
    notion_lead_magnet_db_id: str = os.getenv("NOTION_LEAD_MAGNET_DB_ID", "")
    notion_runs_db_id: str = os.getenv("NOTION_RUNS_DB_ID", "")

    blotato_api_key: str = os.getenv("BLOTATO_API_KEY", "")
    blotato_account_id: str = os.getenv("BLOTATO_ACCOUNT_ID", "")
    blotato_base_url: str = os.getenv("BLOTATO_BASE_URL", "https://backend.blotato.com/v2")

    apify_api_token: str = os.getenv("APIFY_API_TOKEN", "")
    apify_actor_id_linkedin_metrics: str = os.getenv("APIFY_ACTOR_ID_LINKEDIN_METRICS", "")
    linkedin_profile_url: str = os.getenv("LINKEDIN_PROFILE_URL", "")
    linkedin_profile_posts_url: str = os.getenv("LINKEDIN_PROFILE_POSTS_URL", "")


SETTINGS = Settings()
