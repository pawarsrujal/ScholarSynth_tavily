"""Publisher agent - synthesizes verified evidence into the final report."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from events import event_hub
from agents.verifier import bibliography_from_registry, cited_source_ids, validate_citations
from llm.llm_manager import get_llm_manager
from llm.prompts import PUBLISHER_PROMPT
from models import Report, Source, SubQuestion


def _format_evidence(sub_questions: List[SubQuestion]) -> str:
    chunks: list[str] = []
    for subquestion in sub_questions:
        if subquestion.status == "failed" and not subquestion.evidence:
            continue
        chunks.append(f"## {subquestion.question}")
        if subquestion.summary:
            chunks.append(f"Summary: {subquestion.summary}")
        for evidence in subquestion.evidence:
            if not evidence.valid:
                continue
            chunks.append(
                f"- Claim: {evidence.claim}\n  Supporting text: {evidence.supporting_text}\n  Sources: {', '.join(evidence.source_ids)}\n  Confidence: {evidence.confidence:.2f}"
            )
    return "\n\n".join(chunks)


def _format_sources(source_registry: dict[str, Source], used_source_ids: list[str] | None = None) -> str:
    sources = bibliography_from_registry(source_registry, used_source_ids)
    blocks: list[str] = []
    for source in sources:
        blocks.append(f"[{source.id}] {source.title}\nURL: {source.url}\nDomain: {source.domain or ''}\nPublished: {source.published_date or ''}")
    return "\n\n".join(blocks)


async def publisher_node(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state.get("query", "")
    sub_questions: List[SubQuestion] = state.get("sub_questions", [])
    source_registry: dict[str, Source] = state.get("source_registry") or {}
    if not source_registry:
        all_sources = state.get("all_sources", [])
        if all_sources:
            source_registry = {
                (s.id if hasattr(s, "id") else s["id"]): (s if isinstance(s, Source) else Source(**s))
                for s in all_sources
            }
        else:
            for subq in sub_questions:
                sources = getattr(subq, "sources", []) or (subq.get("sources", []) if isinstance(subq, dict) else [])
                for s in sources:
                    sid = s.id if hasattr(s, "id") else s.get("id")
                    if sid:
                        source_registry[sid] = s if isinstance(s, Source) else Source(**s)

    task_tag = state.get("task_id", "")[:8]
    print(f"[{task_tag}] 📝 Publisher: Synthesizing {len(sub_questions)} research sections...")

    try:
        task_id = state.get("task_id", "")
        if task_id:
            await event_hub.publish(task_id, "publishing_started", {"sources": len(source_registry)})
        verified_evidence = [evidence for subquestion in sub_questions for evidence in getattr(subquestion, "evidence", []) if getattr(evidence, "valid", False)]
        if not verified_evidence:
            verified_evidence = [evidence for subquestion in sub_questions for evidence in getattr(subquestion, "evidence", [])]
            for ev in verified_evidence:
                ev.valid = True
        if not verified_evidence:
            raise ValueError("No verified evidence to synthesize")

        manager = get_llm_manager()
        prompt = PUBLISHER_PROMPT.format(
            query=query,
            evidence=_format_evidence(sub_questions),
            sources=_format_sources(source_registry),
        )
        response = await manager.generate_json(prompt, role="publisher", temperature=0.2, max_tokens=1400)

        content = str(response.get("content", "")).strip()
        title = str(response.get("title", query)).strip() or query
        summary = str(response.get("summary", "")).strip()
        used_source_ids = [str(source_id) for source_id in response.get("used_source_ids", []) if str(source_id) in source_registry]
        if not used_source_ids:
            used_source_ids = cited_source_ids(content, source_registry)

        content, invalid_citations = validate_citations(content, source_registry)
        citation_count = len(cited_source_ids(content, source_registry))
        sources = bibliography_from_registry(source_registry, used_source_ids or cited_source_ids(content, source_registry))
        word_count = len(content.split())

        if word_count < 1200 and summary:
            content = content + f"\n\n## Summary\n{summary}"
            word_count = len(content.split())

        report = Report(
            title=title,
            summary=summary or query,
            content=content,
            sources=sources,
            word_count=word_count,
            citation_count=citation_count,
            generated_at=datetime.now(timezone.utc),
        )

        print(f"[{task_tag}] ✅ Publisher: Generated {word_count} word report with {len(sources)} cited sources")
        if task_id:
            await event_hub.publish(task_id, "report_completed", {"word_count": word_count, "citation_count": citation_count})
        return {
            "report": report,
            "state": "completed",
            "current_step": "Report generation complete",
            "progress_percentage": 100,
        }

    except Exception as e:
        print(f"[{task_tag}] ❌ Publisher error: {str(e)}")
        return {
            "error": f"Publisher failed: {str(e)}",
            "current_step": "Report synthesis failed",
            "progress_percentage": 80,
        }
