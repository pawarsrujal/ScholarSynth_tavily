"""Groq client using the OpenAI-compatible API."""

from __future__ import annotations

import httpx

from config import get_settings
from llm.base import LLMProvider, LLMProviderError, LLMResult


class GroqClient(LLMProvider):
    provider_name = "groq"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.groq_api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.default_model = self.settings.groq_model or "openai/gpt-oss-20b"

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
            raise LLMProviderError("Groq API key is not configured")

        primary_model = model or self.default_model
        candidate_models = [primary_model]
        for alt in ("openai/gpt-oss-120b", "openai/gpt-oss-20b"):
            if alt not in candidate_models:
                candidate_models.append(alt)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(self.settings.provider_timeout_seconds)

        last_error_response: httpx.Response | None = None
        used_model = primary_model

        async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout) as client:
            for cand_model in candidate_models:
                used_model = cand_model
                payload = {
                    "model": cand_model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if max_tokens is not None:
                    payload["max_tokens"] = max_tokens

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
                    raise LLMProviderError("Groq timed out", retryable=True, error_type="timeout") from exc
                except httpx.HTTPError as exc:
                    raise LLMProviderError(f"Groq request failed: {exc}", retryable=True, error_type="network") from exc

                if response.status_code == 429 and cand_model != candidate_models[-1]:
                    last_error_response = response
                    continue
                break

        if response.status_code >= 400:
            retryable = response.status_code in {408, 409, 425, 429} or response.status_code >= 500
            raise LLMProviderError(
                f"Groq error {response.status_code}: {response.text[:500]}",
                retryable=retryable,
                status_code=response.status_code,
                error_type="http",
            )

        data = response.json()
        try:
            text = data["choices"][0]["message"].get("content")
        except (KeyError, IndexError, AttributeError, TypeError) as exc:
            raise LLMProviderError("Groq returned an unexpected payload", retryable=True, error_type="invalid_response") from exc

        if text is None:
            raise LLMProviderError("Groq returned empty content", retryable=True, error_type="empty")

        text = str(text).strip()
        if not text:
            raise LLMProviderError("Groq returned empty content", retryable=True, error_type="empty")

        return LLMResult(text=text, provider=self.provider_name, model=used_model, raw=data)
