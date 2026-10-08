"""An owner-configured OpenAI-compatible endpoint, never a request-supplied URL."""

import ipaddress
import json
from urllib.parse import urlsplit

import httpx


class CustomModel:
    def __init__(self):
        self.base_url = ""
        self.model = ""
        self.api_key = ""

    def configure(self, payload):
        url = payload.get("base_url", "").strip().rstrip("/")
        model = payload.get("model", "").strip()
        key = payload.get("api_key", "")
        parts = urlsplit(url)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or len(url) > 1000
            or any(ord(c) < 33 for c in url)
        ):
            raise ValueError(
                "HTTP(S) API 기본 주소를 입력하세요. 인증정보는 URL에 넣지 마세요."
            )
        try:
            parts.port
        except ValueError:
            raise ValueError("잘못된 API 포트입니다.") from None
        try:
            address = ipaddress.ip_address(parts.hostname)
        except ValueError:
            address = None
        if parts.hostname.casefold() in {"metadata.google.internal", "metadata"} or (
            address
            and (
                address.is_link_local or address.is_multicast or address.is_unspecified
            )
        ):
            raise ValueError("이 주소는 모델 연결에 사용할 수 없습니다.")
        if not model or len(model) > 240 or any(ord(c) < 32 for c in model):
            raise ValueError("서버의 모델 ID 또는 모델 경로를 입력하세요.")
        if not isinstance(key, str) or len(key) > 4096 or any(ord(c) < 32 for c in key):
            raise ValueError("잘못된 API 키입니다.")
        if payload.get("connection_consent") is not True:
            raise ValueError("해당 API 주소로 연결하는 데 동의하세요.")
        self.base_url, self.model, self.api_key = url, model, key
        return self.public()

    def public(self):
        return {"configured": bool(self.base_url), "model": self.model}

    def settings(self):
        return {
            **self.public(),
            "base_url": self.base_url,
            "has_key": bool(self.api_key),
        }

    def headers(self):
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def models(self):
        if not self.base_url:
            raise ValueError("모델 서버를 먼저 연결하세요.")
        try:
            with httpx.Client(
                timeout=10, follow_redirects=False, trust_env=False
            ) as client:
                response = client.get(self.base_url + "/models", headers=self.headers())
                response.raise_for_status()
                if len(response.content) > 2_000_000:
                    raise ValueError("Oversized model list")
                data = response.json()
                names = [
                    row["id"] for row in data["data"] if isinstance(row.get("id"), str)
                ]
                return {"models": names[:200]}
        except Exception:
            raise ValueError(
                "모델 목록 요청 실패. 주소·API 규격·인증을 확인하세요."
            ) from None

    async def analyze(self, model, prompt, data):
        if not self.base_url:
            raise ValueError("Custom endpoint missing")
        async with httpx.AsyncClient(
            timeout=120, follow_redirects=False, trust_env=False
        ) as client:
            response = await client.post(
                self.base_url + "/chat/completions",
                headers=self.headers(),
                json={
                    "model": model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {
                            "role": "user",
                            "content": json.dumps(data, ensure_ascii=False),
                        },
                    ],
                },
            )
            response.raise_for_status()
            if len(response.content) > 2_000_000:
                raise ValueError("Oversized model response")
            result = response.json()
        content = result["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("Text response required")
        return {"text": content, "usage": result.get("usage", {}), "model": model}
