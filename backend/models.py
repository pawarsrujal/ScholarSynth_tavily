"""Pydantic models for task state management, sources, evidence, and reports."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Unified state machine for research tasks and subquestions."""

    PLANNING = "planning"
    SEARCHING = "searching"
    RETRIEVING = "retrieving"
    ANALYZING = "analyzing"
    VERIFYING = "verifying"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"


class Source(BaseModel):
    """Verified source retrieved from Tavily or optional page fetch."""

    id: str
    title: str
    url: str
    content: str
    snippet: Optional[str] = None
    published_date: Optional[str] = None
    domain: Optional[str] = None
    score: Optional[float] = None
    query: Optional[str] = None
    source_type: str = "web"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    """Evidence item extracted strictly from supplied source content."""

    claim: str
    supporting_text: str
    source_ids: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
    valid: bool = True
    reason: Optional[str] = None


class SubQuestion(BaseModel):
    """Planner output and downstream research container."""

    id: str
    question: str
    search_queries: List[str] = Field(default_factory=list)
    status: Literal["pending", "searching", "retrieving", "analyzing", "completed", "failed"] = "pending"
    sources: List[Source] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    summary: Optional[str] = None
    error: Optional[str] = None


class Report(BaseModel):
    """Final research report and bibliography data."""

    title: str
    summary: str
    content: str
    sources: List[Source] = Field(default_factory=list)
    word_count: int = 0
    citation_count: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskState(BaseModel):
    """Complete state for a research task."""

    task_id: str
    query: str
    state: TaskStatus = TaskStatus.PLANNING
    sub_questions: List[SubQuestion] = Field(default_factory=list)
    source_registry: Dict[str, Source] = Field(default_factory=dict)
    all_sources: List[Source] = Field(default_factory=list)
    all_evidence: List[Evidence] = Field(default_factory=list)
    report: Optional[Report] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    current_step: str = "Initializing research..."
    progress_percentage: int = 0

    @property
    def status(self) -> TaskStatus:
        """Backward-compatible alias used by the V1 code."""

        return self.state

    @status.setter
    def status(self, value: TaskStatus | str) -> None:
        self.state = TaskStatus(value)

    def update_progress(self, step: str, percentage: int) -> None:
        """Update progress tracking."""

        self.current_step = step
        self.progress_percentage = max(0, min(100, percentage))
        self.updated_at = datetime.utcnow()

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()


class CreateReportRequest(BaseModel):
    """Request model for creating a new report."""

    query: str = Field(..., min_length=10, max_length=500)

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "What are the latest advances in quantum computing and their implications for cryptography?"
            }
        }
    }


class StatusResponse(BaseModel):
    """Response for task status polling."""

    task_id: str
    state: TaskStatus
    status: TaskStatus
    current_step: str
    progress_percentage: int
    sub_questions: List[SubQuestion] = Field(default_factory=list)
    sub_questions_count: int = 0
    completed_questions: int = 0
    error: Optional[str] = None


class ReportResponse(BaseModel):
    """Response body for the completed report endpoint."""

    task_id: str
    title: str
    summary: str
    content: str
    sources: List[Source] = Field(default_factory=list)
    word_count: int
    citation_count: int
