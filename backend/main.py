"""FastAPI application for the grounded ScholarSynth V2 workflow."""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import get_settings
from events import event_hub
from graph import run_research_workflow
from memory import memory_store
from models import CreateReportRequest, StatusResponse, TaskState, TaskStatus

load_dotenv()

settings = get_settings()

app = FastAPI(
    title="ScholarSynth API",
    description="Multi-agent deep research system with LangGraph and real web retrieval",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "ScholarSynth",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/api/report", response_model=Dict[str, str])
async def create_report(request: CreateReportRequest):
    """
    Create a new research report task.
    
    Args:
        request: Research query
        
    Returns:
        task_id and status
    """
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    task_state = TaskState(task_id=task_id, query=request.query)
    
    # Store in memory
    memory_store.create(task_state)
    
    asyncio.create_task(run_research_workflow(task_state, memory_store))
    await event_hub.publish(task_id, "task_started", {"query": request.query})
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "Research workflow initiated"
    }


@app.get("/api/report/{task_id}/status", response_model=StatusResponse)
async def get_report_status(task_id: str):
    """
    Get status of a research task.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Current status and progress
    """
    task_state = memory_store.get(task_id)
    
    if not task_state:
        raise HTTPException(status_code=404, detail="Task not found")
    
    completed = sum(1 for q in task_state.sub_questions if q.status == "completed")
    
    return StatusResponse(
        task_id=task_id,
        state=task_state.state,
        status=task_state.state,
        current_step=task_state.current_step,
        progress_percentage=task_state.progress_percentage,
        sub_questions=task_state.sub_questions,
        sub_questions_count=len(task_state.sub_questions),
        completed_questions=completed,
        error=task_state.error,
    )


@app.get("/api/report/{task_id}")
async def get_report(task_id: str):
    """
    Get the final research report.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Complete task state with report
    """
    task_state = memory_store.get(task_id)
    
    if not task_state:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task_state.model_dump(mode="json")


@app.get("/api/report/{task_id}/stream")
async def stream_report_progress(task_id: str):
    """
    Server-Sent Events stream for real-time progress updates.
    
    Args:
        task_id: Task identifier
        
    Returns:
        SSE stream of status updates
    """
    task_state = memory_store.get(task_id)
    
    if not task_state:
        raise HTTPException(status_code=404, detail="Task not found")
    
    queue = event_hub.subscribe(task_id)

    async def event_generator():
        try:
            current_state = memory_store.get(task_id)
            if not current_state:
                yield f"event: error\ndata: {json.dumps({'error': 'Task not found'})}\n\n"
                return

            yield f"event: snapshot\ndata: {json.dumps(current_state.model_dump(mode='json'))}\n\n"

            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=2.0)
                    yield f"event: {payload['event']}\ndata: {json.dumps(payload)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"

                current_state = memory_store.get(task_id)
                if current_state and current_state.state in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    yield f"event: complete\ndata: {json.dumps(current_state.model_dump(mode='json'))}\n\n"
                    break
        finally:
            event_hub.unsubscribe(task_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.delete("/api/report/{task_id}")
async def delete_report(task_id: str):
    """
    Delete a research task from memory.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Success message
    """
    deleted = memory_store.delete(task_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task deleted successfully"}


@app.get("/api/reports")
async def list_reports():
    """
    List all active research tasks.
    
    Returns:
        List of all tasks in memory
    """
    all_tasks = memory_store.list_all()
    
    # Return summary of each task
    summaries = []
    for task_id, task_state in all_tasks.items():
        summaries.append({
            "task_id": task_id,
            "query": task_state.query,
            "status": task_state.state.value,
            "progress_percentage": task_state.progress_percentage,
            "created_at": task_state.created_at.isoformat(),
            "has_report": task_state.report is not None
        })
    
    return {"tasks": summaries, "count": len(summaries)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
