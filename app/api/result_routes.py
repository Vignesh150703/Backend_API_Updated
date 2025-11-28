from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_page import DocumentPage
from app.db.models.job import Job
from app.db.models.ocr_deidentified_text import OcrDeidentifiedText
from app.db.session import get_db_session

router = APIRouter(prefix="/result", tags=["result"])


@router.get("/{job_id}")
async def job_result(job_id: str, session: AsyncSession = Depends(get_db_session)) -> dict:
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    documents = (await session.scalars(select(Document).where(Document.job_id == job_id))).all()
    document_payload = []
    for doc in documents:
        pages = (
            await session.scalars(select(DocumentPage).where(DocumentPage.document_id == doc.document_id).order_by(DocumentPage.page_number))
        ).all()
        extract = {}
        for page in pages:
            deid = await session.scalar(select(OcrDeidentifiedText).where(OcrDeidentifiedText.page_id == page.page_id))
            extract[f"page{page.page_number}"] = {
                "img": page.image_base64,
                "text": deid.deid_text if deid else "",
            }
        document_payload.append({"docId": doc.document_id, "extract": extract})

    return {"jobId": job.job_id, "documents": document_payload}

