import pytest

from agents import executor as executor_module
from models import SubQuestion


@pytest.mark.asyncio
async def test_no_hallucinated_research(monkeypatch):
    subquestion = SubQuestion(id='SQ1', question='What happened in XYZ?', search_queries=['XYZ'], sources=[])
    result = await executor_module.execute_single_question(subquestion, 1)
    assert result.status == 'failed'
    assert 'No sources' in (result.error or '') or 'No sources' in (result.summary or '')
