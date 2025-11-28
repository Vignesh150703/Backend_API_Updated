from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.session import get_db_session
from app.schemas.document_schema import DocumentOut, DocumentsResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentsResponse)
async def list_documents(
    patient_id: str = Query(...),
    hospital_id: str = Query(...),
    doc_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentsResponse:
    stmt = select(Document).where(Document.patient_id == patient_id, Document.hospital_id == hospital_id)
    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)
    if status_filter:
        stmt = stmt.where(Document.status == status_filter)

    documents = (await session.scalars(stmt)).all()
    return DocumentsResponse(documents=[DocumentOut.model_validate(doc, from_attributes=True) for doc in documents])

