from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


BillingType = Literal["billable", "non-billable"]
Priority = Literal["high", "medium", "low"]
TaskStatus = Literal["created", "failed", "warning"]


class Task(BaseModel):
    task_name: str
    description: str
    assignee_names: list[str] = Field(default_factory=list)
    estimated_hours: float = Field(..., ge=0.5, le=999)
    billing_type: BillingType
    priority: Optional[Priority] = None
    dependencies: list[str] = Field(default_factory=list)
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD

    @field_validator('assignee_names', mode='before')
    @classmethod
    def coerce_assignee_names(cls, v):
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [v]
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> Task:
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be >= start_date")
        return self


class PushTask(Task):
    row_id: str


class ExtractRequest(BaseModel):
    sow_text: str = Field(..., max_length=50_000)
    team_members: list[str] = Field(default_factory=list)


class ExtractResponse(BaseModel):
    tasks: list[Task]


class PushRequest(BaseModel):
    project_id: str
    tasks: list[PushTask]


class PushTaskResult(BaseModel):
    row_id: str
    task_name: str
    status: TaskStatus
    zoho_task_id: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class PushResponse(BaseModel):
    results: list[PushTaskResult]
