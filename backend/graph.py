"""LangGraph workflow for the grounded research pipeline."""

from __future__ import annotations

import asyncio
import sys
from typing import Any, Dict, List, Optional, TypedDict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


from agents.executor import executor_node
from agents.planner import planner_node
from agents.publisher import publisher_node
from agents.verifier import verifier_node
from events import event_hub
from langgraph.graph import END, StateGraph
from models import Evidence, Report, Source, SubQuestion, TaskState, TaskStatus


class GraphState(TypedDict):
    """State definition for the research graph"""
    task_id: str
    query: str
    state: str
    sub_questions: List[Dict[str, Any]]
    source_registry: Dict[str, Dict[str, Any]]
    all_sources: List[Dict[str, Any]]
    all_evidence: List[Dict[str, Any]]
    report: Optional[Dict[str, Any]]
    error: Optional[str]
    current_step: str
    progress_percentage: int


def should_continue_to_executor(state: GraphState) -> str:
    """Conditional edge: check if planner succeeded"""
    if state.get("error"):
        return "end"
    if not state.get("sub_questions"):
        return "end"
    return "executor"


def should_continue_to_verifier(state: GraphState) -> str:
    """Conditional edge: check if executor succeeded"""
    if state.get("error"):
        print("⚠️ Skipping verifier: error detected")
        return "end"
    
    sub_questions = state.get("sub_questions", [])
    if not sub_questions:
        print("⚠️ Skipping verifier: no sub_questions")
        return "end"
    return "verifier"


def should_continue_to_publisher(state: GraphState) -> str:
    if state.get("error"):
        print("⚠️ Skipping publisher: error detected")
        return "end"
    if not state.get("sub_questions"):
        print("⚠️ Skipping publisher: no sub_questions")
        return "end"
    return "publisher"


