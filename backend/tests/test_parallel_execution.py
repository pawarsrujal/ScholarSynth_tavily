import pytest

from agents import executor as executor_module
from models import Evidence, Source, SubQuestion


@pytest.mark.asyncio
async def test_parallel_execution(monkeypatch):
    subquestions = [
        SubQuestion(id='SQ1', question='Q1', search_queries=['q1'], sources=[Source(id='S1', title='A', url='https://example.com/a', content='alpha', snippet='alpha')]),
        SubQuestion(id='SQ2', question='Q2', search_queries=['q2'], sources=[Source(id='S2', title='B', url='https://example.com/b', content='beta', snippet='beta')]),
    ]

    async def fake_build_source_registry(subqs, task_id):
        all_sources = []
        counter = 1
        for subq in subqs:
            for source in subq.sources:
                source.id = f'S{counter}'
                counter += 1
                all_sources.append(source)
        return subqs, all_sources

    async def fake_generate_json(*args, **kwargs):
        return {
            'summary': 'summary',
            'evidence': [{'claim': 'c', 'supporting_text': 'alpha', 'source_ids': ['S1'], 'confidence': 0.8}],
        }

    class FakeManager:
        async def generate_json(self, *args, **kwargs):
            return await fake_generate_json()

    monkeypatch.setattr(executor_module, 'build_source_registry', fake_build_source_registry)
    monkeypatch.setattr(executor_module, 'get_llm_manager', lambda: FakeManager())

    result = await executor_module.executor_node({'task_id': 't1', 'sub_questions': subquestions})
    assert len(result['sub_questions']) == 2
    assert result['all_sources']
    assert any(q.status == 'completed' for q in result['sub_questions'])
