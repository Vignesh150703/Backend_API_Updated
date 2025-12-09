from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class DocTypeEnum(str, enum.Enum):
    LAB_REPORTS = "lab_reports"
    RADIOLOGY_REPORTS = "radiology_reports"
    PROGRESS_NOTES = "progress_notes"
    CONSULTATION_NOTES = "consultation_notes"


class UploadMetadata(BaseModel):
    patient_id: str = Field(..., min_length=1, example="patient_123")
    hospital_id: str = Field(..., min_length=1, example="hospital_456")
    doc_type: DocTypeEnum = Field(...)


class PageExtraction(BaseModel):
    image_path: str
    extracted_text: str


class UploadResponse(BaseModel):
    job_id: str

