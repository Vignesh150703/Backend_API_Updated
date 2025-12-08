from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.upload_schema import UploadMetadata, UploadResponse
from app.services.upload_service import get_upload_service
from app.utils.pdf_to_image import PopplerNotInstalledError

router = APIRouter(prefix="/upload", tags=["upload"])
upload_service = get_upload_service()


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_documents(
    patient_id: str = Form(...),
    hospital_id: str = Form(...),
    doc_type: str = Form(...),
    files: List[UploadFile] = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> UploadResponse:
    metadata = UploadMetadata(patient_id=patient_id, hospital_id=hospital_id, doc_type=doc_type)
    try:
        job_id = await upload_service.create_job_with_documents(session, files, metadata)
        return UploadResponse(job_id=job_id)
    except PopplerNotInstalledError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

