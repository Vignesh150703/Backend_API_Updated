from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.process_schema import ProcessRequest
from app.services.processing_service import get_processing_service

router = APIRouter(prefix="/process", tags=["processing"])
processing_service = get_processing_service()


@router.post("/{job_id}", status_code=status.HTTP_202_ACCEPTED)
async def process_job(
    job_id: str,
    _: ProcessRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        await processing_service.start_job(session, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"jobId": job_id, "message": "Processing started"}

