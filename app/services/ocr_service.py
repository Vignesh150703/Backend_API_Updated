from __future__ import annotations

import asyncio

from app.config.settings import get_settings


class OcrService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def run_ocr(self, image_bytes: bytes) -> str:
        # Placeholder: replace with actual OCR provider integration
        await asyncio.sleep(0)  # yield control
        return "Simulated OCR text"


def get_ocr_service() -> OcrService:
    return OcrService()

