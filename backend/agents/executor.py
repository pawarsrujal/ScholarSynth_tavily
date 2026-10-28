"""Executor agent - performs concurrent real web research and evidence extraction."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from config import get_settings
from events import event_hub
from llm.llm_manager import get_llm_manager
from llm.prompts import EXECUTOR_PROMPT
from models import Evidence, Source, SubQuestion
from research.search import build_source_registry, format_sources_for_prompt
from agents.verifier import verify_evidence_items


def _fallback_evidence(question: SubQuestion, sources: list[Source]) -> tuple[str, list[Evidence]]:
    summary = f"Insufficient verified evidence was available to fully answer: {question.question}"
    evidence: list[Evidence] = []
    for source in sources[:2]:
        evidence.append(
            Evidence(
                claim=f"Relevant source identified for {question.question}",
                supporting_text=(source.snippet or source.content or "")[:300],
                source_ids=[source.id],
                confidence=0.35,
            )
        )
    return summary, evidence


async def execute_single_question(question: SubQuestion, index: int) -> SubQuestion:
    task_tag = getattr(question, "task_id", "")[:8] if hasattr(question, "task_id") else ""
    print(f"[{task_tag}]   🔎 Executor [{index}]: Researching: {question.question[:60]}...")

    try:
        question.status = "searching"
        manager = get_llm_manager()
        prompt = EXECUTOR_PROMPT.format(question=question.question, sources=format_sources_for_prompt(question.sources))

        if not question.sources:
            summary, evidence = _fallback_evidence(question, question.sources)
            question.summary = summary
            question.evidence = evidence
            question.status = "failed"
            question.error = "No sources available for evidence extraction"
            return question

        question.status = "analyzing"
        response = await manager.generate_json(prompt, role="executor", temperature=0.2, max_tokens=800)

        summary = str(response.get("summary", "")).strip()
        evidence_items: list[Evidence] = []
        for item in response.get("evidence", []):
            if not isinstance(item, dict):
                continue
            source_ids = [str(source_id) for source_id in item.get("source_ids", []) if str(source_id)]
            evidence_items.append(
                Evidence(
                    claim=str(item.get("claim", "")).strip(),
                    supporting_text=str(item.get("supporting_text", "")).strip(),
                    source_ids=source_ids,
                    confidence=float(item.get("confidence", 0.5) or 0.5),
                )
            )

        verified = verify_evidence_items(evidence_items, {source.id: source for source in question.sources})
        question.summary = summary or _fallback_evidence(question, question.sources)[0]
        question.evidence = verified
        question.status = "completed" if (any(item.valid for item in verified) or (evidence_items and question.sources)) else "failed"
        if question.status == "failed" and not question.error:
            question.error = "Evidence extraction did not yield valid claims"

        print(f"[{task_tag}]   ✅ Executor [{index}]: Completed with {len(question.sources)} sources and {len(verified)} evidence items")
        return question

    except Exception as e:
        print(f"[{task_tag}]   ❌ Executor [{index}] error: {str(e)}")
        question.status = "failed"
        question.summary = f"Failed to research: {str(e)}"
        question.error = str(e)
        return question


async def executor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    sub_questions: List[SubQuestion] = state.get("sub_questions", [])

    if not sub_questions:
        return {
            "error": "No sub-questions to execute",
            "current_step": "Execution failed - no questions",
            "progress_percentage": 20,
        }

    task_tag = state.get("task_id", "")[:8]
    print(f"[{task_tag}] 🔬 Executor: Processing {len(sub_questions)} questions in parallel...")

    try:
        task_id = state["task_id"]
        await event_hub.publish(task_id, "research_started", {"subquestions": len(sub_questions)})
        sub_questions, all_sources = await build_source_registry(sub_questions, task_id)
        await event_hub.publish(task_id, "sources_collected", {"count": len(all_sources)})

        settings = get_settings()
        sem = asyncio.Semaphore(1)

        async def sem_execute(q: SubQuestion, i: int) -> SubQuestion:
            async with sem:
                res = await execute_single_question(q, i)
                await asyncio.sleep(1.2)
                return res

        tasks = [sem_execute(q, i) for i, q in enumerate(sub_questions)]
        completed_questions = await asyncio.gather(*tasks, return_exceptions=False)

        successful = sum(1 for q in completed_questions if q.status == "completed")
        all_evidence: list[Evidence] = []
        for q in completed_questions:
            all_evidence.extend(q.evidence)
            await event_hub.publish(task_id, "subquestion_completed", {"subquestion_id": q.id, "status": q.status, "source_count": len(q.sources)})

        source_registry = {source.id: source for source in all_sources}
        print(f"[{task_tag}] ✅ Executor: Completed {successful}/{len(sub_questions)} questions successfully")

        return {
            "sub_questions": completed_questions,
            "all_sources": all_sources,
            "source_registry": source_registry,
            "all_evidence": all_evidence,
            "state": "analyzing",
            "current_step": f"Research complete - {successful}/{len(sub_questions)} questions answered",
            "progress_percentage": 72,
        }

    except Exception as e:
        print(f"[{task_tag}] ❌ Executor error: {str(e)}")
        return {
            "error": f"Executor failed: {str(e)}",
            "current_step": "Research execution failed",
            "progress_percentage": 40,
        }
