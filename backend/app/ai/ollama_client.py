from __future__ import annotations

from typing import Any

import httpx

from app.core import settings


class IncompleteOllamaResponse(ValueError):
    pass


class InvalidOllamaResponse(ValueError):
    pass


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
        num_predict: int = 256,
        schema: dict[str, Any] | None = None,
        num_ctx: int = 4096,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": schema if schema is not None else "json",
            "options": {"temperature": 0, "num_predict": num_predict, "num_ctx": num_ctx},
        }

        if schema is not None and self.model.split(":")[0].lower() in ("qwen3", "deepseek-r1"):
            payload["think"] = False

        if system:
            payload["system"] = system

        response = httpx.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )

        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as exc:
            raise InvalidOllamaResponse("Ollama returned a non-JSON response envelope.") from exc
        if not isinstance(data, dict):
            raise InvalidOllamaResponse("Ollama response envelope must be an object.")

        if data.get("done") is False or data.get("done_reason") == "length":
            raise IncompleteOllamaResponse("Ollama generation was incomplete or reached the output token limit.")
        value = data.get("response")
        if not isinstance(value, str):
            raise InvalidOllamaResponse("Ollama response must contain text.")
        return value.strip()
