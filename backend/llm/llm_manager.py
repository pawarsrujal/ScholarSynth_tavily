"""Central LLM fallback manager for ScholarSynth."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from config import get_settings
from llm.base import LLMProviderError, LLMResult
from llm.gemini_client import GeminiClient
from llm.groq_client import GroqClient
from llm.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)


class LLMManager:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.providers = [GroqClient(), GeminiClient(), OpenRouterClient()]
        self.disabled_providers: set[str] = set()

    def _model_for_provider(self, provider_name: str, role: str | None, model: str | None) -> str | None:
        if model:
            return model
        if provider_name == "openrouter":
            role_models = {
                "planner": self.settings.openrouter_planner_model,
                "executor": self.settings.openrouter_executor_model,
                "publisher": self.settings.openrouter_publisher_model,
                "verifier": self.settings.openrouter_verifier_model,
            }
            return role_models.get(role or "") or self.settings.openrouter_model
        if provider_name == "groq":
            return self.settings.groq_model or "openai/gpt-oss-20b"
        if provider_name == "gemini":
            return self.settings.gemini_model or "gemini-3.6-flash"
        return None

    def _strict_system_prompt(self, system_prompt: str | None) -> str:
        base = (system_prompt or "").strip()
        extra = (
            "Return ONLY valid JSON. Do not use markdown fences. "
            "Do not include commentary. Return exactly one JSON object."
        )
        return f"{base}\n\n{extra}".strip()

    def _extract_retry_delay(self, error_str: str) -> float | None:
        match = re.search(r"(?:retry in|try again in|seconds:\s*)(\d+(?:\.\d+)?)", error_str, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None

    def _log_request(self, provider_name: str, model: str | None, role: str | None, attempt: int) -> None:
        logger.info(
            "[LLM] provider=%s model=%s role=%s attempt=%s",
            provider_name,
            model or "auto",
            role or "generic",
            attempt,
        )

    def parse_json_response(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")
        while start != -1:
            depth = 0
            in_string = False
            escape = False
            for index in range(start, len(cleaned)):
                char = cleaned[index]
                if in_string:
                    if escape:
                        escape = False
                    elif char == "\\":
                        escape = True
                    elif char == '"':
                        in_string = False
                    continue
                if char == '"':
                    in_string = True
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = cleaned[start : index + 1]
                        return json.loads(candidate)
            start = cleaned.find("{", start + 1)

        raise json.JSONDecodeError("No valid JSON object found", cleaned, 0)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        role: str | None = None,
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResult:
        last_error: Exception | None = None

        for provider in self.providers:
            if provider.provider_name in self.disabled_providers:
                continue
            if provider.provider_name == "openrouter" and not self.settings.openrouter_api_key:
                continue
            if provider.provider_name == "groq" and not self.settings.groq_api_key:
                continue
            if provider.provider_name == "gemini" and not self.settings.gemini_api_key:
                continue

            provider_model = self._model_for_provider(provider.provider_name, role, model)

            for attempt in range(1, self.settings.provider_retries + 2):
                try:
                    self._log_request(provider.provider_name, provider_model, role, attempt)
                    result = await provider.generate(
                        prompt,
                        system_prompt=system_prompt,
                        model=provider_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        json_mode=json_mode,
                        role=role,
                    )
                    return result
                except LLMProviderError as exc:
                    last_error = exc
                    logger.warning(
                        "[LLM] provider=%s model=%s role=%s attempt=%s retryable=%s status=%s error=%s",
                        provider.provider_name,
                        provider_model or "auto",
                        role or "generic",
                        attempt,
                        exc.retryable,
                        exc.status_code,
                        exc,
                    )
                    if exc.error_type == "quota_exhausted" or ("quota" in str(exc).lower() and not exc.retryable):
                        self.disabled_providers.add(provider.provider_name)
                        logger.warning("[LLM] Disabling provider %s due to quota exhaustion", provider.provider_name)
                        break
                    if not exc.retryable or attempt >= self.settings.provider_retries + 1:
                        break
                    delay = self._extract_retry_delay(str(exc)) or min(2 ** (attempt - 1), 4)
                    await asyncio.sleep(min(delay, 20))

        raise LLMProviderError(f"All LLM providers failed: {last_error}") if last_error else LLMProviderError(
            "No LLM providers are configured"
        )

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        role: str | None = None,
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        strict_prompt = self._strict_system_prompt(system_prompt)

        for provider in self.providers:
            if provider.provider_name in self.disabled_providers:
                continue
            if provider.provider_name == "openrouter" and not self.settings.openrouter_api_key:
                continue
            if provider.provider_name == "groq" and not self.settings.groq_api_key:
                continue
            if provider.provider_name == "gemini" and not self.settings.gemini_api_key:
                continue

            provider_model = self._model_for_provider(provider.provider_name, role, model)

            provider_attempts = [True, False] if provider.provider_name == "openrouter" else [True]
            provider_break = False
            for json_mode in provider_attempts:
                if provider_break:
                    break
                for attempt in range(1, self.settings.provider_retries + 2):
                    try:
                        self._log_request(provider.provider_name, provider_model, role, attempt)
                        result = await provider.generate(
                            prompt,
                            system_prompt=strict_prompt,
                            model=provider_model,
                            role=role,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            json_mode=json_mode,
                        )
                        try:
                            return self.parse_json_response(result.text)
                        except json.JSONDecodeError as exc:
                            last_error = LLMProviderError(
                                f"Invalid JSON returned by {result.provider}: {exc}",
                                retryable=True,
                                error_type="invalid_json",
                            )
                            logger.warning(
                                "[LLM] invalid json from %s model=%s role=%s attempt=%s json_mode=%s",
                                result.provider,
                                provider_model or "auto",
                                role or "generic",
                                attempt,
                                json_mode,
                            )
                            break
                    except LLMProviderError as exc:
                        last_error = exc
                        logger.warning(
                            "[LLM] provider=%s model=%s role=%s attempt=%s json_mode=%s retryable=%s status=%s error=%s",
                            provider.provider_name,
                            provider_model or "auto",
                            role or "generic",
                            attempt,
                            json_mode,
                            exc.retryable,
                            exc.status_code,
                            exc,
                        )
                        if exc.error_type == "quota_exhausted" or ("quota" in str(exc).lower() and not exc.retryable):
                            self.disabled_providers.add(provider.provider_name)
                            logger.warning("[LLM] Disabling provider %s due to quota exhaustion", provider.provider_name)
                            provider_break = True
                            break
                        if not exc.retryable or attempt >= self.settings.provider_retries + 1:
                            break
                        delay = self._extract_retry_delay(str(exc)) or min(2 ** (attempt - 1), 4)
                        await asyncio.sleep(min(delay, 20))

        raise LLMProviderError(f"All LLM providers failed to produce valid JSON: {last_error}") if last_error else LLMProviderError(
            "No LLM providers are configured"
        )


_llm_manager: LLMManager | None = None


def get_llm_manager() -> LLMManager:
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager
