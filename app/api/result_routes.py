from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_page import DocumentPage
from app.db.models.job import Job
from app.db.models.ocr_raw_text import OcrRawText
from app.db.models.ocr_spellchecked_text import OcrSpellcheckedText
from app.db.models.ocr_deidentified_text import OcrDeidentifiedText
from app.db.session import get_db_session
from app.schemas.result_schema import ResultResponse

router = APIRouter(prefix="/result", tags=["result"])


@router.get("/{job_id}", response_model=ResultResponse)
async def job_result(job_id: str, session: AsyncSession = Depends(get_db_session)) -> ResultResponse:
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    documents = (await session.scalars(select(Document).where(Document.job_id == job_id))).all()
    document_payload: list[dict] = []
    for doc in documents:
        pages = (
            await session.scalars(select(DocumentPage).where(DocumentPage.document_id == doc.document_id).order_by(DocumentPage.page_number))
        ).all()
        extraction_entries = []
        for page in pages:
            raw = await session.scalar(select(OcrRawText).where(OcrRawText.page_id == page.page_id))
            spellchecked = await session.scalar(
                select(OcrSpellcheckedText).where(OcrSpellcheckedText.page_id == page.page_id)
            )
            deid = await session.scalar(select(OcrDeidentifiedText).where(OcrDeidentifiedText.page_id == page.page_id))
            image_path = f"{doc.file_path}/page_{page.page_number}.png"
            extraction_entries.append(
                {
                    "image_path": image_path,
                    "extracted_text": raw.raw_text if raw else "",
                    "spellchecked_text": spellchecked.spellchecked_text if spellchecked else "",
                    "deid_text": deid.deid_text if deid else "",
                }
            )
        document_payload.append(
            {
                "doc_id": doc.document_id,
                "original_file_path": doc.original_file_path,
                "extraction": extraction_entries,
            }
        )

    return ResultResponse(job_id=job.job_id, status=job.status, document=document_payload)

