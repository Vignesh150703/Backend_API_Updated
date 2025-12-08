from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.document_routes import router as document_router
from app.api.result_routes import router as result_router
from app.api.status_routes import router as status_router
from app.api.upload_routes import router as upload_router
from app.db.base import Base
from app.db.session import engine
from app.utils.logger import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Medical Document Pipeline", lifespan=lifespan)

app.include_router(upload_router)
app.include_router(document_router)
app.include_router(result_router)
app.include_router(status_router)

