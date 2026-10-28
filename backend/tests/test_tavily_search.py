import pytest

from research.tavily_client import TavilyClient


@pytest.mark.asyncio
async def test_tavily_search(monkeypatch):
    class FakeResponse:
        status_code = 200
        text = ''
        def json(self):
            return {
                'results': [
                    {
                        'title': 'Example Article',
                        'url': 'https://example.com/article/?utm_source=x',
                        'content': 'Example content',
                        'raw_content': 'Example raw content',
                        'score': 0.9,
                        'published_date': '2025-01-01',
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr('research.tavily_client.httpx.AsyncClient', FakeClient)
    monkeypatch.setattr('research.tavily_client.get_settings', lambda: type('S', (), {'tavily_api_key': 'x', 'tavily_timeout_seconds': 1, 'max_results_per_query': 5})())

    client = TavilyClient()
    results = await client.search('example')
    assert len(results) == 1
    assert results[0].title == 'Example Article'
