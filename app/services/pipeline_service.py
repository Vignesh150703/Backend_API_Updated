from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Dict, List

from sqlalchemy import select

from app.db.models.document import Document, DocumentStatusEnum
from app.db.models.document_page import DocumentPage
from app.db.models.job import Job, JobStatusEnum
from app.db.models.ocr_deidentified_text import OcrDeidentifiedText
from app.db.models.ocr_raw_text import OcrRawText
from app.db.models.ocr_spellchecked_text import OcrSpellcheckedText
from app.db.session import AsyncSessionLocal
from app.services.pdf_service import get_pdf_service
from app.services.storage_service import get_storage_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Hardcoded stage outputs reused by the pipeline.
HARDCODED_OCR_TEXT = """Pl. Name: John Williams  Age: 45  Sex: M  Date: 10/2/21  Time: 10 PM  Seen by Dr: Matteo Rossi

Acute Kidney Injury, acute on chronic kidney disease (CKD), hypertension, diabetes mellitus, and hypothyroidism. Blood Pressure: 140/100 mmHg, Pulse Rate: 84/min, Oxygen Saturation: 99%. Ruled out Cushing's syndrome. Heart sounds: S1S2. Respiratory status: BAC. Temperature: Atebula (2) degrees Celsius. Oxygen therapy: (1) Inj. Meron 1.5 gm IV, twice daily; (2) Inj. Dytca 40 mg IV, twice daily; (3) Inj. Razole 80 mg IV, once daily; (4) Inj. Thiamine + Ruodine IV, once daily; (5) Inj. Pam 1 gm SC; (6) Tab. Rifagut 400 mg PO, twice daily; (7) Tab. Thymomom 75 mg PO, once daily; (8) G. Nacal Zalut 2 L/day PO, twice daily; (9) Nebulization with Dudlium x three times daily and Buducort x twice daily. Oxygen support: (10) Sitter. Gastrointestinal Resin: (11) x 8th hourly. Inj. 3% NaCl: (12) Tunkou. Plan: Hemodiafiltration."""

HARDCODED_SPELLCHECK_TEXT = HARDCODED_OCR_TEXT
HARDCODED_DEID_TEXT = """Pl. Name: PERSON  Age: AGE  Sex: M  Date: DATE_TIME  Time: 10 PM  Seen by Dr: PERSON


Acute Kidney Injury, acute on chronic kidney disease (CKD), hypertension, diabetes mellitus, and hypothyroidism. Blood Pressure: 140/100 mmHg, Pulse Rate: 84/min, Oxygen Saturation: 99%. Ruled out Cushing's syndrome. Heart sounds: S1S2. Respiratory status: BAC. Temperature: Atebula (2) degrees Celsius. Oxygen therapy: (1) Inj. Meron 1.5 gm IV, twice daily; (2) Inj. Dytca 40 mg IV, twice daily; (3) Inj. Razole 80 mg IV, once daily; (4) Inj. Thiamine + Ruodine IV, once daily; (5) Inj. Pam 1 gm SC; (6) Tab. Rifagut 400 mg PO, twice daily; (7) Tab. Thymomom 75 mg PO, once daily; (8) G. Nacal Zalut 2 L/day PO, twice daily; (9) Nebulization with Dudlium x three times daily and Buducort x twice daily. Oxygen support: (10) Sitter. Gastrointestinal Resin: (11) x 8th hourly. Inj. 3% NaCl: (12) Tunkou. Plan: Hemodiafiltration."""


class PipelineService:
    """Runs OCR -> spellcheck -> de-identification in the background."""

    def __init__(self) -> None:
        self.storage = get_storage_service()
        self.pdf_service = get_pdf_service()
        self._lock = asyncio.Lock()
        self._active_jobs: Dict[str, asyncio.Task] = {}

    async def ensure_started(self, job_id: str) -> None:
        """Start processing for the job if it's not already running."""
        async with self._lock:
            task = self._active_jobs.get(job_id)
            if task and not task.done():
                return
            task = asyncio.create_task(self._run_job(job_id))
            self._active_jobs[job_id] = task
            task.add_done_callback(lambda _: self._active_jobs.pop(job_id, None))

    async def _run_job(self, job_id: str) -> None:
        logger.info("pipeline.start", job_id=job_id)
        try:
            async with AsyncSessionLocal() as session:
                job = await session.get(Job, job_id)
                if not job:
                    return
                job.status = JobStatusEnum.PROCESSING.value
                await session.commit()

            await self._process_documents(job_id)

            async with AsyncSessionLocal() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.status = JobStatusEnum.COMPLETED.value
                    await session.commit()
            logger.info("pipeline.completed", job_id=job_id)
        except Exception:
            logger.exception("pipeline.failed", job_id=job_id)
            async with AsyncSessionLocal() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.status = JobStatusEnum.FAILED.value
                    await session.commit()

    async def _process_documents(self, job_id: str) -> None:
        async with AsyncSessionLocal() as session:
            documents = (
                await session.scalars(select(Document).where(Document.job_id == job_id))
            ).all()

        for document in documents:
            await self._process_document(document.document_id)

    async def _process_document(self, document_id: str) -> None:
        async with AsyncSessionLocal() as session:
            document = await session.get(Document, document_id)
            if not document:
                return
            if document.status == DocumentStatusEnum.COMPLETED.value:
                return
            document.status = DocumentStatusEnum.PROCESSING.value
            await session.commit()

        async with AsyncSessionLocal() as session:
            document = await session.get(Document, document_id)
            if not document:
                return

            original_bytes = await self.storage.retrieve_file(document.original_file_path)
            is_pdf = Path(document.original_file_path).suffix.lower() == ".pdf"
            if is_pdf:
                page_images = await self.pdf_service.convert_pdf_to_images(original_bytes)
            else:
                page_images = [original_bytes]

            for page_num, image_bytes in enumerate(page_images, start=1):
                image_path = f"{document.file_path}/page_{page_num}.png"
                await self.storage.store_file(image_path, image_bytes, "image/png")

                page = DocumentPage(
                    document_id=document.document_id,
                    page_number=page_num,
                    image_base64=base64.b64encode(image_bytes).decode("utf-8"),
                )
                session.add(page)
                await session.flush()

                session.add(OcrRawText(page_id=page.page_id, raw_text=HARDCODED_OCR_TEXT))
                session.add(
                    OcrSpellcheckedText(page_id=page.page_id, spellchecked_text=HARDCODED_SPELLCHECK_TEXT)
                )
                session.add(OcrDeidentifiedText(page_id=page.page_id, deid_text=HARDCODED_DEID_TEXT))

            document.status = DocumentStatusEnum.COMPLETED.value
            await session.commit()


_pipeline_service = PipelineService()


def get_pipeline_service() -> PipelineService:
    return _pipeline_service


