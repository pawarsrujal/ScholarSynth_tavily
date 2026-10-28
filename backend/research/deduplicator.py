"""Source deduplication helpers based on normalized URLs."""

from __future__ import annotations

from collections import OrderedDict

from models import Source
from research.source_processor import normalize_url


def deduplicate_sources(sources: list[Source]) -> list[Source]:
    merged: OrderedDict[str, Source] = OrderedDict()
    for source in sources:
        key = normalize_url(source.url)
        if key not in merged:
            merged[key] = source
            continue
        existing = merged[key]
        if len(source.content or "") > len(existing.content or ""):
            existing.content = source.content
        if not existing.snippet and source.snippet:
            existing.snippet = source.snippet
        if source.score is not None:
            existing.score = max(existing.score or 0.0, source.score)
        if source.published_date and not existing.published_date:
            existing.published_date = source.published_date
        if source.metadata:
            existing.metadata.update(source.metadata)
    return list(merged.values())
