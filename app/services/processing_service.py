from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document, DocumentStatusEnum
from app.db.models.job import Job, JobStatusEnum
from app.utils.logger import get_logger
from app.workers.tasks.process_document_task import process_job_task

logger = get_logger(__name__)


class ProcessingService:
    async def start_job(self, session: AsyncSession, job_id: str) -> None:
        job = await session.scalar(select(Job).where(Job.job_id == job_id))
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = JobStatusEnum.PROCESSING.value

        documents = (await session.scalars(select(Document).where(Document.job_id == job_id))).all()
        for doc in documents:
            doc.status = DocumentStatusEnum.PROCESSING.value

        await session.commit()
        logger.info("processing.job.queued", job_id=job_id)
        process_job_task.delay(job_id)


def get_processing_service() -> ProcessingService:
    return ProcessingService()