def create_research_graph():
    """
    Create and compile the LangGraph workflow.
    
    Graph structure:
        START → planner → executor → verifier → publisher → END
    """
    # Initialize graph
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("publisher", publisher_node)
    
    # Add edges
    workflow.set_entry_point("planner")
    
    # Planner → Executor (with conditional check)
    workflow.add_conditional_edges(
        "planner",
        should_continue_to_executor,
        {
            "executor": "executor",
            "end": END
        }
    )
    
    # Executor → Publisher (with conditional check)
    workflow.add_conditional_edges(
        "executor",
        should_continue_to_verifier,
        {
            "verifier": "verifier",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "verifier",
        should_continue_to_publisher,
        {
            "publisher": "publisher",
            "end": END
        }
    )
    
    # Publisher → END
    workflow.add_edge("publisher", END)
    
    # Compile graph
    return workflow.compile()


# Global compiled graph instance
research_graph = create_research_graph()


async def run_research_workflow(task_state: TaskState, memory_store) -> TaskState:
    """
    Execute the complete research workflow for a task.
    
    Args:
        task_state: Initial task state
        memory_store: Memory store to update during execution
        
    Returns:
        Updated task state after workflow completion
    """
    task_tag = task_state.task_id[:8]
    print(f"\n{'='*60}")
    print(f"[{task_tag}] 🚀 Starting research workflow")
    print(f"[{task_tag}] 📋 Query: {task_state.query}")
    print(f"{'='*60}\n")
    
    # Convert TaskState to GraphState dict
    initial_state: GraphState = {
        "task_id": task_state.task_id,
        "query": task_state.query,
        "state": TaskStatus.PLANNING.value,
        "sub_questions": [],
        "source_registry": {},
        "all_sources": [],
        "all_evidence": [],
        "report": None,
        "error": None,
        "current_step": "Starting research...",
        "progress_percentage": 0
    }
    
    try:
        # Update status to planning
        task_state.state = TaskStatus.PLANNING
        task_state.update_progress("Planning research questions...", 5)
        memory_store.update(task_state.task_id, task_state)
        await event_hub.publish(task_state.task_id, "progress", task_state.model_dump(mode="json"))
        
        # Run the graph with streaming to capture intermediate states
        final_state = None
        
        # Use astream to get updates after each node completes
        # astream yields updates in format: {node_name: node_output}
        async for state_update in research_graph.astream(initial_state):
            # Extract the actual state data from the node output
            # state_update format: {node_name: {...node_output...}}
            print(f"[{task_tag}] 📡 Graph state update received: {list(state_update.keys())}")
            
            # Get the node output (the actual state data)
            node_output = None
            for node_name, output in state_update.items():
                node_output = output
                print(f"[{task_tag}]   └─ Processing node: {node_name}")
                break
            
            if not node_output:
                continue
                
            # Update task state with the node output
            if node_output.get("state"):
                task_state.state = TaskStatus(node_output["state"])
            
            # Update progress
            if node_output.get("current_step") or node_output.get("progress_percentage") is not None:
                task_state.update_progress(
                    node_output.get("current_step", task_state.current_step),
                    node_output.get("progress_percentage", task_state.progress_percentage)
                )
            
            # Update sub_questions if available
            if node_output.get("sub_questions"):
                task_state.sub_questions = [
                    SubQuestion(**q) if isinstance(q, dict) else q
                    for q in node_output["sub_questions"]
                ]

            if node_output.get("all_sources") is not None:
                task_state.all_sources = [
                    Source(**source) if isinstance(source, dict) else source
                    for source in node_output.get("all_sources", [])
                ]
                task_state.source_registry = {source.id: source for source in task_state.all_sources}

            if node_output.get("all_evidence") is not None:
                task_state.all_evidence = [
                    Evidence(**evidence) if isinstance(evidence, dict) else evidence
                    for evidence in node_output.get("all_evidence", [])
                ]
            
            # Update report if available
            if node_output.get("report"):
                report_data = node_output["report"]
                task_state.report = Report(**report_data) if isinstance(report_data, dict) else report_data
                task_state.state = TaskStatus.COMPLETED
                task_state.update_progress("Research complete!", 100)
            
            # Handle errors
            if node_output.get("error"):
                task_state.state = TaskStatus.FAILED
                task_state.error = node_output["error"]
            
            # Persist to memory store after each state update
            memory_store.update(task_state.task_id, task_state)
            await event_hub.publish(task_state.task_id, "progress", task_state.model_dump(mode="json"))
            print(f"[{task_tag}]   └─ Memory store updated: {task_state.state.value}, {task_state.progress_percentage}%, sub_questions: {len(task_state.sub_questions)}")
            
            final_state = node_output
        
        # Final update after workflow completes
        if final_state:
            if final_state.get("error"):
                task_state.state = TaskStatus.FAILED
                task_state.error = final_state["error"]
                task_state.update_progress(f"Failed: {final_state['error']}", 0)
            elif task_state.state != TaskStatus.COMPLETED:
                # If we completed without errors but status isn't DONE, check if we have a report
                if task_state.report:
                    task_state.state = TaskStatus.COMPLETED
                    task_state.update_progress("Research complete!", 100)
        
        # Save final state
        memory_store.update(task_state.task_id, task_state)
        terminal_event = "complete" if task_state.state == TaskStatus.COMPLETED else "error"
        await event_hub.publish(task_state.task_id, terminal_event, task_state.model_dump(mode="json"))
        await event_hub.publish(task_state.task_id, "progress", task_state.model_dump(mode="json"))

        print(f"\n{'='*60}")
        print(f"[{task_tag}] ✅ Workflow complete")
        print(f"[{task_tag}] 📊 Status: {task_state.state}")
        print(f"{'='*60}\n")

        return task_state

    except Exception as e:
        print(f"\n❌ Workflow error for task {task_state.task_id}: {str(e)}\n")
        task_state.state = TaskStatus.FAILED
        task_state.error = str(e)
        task_state.update_progress(f"Workflow failed: {str(e)}", 0)
        memory_store.update(task_state.task_id, task_state)
        await event_hub.publish(task_state.task_id, "error", task_state.model_dump(mode="json"))
        return task_state
