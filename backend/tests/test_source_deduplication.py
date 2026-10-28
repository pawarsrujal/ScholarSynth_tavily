from models import Source
from research.deduplicator import deduplicate_sources


def test_source_deduplication():
    sources = [
        Source(id='S1', title='A', url='https://example.com/article', content='one', snippet='one'),
        Source(id='S2', title='A copy', url='https://example.com/article/', content='two', snippet='two'),
    ]
    deduped = deduplicate_sources(sources)
    assert len(deduped) == 1
    assert deduped[0].content in {'one', 'two'}
