import pytest

from llm.base import LLMProviderError, LLMResult
from llm.llm_manager import LLMManager


class FailingProvider:
    provider_name = 'openrouter'

    async def generate(self, *args, **kwargs):
        raise LLMProviderError('down', retryable=True)


class SuccessProvider:
    provider_name = 'gemini'

    async def generate(self, *args, **kwargs):
        return LLMResult(text='{"ok": true}', provider='gemini', model='test')


@pytest.mark.asyncio
async def test_llm_fallback(monkeypatch):
    manager = LLMManager()
    manager.providers = [FailingProvider(), SuccessProvider()]
    manager.settings.openrouter_api_key = 'x'
    manager.settings.groq_api_key = None
    manager.settings.gemini_api_key = 'x'
    result = await manager.generate('test', json_mode=False)
    assert result.provider == 'gemini'
