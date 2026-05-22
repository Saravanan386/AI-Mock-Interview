import json
from typing import Any

import httpx

from app.config import settings


class LLMService:
    def __init__(self) -> None:
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model

    async def generate_text(self, prompt: str, fallback: str) -> str:
        if not settings.llm_enabled:
            if settings.strict_ai_mode:
                raise RuntimeError("LLM is disabled while strict AI mode is enabled")
            return fallback

        url = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a precise recruitment AI assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception:
            if settings.strict_ai_mode:
                raise
            return fallback

    async def generate_json(self, prompt: str, fallback: Any) -> Any:
        text = await self.generate_text(prompt, fallback=json.dumps(fallback))
        try:
            return json.loads(_extract_json(text))
        except json.JSONDecodeError:
            if settings.strict_ai_mode:
                raise
            return fallback


def _extract_json(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.removeprefix("json").strip()
    start_array = stripped.find("[")
    start_object = stripped.find("{")
    starts = [index for index in [start_array, start_object] if index >= 0]
    if not starts:
        return stripped
    start = min(starts)
    end = max(stripped.rfind("]"), stripped.rfind("}"))
    return stripped[start : end + 1]


llm_service = LLMService()
