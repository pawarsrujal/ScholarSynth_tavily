"""Concurrent Tavily-backed research orchestration."""

from __future__ import annotations

import asyncio
from config import get_settings
from events import event_hub
from models import Source, SubQuestion
from research.deduplicator import deduplicate_sources
from research.ranking import rank_sources
from research.source_processor import assign_source_ids, enrich_source_content, source_text_bundle
from research.tavily_client import TavilyClient


async def search_subquestion(subquestion: SubQuestion, semaphore: asyncio.Semaphore, task_id: str) -> list[Source]:
    settings = get_settings()
    client = TavilyClient()
    subquestion.status = "searching"
    await event_hub.publish(task_id, "subquestion_started", {"subquestion_id": subquestion.id, "question": subquestion.question})

    collected: list[Source] = []
    search_queries = subquestion.search_queries[: settings.max_search_queries_per_subquestion]
    for query in search_queries:
        await event_hub.publish(task_id, "search_started", {"subquestion_id": subquestion.id, "query": query})
        async with semaphore:
            sources = await client.search_with_retry(query)
        for source in sources:
            await event_hub.publish(task_id, "source_found", {"title": source.title, "url": source.url, "query": query})
        collected.extend(sources)

    if not collected:
        return []

    deduped = deduplicate_sources(collected)
    ranked = rank_sources(deduped, limit=settings.max_sources_per_subquestion)

    enriched = await asyncio.gather(*(enrich_source_content(source) for source in ranked))
    return assign_source_ids(list(enriched))


async def build_source_registry(subquestions: list[SubQuestion], task_id: str) -> tuple[list[SubQuestion], list[Source]]:
    settings = get_settings()
    semaphore = asyncio.Semaphore(settings.max_concurrent_research)
    tasks = [search_subquestion(subquestion, semaphore, task_id) for subquestion in subquestions]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_sources: list[Source] = []
    counter = 1
    for subquestion, result in zip(subquestions, results):
        if isinstance(result, Exception):
            subquestion.status = "failed"
            subquestion.error = str(result)
            continue
        subquestion.sources = result
        if result:
            for source in result:
                source.id = f"S{counter}"
                counter += 1
                all_sources.append(source)
            subquestion.status = "retrieving"
        else:
            subquestion.status = "failed"
            subquestion.error = "No legitimate sources found"
    return subquestions, all_sources

def format_sources_for_prompt(sources: list[Source], max_sources: int = 4, max_length_per_source: int = 700) -> str:
    return "\n\n".join(source_text_bundle(source, max_content_length=max_length_per_source) for source in sources[:max_sources])
