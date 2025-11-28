from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class UploadMetadata(BaseModel):
    patient_id: str = Field(..., min_length=1)
    hospital_id: str = Field(..., min_length=1)
    doc_type: str = Field(..., min_length=1)


class PageExtraction(BaseModel):
    image_path: str
    extracted_text: str


class DocumentResult(BaseModel):
    doc_id: str
    # Dynamic page extractions (page1extraction, page2extraction, etc.)
    model_config = {"extra": "allow"}


class UploadResponse(BaseModel):
    job_id: str
    document: List[Dict[str, Any]]
    status: str

