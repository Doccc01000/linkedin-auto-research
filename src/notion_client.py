from typing import Any, Dict, Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class NotionAPIError(Exception):
    pass


class NotionClient:
    def __init__(self, api_token: str, notion_version: str = "2022-06-28") -> None:
        self.api_token = api_token
        self.notion_version = notion_version
        self.base_url = "https://api.notion.com/v1"

    @property
    def enabled(self) -> bool:
        return bool(self.api_token)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Notion-Version": self.notion_version,
            "Content-Type": "application/json",
        }

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _post(self, endpoint: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        with httpx.Client(timeout=30) as client:
            res = client.post(f"{self.base_url}{endpoint}", headers=self._headers(), json=payload, timeout=timeout)
            try:
                res.raise_for_status()
            except httpx.HTTPStatusError as exc:
                body = res.text[:1200]
                raise NotionAPIError(f"Notion POST {endpoint} failed ({res.status_code}): {body}") from exc
            return res.json()

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _get(self, endpoint: str, timeout: int = 30) -> Dict[str, Any]:
        with httpx.Client(timeout=timeout) as client:
            res = client.get(f"{self.base_url}{endpoint}", headers=self._headers())
            try:
                res.raise_for_status()
            except httpx.HTTPStatusError as exc:
                body = res.text[:1200]
                raise NotionAPIError(f"Notion GET {endpoint} failed ({res.status_code}): {body}") from exc
            return res.json()

    def get_database_properties(self, database_id: str) -> Dict[str, Dict[str, Any]]:
        data = self._get(f"/databases/{database_id}")
        props = data.get("properties", {})
        if isinstance(props, dict):
            return props
        return {}

    def create_page(self, database_id: str, properties: Dict[str, Any], children: Optional[list] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"parent": {"database_id": database_id}, "properties": properties}
        if children:
            payload["children"] = children
        return self._post("/pages", payload)
