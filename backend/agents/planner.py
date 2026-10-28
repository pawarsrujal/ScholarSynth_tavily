"""Planner agent - generates grounded subquestions and search queries."""

from __future__ import annotations

from typing import Any, Dict

from config import get_settings
from events import event_hub
from llm.llm_manager import get_llm_manager
from llm.prompts import PLANNER_PROMPT
from models import SubQuestion


def _fallback_subquestions(query: str, count: int) -> list[dict[str, Any]]:
    themes = [
        "historical background and foundational concepts",
        "current state of the field",
        "key empirical findings",
        "methodologies and approaches",
        "controversies and disagreements",
        "limitations and open problems",
        "real-world applications and implications",
        "future directions and research agenda",
    ]
    settings = get_settings()
    subquestions: list[dict[str, Any]] = []
    for index, theme in enumerate(themes[:count], start=1):
        question = f"What does the literature say about the {theme} related to {query.lower()}?"
        subquestions.append(
            {
                "id": f"SQ{index}",
                "question": question,
                "search_queries": [
                    f"{query} {theme}",
                    f"{query} research {theme}",
                    f"{query} study {theme}",
                ][: settings.max_search_queries_per_subquestion],
            }
        )
    return subquestions


async def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state["query"]
    task_tag = state.get("task_id", "")[:8]
    print(f"[{task_tag}] 🔍 Planner: Analyzing query: {query}")

    try:
        settings = get_settings()
        manager = get_llm_manager()
        await event_hub.publish(state["task_id"], "planning_started", {"query": query})
        prompt = PLANNER_PROMPT.format(query=query)
        response = await manager.generate_json(prompt, role="planner", temperature=0.2, max_tokens=1800)
        items = response.get("sub_questions", [])
        if not isinstance(items, list) or not items:
            raise ValueError("Planner returned no subquestions")

        subquestions: list[SubQuestion] = []
        for index, item in enumerate(items[: settings.max_subquestions], start=1):
            if isinstance(item, str):
                question = item.strip()
                item = {
                    "id": f"SQ{index}",
                    "question": question,
                    "search_queries": [f"{query} {question}"],
                }
            question = str(item.get("question", "")).strip()
            search_queries = [str(q).strip() for q in item.get("search_queries", []) if str(q).strip()]
            if not question:
                continue
            if not search_queries:
                search_queries = [f"{query} {question}"]
            subquestions.append(
                SubQuestion(
                    id=str(item.get("id") or f"SQ{index}"),
                    question=question,
                    search_queries=search_queries[: settings.max_search_queries_per_subquestion],
                )
            )

        if not subquestions:
            subquestions = [
                SubQuestion(id=item["id"], question=item["question"], search_queries=item["search_queries"])
                for item in _fallback_subquestions(query, min(settings.max_subquestions, 4))
            ]

        print(f"[{task_tag}] ✅ Planner: Generated {len(subquestions)} sub-questions")
        await event_hub.publish(state["task_id"], "subquestions_created", {"count": len(subquestions)})
        return {
            "sub_questions": subquestions,
            "state": "planning",
            "current_step": f"Planning complete - {len(subquestions)} research questions generated",
            "progress_percentage": 10,
        }

    except Exception as e:
        print(f"[{task_tag}] ⚠️ Planner LLM error: {str(e)} - using fallback subquestions")
        settings = get_settings()
        fallback = _fallback_subquestions(query, min(settings.max_subquestions, 4))
        subquestions = [
            SubQuestion(id=item["id"], question=item["question"], search_queries=item["search_queries"])
            for item in fallback
        ]
        await event_hub.publish(state["task_id"], "subquestions_created", {"count": len(subquestions)})
        return {
            "sub_questions": subquestions,
            "state": "planning",
            "current_step": f"Planning complete - {len(subquestions)} research questions generated",
            "progress_percentage": 10,
        }
