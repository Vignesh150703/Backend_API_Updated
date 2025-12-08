from __future__ import annotations

from pydantic import BaseModel, Field


class UploadMetadata(BaseModel):
    patient_id: str = Field(..., min_length=1)
    hospital_id: str = Field(..., min_length=1)
    doc_type: str = Field(..., min_length=1)


class PageExtraction(BaseModel):
    image_path: str
    extracted_text: str


class UploadResponse(BaseModel):
    job_id: str

