import pytest

from agents import executor as executor_module
from models import Source, SubQuestion


@pytest.mark.asyncio
async def test_failed_subquestion(monkeypatch):
    subquestions = [
        SubQuestion(id='SQ1', question='Q1', search_queries=['q1'], sources=[]),
        SubQuestion(id='SQ2', question='Q2', search_queries=['q2'], sources=[Source(id='S1', title='A', url='https://example.com/a', content='alpha', snippet='alpha')]),
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

    class FakeManager:
        async def generate_json(self, *args, **kwargs):
            return {'summary': 'summary', 'evidence': [{'claim': 'c', 'supporting_text': 'alpha', 'source_ids': ['S1'], 'confidence': 0.8}]}

    monkeypatch.setattr(executor_module, 'build_source_registry', fake_build_source_registry)
    monkeypatch.setattr(executor_module, 'get_llm_manager', lambda: FakeManager())

    result = await executor_module.executor_node({'task_id': 't1', 'sub_questions': subquestions})
    assert any(q.status == 'failed' for q in result['sub_questions'])
    assert any(q.status == 'completed' for q in result['sub_questions'])
