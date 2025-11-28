from __future__ import annotations

import asyncio


class SpellcheckService:
    async def correct_text(self, text: str) -> str:
        # Placeholder: implement medical spellcheck
        await asyncio.sleep(0)
        return text


def get_spellcheck_service() -> SpellcheckService:
    return SpellcheckService()

