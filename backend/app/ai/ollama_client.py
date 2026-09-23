from __future__ import annotations

from typing import Any

import httpx

from app.core import settings


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (
            base_url
            or getattr(
                settings,
                "OLLAMA_BASE_URL",
                "http://localhost:11434",
            )
        ).rstrip("/")

        self.model = (
            model
            or getattr(
                settings,
                "OLLAMA_MODEL",
                "gemma3:4b",
            )
        )

        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0, "num_predict": 256, "num_ctx": 4096},
        }

        if system:
            payload["system"] = system

        response = httpx.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("done") is False:
            raise ValueError("Ollama response was incomplete.")
        value = data.get("response")
        if not isinstance(value, str):
            raise ValueError("Ollama response must contain text.")
        return value.strip()
