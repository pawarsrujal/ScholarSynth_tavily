from agents.verifier import verify_evidence_items
from models import Evidence, Source


def test_evidence_validation():
    registry = {'S1': Source(id='S1', title='A', url='https://example.com/a', content='the sky is blue', snippet='the sky is blue')}
    evidence = [Evidence(claim='Sky color', supporting_text='the sky is blue', source_ids=['S1'], confidence=0.9)]
    verified = verify_evidence_items(evidence, registry)
    assert verified[0].valid is True
