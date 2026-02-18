import os
from typing import List

import httpx


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str | None = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.base_url = base_url or os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is required for Gemini provider")

    async def chat(self, messages: List[dict]) -> str:
        system_parts: list[str] = []
        contents: list[dict] = []

        for message in messages:
            text = (message.get("content") or "").strip()
            if not text:
                continue

            role = message.get("role", "user")
            if role == "system":
                system_parts.append(text)
                continue

            gemini_role = "user" if role == "user" else "model"
            contents.append({"role": gemini_role, "parts": [{"text": text}]})

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 800,
            },
        }

        if system_parts:
            payload["system_instruction"] = {"parts": [{"text": "\n".join(system_parts)}]}

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates") if isinstance(data, dict) else None
        if candidates and len(candidates) > 0:
            parts = candidates[0].get("content", {}).get("parts", [])
            texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
            return "".join(texts).strip()

        return ""