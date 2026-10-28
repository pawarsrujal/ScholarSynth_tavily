"""Gemini fallback provider kept for compatibility."""

from __future__ import annotations

import asyncio
from typing import Any

import google.generativeai as genai

from config import get_settings
from llm.base import LLMProvider, LLMProviderError, LLMResult


class GeminiClient(LLMProvider):
    provider_name = "gemini"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.gemini_api_key
        self.default_model = self.settings.gemini_model
        self._configured = False

    def _ensure_configured(self) -> None:
        if not self.api_key:
            raise LLMProviderError("Gemini API key is not configured")
        if not self._configured:
            genai.configure(api_key=self.api_key)
            self._configured = True

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        json_mode: bool = False,
        role: str | None = None,
    ) -> LLMResult:
        self._ensure_configured()
        selected_model = model or self.default_model

        def _call() -> Any:
            generation_config: dict[str, Any] = {
                "temperature": temperature,
                "top_p": 0.95,
                "top_k": 40,
            }
            if max_tokens is not None:
                generation_config["max_output_tokens"] = max_tokens
            if json_mode:
                generation_config["response_mime_type"] = "application/json"

            gemini_model = genai.GenerativeModel(
                model_name=selected_model,
                system_instruction=system_prompt,
            )
            response = gemini_model.generate_content(prompt, generation_config=generation_config)
            return response

        try:
            response = await asyncio.to_thread(_call)
        except Exception as exc:  # pragma: no cover - provider specific
            exc_str = str(exc)
            is_quota = (
                "quota" in exc_str.lower()
                or "resourceexhausted" in exc_str.lower()
                or "exceeded your current quota" in exc_str.lower()
                or "free_tier_requests" in exc_str.lower()
            )
            raise LLMProviderError(
                f"Gemini request failed: {exc}",
                retryable=not is_quota,
                error_type="quota_exhausted" if is_quota else "provider",
            ) from exc

        text = getattr(response, "text", None)
        if text is None:
            raise LLMProviderError("Gemini returned an empty response", retryable=True, error_type="empty")

        text = str(text).strip()
        if not text:
            raise LLMProviderError("Gemini returned an empty response", retryable=True, error_type="empty")

        return LLMResult(text=text, provider=self.provider_name, model=selected_model, raw={"text": text})
