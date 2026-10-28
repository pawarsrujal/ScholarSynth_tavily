from agents.verifier import validate_citations
from models import Source


def test_citation_validation():
    registry = {'S1': Source(id='S1', title='A', url='https://example.com/a', content='x')}
    content, invalid = validate_citations('Claim [S1] and [S999].', registry)
    assert '[S999]' not in content
    assert invalid == ['S999']
