from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_page import DocumentPage
from app.db.models.job import Job
from app.db.models.log_entry import LogEntry
from app.db.models.ocr_deidentified_text import OcrDeidentifiedText
from app.db.session import get_db_session

router = APIRouter(prefix="/status", tags=["status"])


@router.get("/{job_id}")
async def job_status(job_id: str, session: AsyncSession = Depends(get_db_session)) -> dict:
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    documents = (await session.scalars(select(Document).where(Document.job_id == job_id))).all()
    doc_payload = []
    for doc in documents:
        total_pages = await session.scalar(
            select(func.count()).select_from(DocumentPage).where(DocumentPage.document_id == doc.document_id)
        )
        completed_pages = await session.scalar(
            select(func.count())
            .select_from(OcrDeidentifiedText)
            .join(DocumentPage, OcrDeidentifiedText.page_id == DocumentPage.page_id)
            .where(DocumentPage.document_id == doc.document_id)
        )
        doc_payload.append(
            {
                "documentId": doc.document_id,
                "status": doc.status,
                "pagesTotal": total_pages or 0,
                "pagesCompleted": completed_pages or 0,
            }
        )

    logs = (
        await session.scalars(
            select(LogEntry.message).where(LogEntry.job_id == job_id).order_by(LogEntry.created_at.desc())
        )
    ).all()

    return {
        "job": {
            "jobId": job.job_id,
            "status": job.status,
            "createdAt": job.created_at,
            "updatedAt": job.updated_at,
        },
        "documents": doc_payload,
        "errors": logs,
    }

