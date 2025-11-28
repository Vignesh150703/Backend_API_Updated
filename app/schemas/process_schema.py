from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ProcessRequest(BaseModel):
    priority: Optional[int] = 5


class JobStatus(BaseModel):
    job_id: str
    status: str
    created_at: datetime
    updated_at: datetime


class StatusResponse(BaseModel):
    job: JobStatus
    documents: List[dict]
    errors: List[str]

