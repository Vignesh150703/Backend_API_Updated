from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.models.document_page import DocumentPage
from app.db.models.ocr_raw_text import OcrRawText
from app.db.models.ocr_spellchecked_text import OcrSpellcheckedText
from app.db.session import AsyncSessionLocal
from app.services.log_service import get_log_service
from app.services.spellcheck_service import get_spellcheck_service
from app.utils.logger import get_logger
from app.workers.celery_app import celery_app
from app.workers.tasks.deid_task import deid_task

logger = get_logger(__name__)


log_service = get_log_service()


@celery_app.task(name="spellcheck_task")
def spellcheck_task(page_id: str) -> None:
    asyncio.run(_run_spellcheck(page_id))


async def _run_spellcheck(page_id: str) -> None:
    spell_service = get_spellcheck_service()

    async with AsyncSessionLocal() as session:
        raw_text = await session.scalar(select(OcrRawText).where(OcrRawText.page_id == page_id))
        if not raw_text:
            logger.warning("spellcheck.raw_text_missing", page_id=page_id)
            return
        page = await session.get(DocumentPage, page_id)

        corrected = await spell_service.correct_text(raw_text.raw_text)

        existing = await session.scalar(select(OcrSpellcheckedText).where(OcrSpellcheckedText.page_id == page_id))
        if existing:
            existing.spellchecked_text = corrected
        else:
            session.add(OcrSpellcheckedText(page_id=page_id, spellchecked_text=corrected))
        await log_service.record(
            session,
            level="INFO",
            message="Spellcheck stage complete",
            document_id=page.document_id if page else None,
        )
        await session.commit()

    deid_task.delay(page_id)

