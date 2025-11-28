from __future__ import annotations

import asyncio
import re


class DeidService:
    PHI_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{10}\b")

    async def redact_phi(self, text: str) -> str:
        await asyncio.sleep(0)
        return self.PHI_PATTERN.sub("[REDACTED]", text)


def get_deid_service() -> DeidService:
    return DeidService()

