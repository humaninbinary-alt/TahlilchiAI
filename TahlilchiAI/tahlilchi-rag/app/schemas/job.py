"""Pydantic schemas for job tracking."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class JobStatus(BaseModel):
    """Job status response."""

    id: str
    tenant_id: str
    chat_id: str | None = None
    created_by: str | None = None
    task_name: str
    status: str
    progress: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobResult(BaseModel):
    """Job result response."""

    id: str
    tenant_id: str
    chat_id: str | None = None
    created_by: str | None = None
    task_name: str
    status: str
    progress: int
    result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    """Job creation response."""

    job_id: str
    message: str
