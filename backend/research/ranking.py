"""Heuristic source ranking with diversity awareness."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from urllib.parse import urlparse

from models import Source


QUALITY_DOMAINS = {
    "arxiv.org": 1.0,
    "nature.com": 1.0,
    "science.org": 1.0,
    "nejm.org": 1.0,
    "pubmed.ncbi.nlm.nih.gov": 0.95,
    "wikipedia.org": 0.2,
}


def _freshness_boost(source: Source) -> float:
    if not source.published_date:
        return 0.0
    for fmt in ("%Y-%m-%d", "%a, %d %b %Y %H:%M:%S %Z", "%Y/%m/%d"):
        try:
            published = datetime.strptime(source.published_date, fmt)
            age_days = max((datetime.utcnow() - published).days, 0)
            if age_days < 30:
                return 0.25
            if age_days < 365:
                return 0.1
        except ValueError:
            continue
    return 0.0

def rank_sources(sources: list[Source], *, limit: int, promote_diversity: bool = True) -> list[Source]:
    domain_counts = Counter((source.domain or urlparse(source.url).hostname or "") for source in sources)

    def score(source: Source) -> float:
        base = source.score or 0.0
        content_bonus = min(len(source.content or "") / 4000, 0.4)
        snippet_bonus = 0.1 if source.snippet else 0.0
        quality_bonus = QUALITY_DOMAINS.get((source.domain or urlparse(source.url).hostname or "").lower(), 0.0)
        freshness_bonus = _freshness_boost(source)
        diversity_penalty = 0.0
        if promote_diversity and domain_counts[(source.domain or urlparse(source.url).hostname or "")] > 2:
            diversity_penalty = 0.15 * (domain_counts[(source.domain or urlparse(source.url).hostname or "")] - 2)
        return base + content_bonus + snippet_bonus + quality_bonus + freshness_bonus - diversity_penalty

    ranked = sorted(sources, key=score, reverse=True)
    selected: list[Source] = []
    used_domains: set[str] = set()
    for source in ranked:
        domain = (source.domain or urlparse(source.url).hostname or "").lower()
        if promote_diversity and domain in used_domains and len(selected) < max(limit // 2, 1):
            continue
        selected.append(source)
        used_domains.add(domain)
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        for source in ranked:
            if source not in selected:
                selected.append(source)
            if len(selected) >= limit:
                break
    return selected[:limit]
