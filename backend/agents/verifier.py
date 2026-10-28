"""Programmatic evidence and citation verification."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Tuple

from models import Evidence, Source

_CITATION_RE = re.compile(r"\[(S\d+)\]")


def verify_evidence_items(evidence_items: list[Evidence], source_registry: dict[str, Source]) -> list[Evidence]:
    verified: list[Evidence] = []
    for item in evidence_items:
        if not item.supporting_text:
            item.valid = False
            item.reason = "Missing supporting text"
            verified.append(item)
            continue

        invalid_ids = [source_id for source_id in item.source_ids if source_id not in source_registry]
        if invalid_ids:
            item.valid = False
            item.reason = f"Unknown source IDs: {', '.join(invalid_ids)}"
            verified.append(item)
            continue

        supporting_text = item.supporting_text.lower()
        matched = False
        for source_id in item.source_ids:
            source = source_registry[source_id]
            source_text = f"{source.content or ''} {source.snippet or ''}".lower()
            if not source_text.strip():
                continue
            if supporting_text in source_text:
                matched = True
                break
            words = [w for w in re.findall(r"\w+", supporting_text) if len(w) > 2]
            if words:
                overlap = sum(1 for w in words if w in source_text)
                if overlap / len(words) >= 0.4:
                    matched = True
                    break

        if not matched:
            item.valid = False
            item.reason = "Supporting text not found in supplied sources"
            verified.append(item)
            continue

        item.valid = True
        item.reason = None
        verified.append(item)
    return verified


def validate_citations(report_content: str, source_registry: dict[str, Source]) -> tuple[str, list[str]]:
    citations = _CITATION_RE.findall(report_content)
    invalid_ids = sorted(set(citation for citation in citations if citation not in source_registry))
    sanitized = report_content
    for citation_id in invalid_ids:
        sanitized = sanitized.replace(f"[{citation_id}]", "")
    sanitized = re.sub(r"\s{2,}", " ", sanitized).strip()
    return sanitized, invalid_ids


def cited_source_ids(report_content: str, source_registry: dict[str, Source]) -> list[str]:
    citations = _CITATION_RE.findall(report_content)
    unique_ids: list[str] = []
    for citation_id in citations:
        if citation_id in source_registry and citation_id not in unique_ids:
            unique_ids.append(citation_id)
    return unique_ids


def bibliography_from_registry(source_registry: dict[str, Source], used_source_ids: list[str] | None = None) -> list[Source]:
    if used_source_ids is None:
        return list(source_registry.values())
    return [source_registry[source_id] for source_id in used_source_ids if source_id in source_registry]


async def verifier_node(state: dict[str, Any]) -> dict[str, Any]:
    source_registry: dict[str, Source] = state.get("source_registry") or {}
    subquestions = state.get("sub_questions", [])
    if not source_registry:
        all_sources = state.get("all_sources", [])
        if all_sources:
            source_registry = {
                (s.id if hasattr(s, "id") else s["id"]): (s if isinstance(s, Source) else Source(**s))
                for s in all_sources
            }
        else:
            for subq in subquestions:
                sources = getattr(subq, "sources", []) or (subq.get("sources", []) if isinstance(subq, dict) else [])
                for s in sources:
                    sid = s.id if hasattr(s, "id") else s.get("id")
                    if sid:
                        source_registry[sid] = s if isinstance(s, Source) else Source(**s)

    task_id = state.get("task_id", "")
    if task_id:
        from events import event_hub

        await event_hub.publish(task_id, "verification_started", {"evidence_items": len([e for s in subquestions for e in getattr(s, 'evidence', [])])})
    all_evidence = [evidence for subquestion in subquestions for evidence in getattr(subquestion, "evidence", [])]
    verified = verify_evidence_items(all_evidence, source_registry)

    index = 0
    for subquestion in subquestions:
        updated_items: list[Evidence] = []
        for evidence in getattr(subquestion, "evidence", []):
            if index < len(verified):
                updated_items.append(verified[index])
            index += 1
        subquestion.evidence = updated_items

    return {
        "sub_questions": subquestions,
        "source_registry": source_registry,
        "all_evidence": verified,
        "state": "verifying",
        "current_step": f"Verified {len(verified)} evidence items",
        "progress_percentage": 85,
    }
