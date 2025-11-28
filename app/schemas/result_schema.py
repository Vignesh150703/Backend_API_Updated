from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel


class PageExtract(BaseModel):
    img: str
    text: str


class DocumentExtract(BaseModel):
    doc_id: str
    extract: Dict[str, PageExtract]


class ResultResponse(BaseModel):
    job_id: str
    documents: List[DocumentExtract]

