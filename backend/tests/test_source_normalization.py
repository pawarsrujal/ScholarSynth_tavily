from research.source_processor import normalize_url


def test_source_normalization():
    assert normalize_url('https://example.com/article/?utm_source=x#section') == 'https://example.com/article'
    assert normalize_url('https://Example.com/article/') == 'https://example.com/article'
