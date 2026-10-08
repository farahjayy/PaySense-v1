"""PaySense API — FastAPI entrypoint.

    cd backend && .venv/Scripts/uvicorn app.main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config
from app.db import repo
from app.routers import balance, bnpl, dashboard, imports, risk, transactions
from app.services.ml_models import get_engine2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("paysense")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast and loud: missing env or unloadable model must stop the server.
    config.validate_env()
    repo.assert_transactions_link_column()
    engine = get_engine2()
    logger.info("Startup OK — Engine 2 ready with %d features", len(engine.feature_names))
    yield


app = FastAPI(title="PaySense API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "code": "INTERNAL_ERROR",
                "message": "Something went wrong on the server — check the backend logs.",
            }
        },
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(dashboard.router)
app.include_router(balance.router)
app.include_router(transactions.router)
app.include_router(bnpl.router)
app.include_router(risk.router)
app.include_router(imports.router)
