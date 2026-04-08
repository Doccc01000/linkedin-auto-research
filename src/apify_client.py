from typing import Any, Dict, List, Optional

import httpx


class ApifySyncTimeoutError(Exception):
    pass


class ApifyClient:
    def __init__(self, api_token: str) -> None:
        self.api_token = api_token
        self.base_url = "https://api.apify.com/v2"

    @property
    def enabled(self) -> bool:
        return bool(self.api_token)

    def scrape_linkedin_metrics(
        self,
        actor_id: str,
        profile_urls: List[str],
        timeout_seconds: int = 280,
        limit: int = 100,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        payload = {"profileUrls": profile_urls, "maxItems": limit}
        params: Dict[str, Any] = {
            "timeout": timeout_seconds,
            "format": "json",
            "clean": "1",
            "limit": limit,
        }
        if fields:
            params["fields"] = ",".join(fields)
        # Keep client timeout above Apify endpoint timeout to avoid local premature disconnect.
        with httpx.Client(timeout=timeout_seconds + 30) as client:
            run = client.post(
                f"{self.base_url}/acts/{actor_id}/run-sync-get-dataset-items",
                headers=headers,
                params=params,
                json=payload,
            )
            if run.status_code == 408:
                raise ApifySyncTimeoutError(
                    "Apify sync run exceeded endpoint timeout (408). Use fewer inputs or async run."
                )
            run.raise_for_status()
            data = run.json()
        if isinstance(data, list):
            return data
        return []
