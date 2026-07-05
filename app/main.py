import logging
import os
import time
from contextlib import asynccontextmanager

import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.routes import sms, users
from app.websocket import router as ws_router
from app.config import SERVICE_NAME, SERVICE_VERSION

# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------
# Configure logging
# ---------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("sms_backend")

# ---------------------------------------------------------
# Sentry
# ---------------------------------------------------------
SENTRY_DSN = os.getenv("SENTRY_DSN")

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=float(
            os.getenv("SENTRY_TRACE_RATE", "1.0")
        ),
        send_default_pii=True,
    )
    logger.info("Sentry initialized")
else:
    logger.info("Sentry disabled")


# ---------------------------------------------------------
# Lifespan
# ---------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("===================================")
    logger.info("%s starting...", SERVICE_NAME)
    logger.info("Version: %s", SERVICE_VERSION)
    logger.info("===================================")

    yield

    logger.info("===================================")
    logger.info("%s shutting down...", SERVICE_NAME)
    logger.info("===================================")


# ---------------------------------------------------------
# FastAPI
# ---------------------------------------------------------
app = FastAPI(
    title=SERVICE_NAME,
    version=SERVICE_VERSION,
    lifespan=lifespan,
)


# ---------------------------------------------------------
# Root
# ---------------------------------------------------------
@app.get("/")
async def root():
    return JSONResponse(
        {
            "status": "healthy",
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
        }
    )


# ---------------------------------------------------------
# Request Logging Middleware
# ---------------------------------------------------------
@app.middleware("http")
async def request_logger(request: Request, call_next):

    start = time.perf_counter()

    logger.info(
        "REQUEST %s %s",
        request.method,
        request.url.path,
    )

    response = await call_next(request)

    duration = round(
        (time.perf_counter() - start) * 1000,
        2,
    )

    logger.info(
        "RESPONSE %s %s (%sms)",
        response.status_code,
        request.url.path,
        duration,
    )

    return response


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------
app.include_router(
    sms.router,
    prefix="/api",
    tags=["SMS"],
)

app.include_router(
    users.router,
    prefix="/api",
    tags=["Users"],
)

app.include_router(ws_router)