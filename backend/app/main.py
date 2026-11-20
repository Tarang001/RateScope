from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text

from app.api.v1 import router as v1_router
from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.core.logging import setup_logging
from app.core.metrics import metrics_payload
from app.core.middleware import RateLimitMiddleware, RequestIdMiddleware, TimingMiddleware
from app.pipeline.demo import bootstrap_data, inline_simulator
from app.pipeline.kafka import consume_loop, kafka_ready, stop_kafka

logger = logging.getLogger(__name__)
_background: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    if settings.app_env != "test":
        bootstrap_data()
    if settings.run_consumer:
        _background.append(asyncio.create_task(consume_loop()))
    elif settings.demo_mode and settings.app_env != "test":
        if not await kafka_ready(settings):
            logger.info("demo_inline_simulator", extra={"request_id": "-"})
            _background.append(asyncio.create_task(inline_simulator(settings)))
    yield
    await stop_kafka()
    for task in _background:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="RateScope", version="1.0.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(TimingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(v1_router)


@app.exception_handler(HTTPException)
async def http_exc(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": "http_error", "message": detail}})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.exception("unhandled_error")
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Unexpected server error"}},
    )


@app.get("/metrics")
def metrics():
    return Response(content=metrics_payload(), media_type="text/plain; version=0.0.4")


@app.get("/")
def root():
    return {"name": "RateScope", "docs": "/docs", "health": "/api/v1/health/live"}
