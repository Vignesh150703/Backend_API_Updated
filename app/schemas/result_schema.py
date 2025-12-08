from __future__ import annotations

from typing import List

from pydantic import BaseModel


class ExtractionEntry(BaseModel):
    image_path: str
    extracted_text: str
    spellchecked_text: str
    deid_text: str


class DocumentResult(BaseModel):
    doc_id: str
    original_file_path: str | None = None
    extraction: List[ExtractionEntry]


class ResultResponse(BaseModel):
    job_id: str
    status: str
    document: List[DocumentResult]

