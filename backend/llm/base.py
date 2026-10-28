"""Shared LLM provider interfaces and response types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(slots=True)
class LLMResult:
    text: str
    provider: str
    model: str
    raw: Optional[dict[str, Any]] = None


class LLMProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
        error_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code
        self.error_type = error_type



class LLMProvider(ABC):
    provider_name: str

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResult:
        raise NotImplementedError
