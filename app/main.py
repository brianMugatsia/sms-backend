import logging
import os
import time
from contextlib import asynccontextmanager

import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.database import Base, engine
from app.routes import sms, users
from app.websocket import router as websocket_router

load_dotenv()

# ==========================================================
# DATABASE
# ==========================================================
Base.metadata.create_all(bind=engine)

# ==========================================================
# LOGGING
# ==========================================================
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("sms_backend")

# ==========================================================
# SENTRY
# ==========================================================
SENTRY_DSN = os.getenv("SENTRY_DSN")

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True,
    )

# ==========================================================
# LIFESPAN
# ==========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("===================================")
    logger.info("SMS Backend Started")
    logger.info("===================================")

    yield

    logger.info("===================================")
    logger.info("SMS Backend Stopped")
    logger.info("===================================")


app = FastAPI(
    title="SMS Backend",
    version="3.0.0",
    lifespan=lifespan,
)

# ==========================================================
# REQUEST LOGGER
# ==========================================================
@app.middleware("http")
async def request_logger(
    request: Request,
    call_next,
):

    start = time.perf_counter()

    response = await call_next(request)

    elapsed = round(
        (time.perf_counter() - start) * 1000,
        2,
    )

    logger.info(
        "%s %s %s (%sms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )

    return response

# ==========================================================
# ROOT
# ==========================================================
@app.get("/")
def root():
    return {
        "status": "healthy",
        "service": "SMS Backend",
        "version": "3.0.0",
    }

# ==========================================================
# API HEALTH
# ==========================================================
@app.get("/api/health")
def health():
    return {
        "status": "healthy",
    }

# ==========================================================
# ROUTERS
# ==========================================================
app.include_router(
    users.router,
    prefix="/api",
    tags=["Users"],
)

app.include_router(
    sms.router,
    prefix="/api",
    tags=["SMS"],
)

app.include_router(
    websocket_router
)

# ==========================================================
# GLOBAL ERROR HANDLER
# ==========================================================
@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):

    logger.exception(exc)

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal Server Error",
        },
    )