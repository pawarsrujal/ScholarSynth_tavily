import pytest

from agents import publisher as publisher_module
from models import Evidence, Report, Source, SubQuestion


@pytest.mark.asyncio
async def test_report_generation(monkeypatch):
    source = Source(id='S1', title='A', url='https://example.com/a', content='alpha', snippet='alpha')
    subquestion = SubQuestion(
        id='SQ1',
        question='Q1',
        search_queries=['q1'],
        status='completed',
        sources=[source],
        evidence=[Evidence(claim='c', supporting_text='alpha', source_ids=['S1'], confidence=0.9)],
        summary='summary',
    )

    class FakeManager:
        async def generate_json(self, *args, **kwargs):
            return {
                'title': 'Test Report',
                'summary': 'A summary',
                'content': '# Title\n\nClaim [S1].',
                'used_source_ids': ['S1'],
            }

    monkeypatch.setattr(publisher_module, 'get_llm_manager', lambda: FakeManager())

    result = await publisher_module.publisher_node({'query': 'q', 'sub_questions': [subquestion], 'source_registry': {'S1': source}})
    assert result['report'].title == 'Test Report'
    assert result['report'].citation_count >= 1
