from __future__ import annotations

import asyncio
import base64

from sqlalchemy import select

from app.db.models.document_page import DocumentPage
from app.db.models.ocr_raw_text import OcrRawText
from app.db.session import AsyncSessionLocal
from app.services.log_service import get_log_service
from app.services.ocr_service import get_ocr_service
from app.utils.logger import get_logger
from app.workers.celery_app import celery_app
from app.workers.tasks.spellcheck_task import spellcheck_task

logger = get_logger(__name__)


log_service = get_log_service()


@celery_app.task(name="ocr_task")
def ocr_task(page_id: str) -> None:
    asyncio.run(_run_ocr(page_id))


async def _run_ocr(page_id: str) -> None:
    ocr_service = get_ocr_service()

    async with AsyncSessionLocal() as session:
        page = await session.get(DocumentPage, page_id)
        if not page:
            logger.error("ocr.page.missing", page_id=page_id)
            return

        image_bytes = base64.b64decode(page.image_base64 or "")
        text = await ocr_service.run_ocr(image_bytes)

        existing = await session.scalar(select(OcrRawText).where(OcrRawText.page_id == page_id))
        if existing:
            existing.raw_text = text
        else:
            session.add(OcrRawText(page_id=page_id, raw_text=text))
        await log_service.record(session, level="INFO", message="OCR stage complete", document_id=page.document_id)
        await session.commit()

    spellcheck_task.delay(page_id)

