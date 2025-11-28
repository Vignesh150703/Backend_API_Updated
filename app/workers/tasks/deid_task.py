from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from app.db.models.document import Document, DocumentStatusEnum
from app.db.models.document_page import DocumentPage
from app.db.models.job import Job, JobStatusEnum
from app.db.models.ocr_deidentified_text import OcrDeidentifiedText
from app.db.models.ocr_spellchecked_text import OcrSpellcheckedText
from app.db.session import AsyncSessionLocal
from app.services.deid_service import get_deid_service
from app.services.log_service import get_log_service
from app.utils.logger import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


log_service = get_log_service()


@celery_app.task(name="deid_task")
def deid_task(page_id: str) -> None:
    asyncio.run(_run_deid(page_id))


async def _run_deid(page_id: str) -> None:
    deid_service = get_deid_service()

    async with AsyncSessionLocal() as session:
        spellchecked = await session.scalar(select(OcrSpellcheckedText).where(OcrSpellcheckedText.page_id == page_id))
        if not spellchecked:
            logger.warning("deid.spellchecked_missing", page_id=page_id)
            return

        cleaned = await deid_service.redact_phi(spellchecked.spellchecked_text)

        existing = await session.scalar(select(OcrDeidentifiedText).where(OcrDeidentifiedText.page_id == page_id))
        if existing:
            existing.deid_text = cleaned
        else:
            session.add(OcrDeidentifiedText(page_id=page_id, deid_text=cleaned))

        await log_service.record(
            session,
            level="INFO",
            message="De-identification stage complete",
            document_id=page.document_id,
        )
        await session.commit()
        await _update_completion_state(session, page_id)


async def _update_completion_state(session: AsyncSessionLocal, page_id: str) -> None:
    page = await session.get(DocumentPage, page_id)
    if not page:
        return

    document_id = page.document_id
    document = await session.get(Document, document_id)
    total_pages = await session.scalar(
        select(func.count()).select_from(DocumentPage).where(DocumentPage.document_id == document_id)
    )
    completed_pages = await session.scalar(
        select(func.count())
        .select_from(OcrDeidentifiedText)
        .join(DocumentPage, OcrDeidentifiedText.page_id == DocumentPage.page_id)
        .where(DocumentPage.document_id == document_id)
    )

    if total_pages and completed_pages == total_pages and document:
        document.status = DocumentStatusEnum.COMPLETED.value
        await session.commit()

    job_id = document.job_id if document else None
    if not job_id:
        return

    remaining_docs = await session.scalar(
        select(func.count())
        .select_from(Document)
        .where(Document.job_id == job_id, Document.status != DocumentStatusEnum.COMPLETED.value)
    )

    if remaining_docs == 0:
        job = await session.get(Job, job_id)
        if job:
            job.status = JobStatusEnum.COMPLETED.value
            await session.commit()

