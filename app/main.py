import logging
import os
import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from app.routes import sms, users
from app.websocket import router as ws_router
from sentry_sdk.integrations.fastapi import FastApiIntegration
from fastapi.responses import JSONResponse

# Load environment variables
load_dotenv()

# Initialize Sentry (no SQLAlchemy integration)
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True
)

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sms_backend")

app = FastAPI(title="SMS Forwarding Backend")

@app.get("/")
async def root():
    return JSONResponse(content={"message": "SMS Forwarding Backend is running"})

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f" Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f" Response status: {response.status_code}")
    return response

# Register routes
app.include_router(sms.router, prefix="/api", tags=["SMS"])
app.include_router(users.router, prefix="/api", tags=["Users"])
app.include_router(ws_router)

@app.on_event("startup")
async def startup_event():
    logger.info(" FastAPI backend started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info(" FastAPI backend shutting down")
