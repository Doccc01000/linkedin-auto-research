from typing import Any, Dict

import httpx


class BlotatoClient:
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def publish_linkedin_post(self, account_id: str, text: str) -> Dict[str, Any]:
        headers = {"blotato-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "post": {
                "accountId": account_id,
                "content": {"text": text, "platform": "linkedin"},
                "target": {"targetType": "social", "platform": "linkedin"},
            }
        }
        with httpx.Client(timeout=30) as client:
            res = client.post(f"{self.base_url}/posts", headers=headers, json=payload)
            res.raise_for_status()
            return res.json()
