from __future__ import annotations

import asyncio
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_page import DocumentPage
from app.db.models.job import Job, JobStatusEnum
from app.db.session import AsyncSessionLocal
from app.services.log_service import get_log_service
from app.services.pdf_service import get_pdf_service
from app.services.storage_service import get_storage_service
from app.utils.pdf_to_image import image_bytes_to_base64
from app.utils.logger import get_logger
from app.workers.celery_app import celery_app
from app.workers.tasks.ocr_task import ocr_task

logger = get_logger(__name__)


@celery_app.task(name="process_job_task")
def process_job_task(job_id: str) -> None:
    asyncio.run(_process_job(job_id))


async def _process_job(job_id: str) -> None:
    storage = get_storage_service()
    pdf_service = get_pdf_service()
    log_service = get_log_service()

    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if not job:
            logger.error("processing.job.missing", job_id=job_id)
            return

        documents = (await session.scalars(select(Document).where(Document.job_id == job_id))).all()
        logger.info("processing.job.start", job_id=job_id, documents=len(documents))
        await log_service.record(session, level="INFO", message="Job processing started", job_id=job_id)

        for document in documents:
            file_bytes = await storage.retrieve_file(document.file_path)
            is_pdf = file_bytes.startswith(b"%PDF")

            if is_pdf:
                page_images = await pdf_service.convert_pdf_to_images(file_bytes)
            else:
                page_images = [file_bytes]

            await _persist_pages_and_dispatch(session, document, page_images)

        job.status = JobStatusEnum.PROCESSING.value
        await session.commit()


async def _persist_pages_and_dispatch(session: AsyncSession, document: Document, page_images: List[bytes]) -> None:
    existing_pages = (
        await session.scalars(select(DocumentPage).where(DocumentPage.document_id == document.document_id))
    ).all()
    if existing_pages:
        logger.info("processing.document.pages.exists", document_id=document.document_id, pages=len(existing_pages))
        for page in existing_pages:
            ocr_task.delay(page.page_id)
        return
    for index, page_bytes in enumerate(page_images, start=1):
        page = DocumentPage(
            document_id=document.document_id,
            page_number=index,
            image_base64=image_bytes_to_base64(page_bytes),
        )
        session.add(page)
        await session.flush()
        ocr_task.delay(page.page_id)
    await session.commit()
    logger.info("processing.document.dispatched", document_id=document.document_id, pages=len(page_images))

