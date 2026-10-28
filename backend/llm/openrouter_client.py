"""OpenRouter client using the OpenAI-compatible API."""

from __future__ import annotations

import httpx

from config import get_settings
from llm.base import LLMProvider, LLMProviderError, LLMResult


class OpenRouterClient(LLMProvider):
    provider_name = "openrouter"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.default_model = self.settings.openrouter_model or "openrouter/free"

    def _select_model(self, role: str | None, model: str | None) -> str:
        if model:
            return model
        role_map = {
            "planner": self.settings.openrouter_planner_model,
            "executor": self.settings.openrouter_executor_model,
            "publisher": self.settings.openrouter_publisher_model,
            "verifier": self.settings.openrouter_verifier_model,
        }
        return role_map.get(role or "", None) or self.default_model

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
        if not self.api_key:
            raise LLMProviderError("OpenRouter API key is not configured")

        selected_model = self._select_model(role, model)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "ScholarSynth",
        }

        timeout = httpx.Timeout(self.settings.provider_timeout_seconds)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout) as client:
            try:
                if json_mode:
                    response = await client.post(
                        "/chat/completions",
                        json={**payload, "response_format": {"type": "json_object"}},
                        headers=headers,
                    )
                    if response.status_code in {400, 422}:
                        response = await client.post("/chat/completions", json=payload, headers=headers)
                else:
                    response = await client.post("/chat/completions", json=payload, headers=headers)
            except httpx.TimeoutException as exc:
                raise LLMProviderError("OpenRouter timed out", retryable=True, error_type="timeout") from exc
            except httpx.HTTPError as exc:
                raise LLMProviderError(f"OpenRouter request failed: {exc}", retryable=True, error_type="network") from exc

        if response.status_code >= 400:
            error_text = response.text[:500]
            is_quota_exhausted = any(
                phrase in error_text.lower()
                for phrase in [
                    "free-models-per-day",
                    "add 10 credits",
                    "insufficient credits",
                    "quota exceeded",
                    "exceeded your current quota",
                ]
            )
            retryable = (response.status_code in {408, 409, 425, 429} or response.status_code >= 500) and not is_quota_exhausted
            error_type = "quota_exhausted" if is_quota_exhausted else "http"
            raise LLMProviderError(
                f"OpenRouter error {response.status_code}: {error_text}",
                retryable=retryable,
                status_code=response.status_code,
                error_type=error_type,
            )

        data = response.json()
        try:
            text = data["choices"][0]["message"].get("content")
        except (KeyError, IndexError, AttributeError, TypeError) as exc:
            raise LLMProviderError("OpenRouter returned an unexpected payload", retryable=True, error_type="invalid_response") from exc

        if text is None:
            raise LLMProviderError("OpenRouter returned empty content", retryable=True, error_type="empty")

        text = str(text).strip()
        if not text:
            raise LLMProviderError("OpenRouter returned empty content", retryable=True, error_type="empty")

        return LLMResult(text=text, provider=self.provider_name, model=selected_model, raw=data)
