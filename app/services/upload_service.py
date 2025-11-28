from __future__ import annotations

import base64
import uuid
from typing import Any, Dict, List

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document, DocumentStatusEnum
from app.db.models.document_page import DocumentPage
from app.db.models.job import Job, JobStatusEnum
from app.db.models.ocr_raw_text import OcrRawText
from app.schemas.upload_schema import UploadMetadata
from app.services.pdf_service import get_pdf_service
from app.services.storage_service import get_storage_service
from app.utils.image_utils import detect_file_kind
from app.utils.logger import get_logger
from app.utils.pdf_to_image import PopplerNotInstalledError

logger = get_logger(__name__)

# Hardcoded extracted text
HARDCODED_EXTRACTED_TEXT = """△ Acute Kidney Injury

? Acute on CKD

HIN @ | DM @ | Hypothyroid

BP

1.  convulsion

and cerebral

BP: 140/100 mmHg

PR: 84/min

SpO  : 99% r/o

CYS: S1S2

RS: BAC@

Temp: Atebula

(2) O  @

(1) Inj. Meron S 1.5 gm IV/BD

(3) Inj. Dytca 40 mg IV/BD

(2) Inj. Razole 80 mg IV/OD

(4) Inj. Thiamine + Ruodine IV/OD

(5) Inj. Pam 1 gm SC

(6) Tab. Rifagut 400 mg PO/BD

(7) Tab. Thymomom 75 mg PO/OD

(8) G. Nacal Zalut 2 L/Day PO/BD

(9) Neb. Dudlium x TID

Buducort x BD

(10) O  support @ Sitter

(11) GRES x 8th hourly

(12) Inj. 3% NaCl @ Tunkou

Plan

HDF"""


class UploadService:
    def __init__(self) -> None:
        self.storage = get_storage_service()
        self.pdf_service = get_pdf_service()

    async def create_job_with_documents(
        self,
        session: AsyncSession,
        files: List[UploadFile],
        metadata: UploadMetadata,
    ) -> tuple[str, List[Dict[str, Any]], str]:
        """Create job, process documents, and return results."""
        job = Job(status=JobStatusEnum.PROCESSING.value)
        session.add(job)
        await session.flush()

        documents_result: List[Dict[str, Any]] = []

        for file in files:
            content = await file.read()
            document_id = str(uuid.uuid4())
            base_storage_path = f"{metadata.hospital_id}/{metadata.patient_id}/{metadata.doc_type}/{document_id}"
            
            # Detect if PDF or image
            file_kind = detect_file_kind(file.filename or "", file.content_type or "")
            
            # Convert PDF to images or use image directly
            if file_kind == "pdf":
                try:
                    page_images = await self.pdf_service.convert_pdf_to_images(content)
                except PopplerNotInstalledError as e:
                    logger.error("upload.pdf_conversion_failed", error=str(e))
                    raise
            else:
                page_images = [content]

            # Create document record
            document = Document(
                document_id=document_id,
                job_id=job.job_id,
                patient_id=metadata.patient_id,
                hospital_id=metadata.hospital_id,
                doc_type=metadata.doc_type,
                file_path=base_storage_path,
                status=DocumentStatusEnum.PROCESSING.value,
            )
            session.add(document)
            await session.flush()

            # Process each page
            page_extractions: Dict[str, Dict[str, str]] = {}
            
            for page_num, image_bytes in enumerate(page_images, start=1):
                # Save image to MinIO
                image_path = f"{base_storage_path}/page_{page_num}.png"
                await self.storage.store_file(image_path, image_bytes, "image/png")
                
                # Use hardcoded extracted text
                extracted_text = HARDCODED_EXTRACTED_TEXT
                
                # Create document page
                page = DocumentPage(
                    document_id=document_id,
                    page_number=page_num,
                    image_base64=base64.b64encode(image_bytes).decode("utf-8"),
                )
                session.add(page)
                await session.flush()
                
                # Save OCR result
                ocr_raw = OcrRawText(page_id=page.page_id, raw_text=extracted_text)
                session.add(ocr_raw)
                
                # Add to page extractions
                page_extractions[f"page{page_num}extraction"] = {
                    "image_path": image_path,
                    "extracted_text": extracted_text,
                }

            document.status = DocumentStatusEnum.COMPLETED.value
            
            documents_result.append({
                "doc_id": document_id,
                **page_extractions,
            })

        job.status = JobStatusEnum.COMPLETED.value
        await session.commit()
        
        logger.info("upload.completed", job_id=job.job_id, documents=len(documents_result))
        return job.job_id, documents_result, job.status


def get_upload_service() -> UploadService:
    return UploadService()

