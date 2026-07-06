import os
from dotenv import load_dotenv

# ==========================================================
# Load Environment Variables
# ==========================================================
load_dotenv()

# ==========================================================
# Application
# ==========================================================
SERVICE_NAME = "SMS Forwarding Backend"

SERVICE_VERSION = "3.0.0"

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# ==========================================================
# Database
# ==========================================================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is missing."
    )

# ==========================================================
# JWT
# ==========================================================
JWT_SECRET = os.getenv("JWT_SECRET")

if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET environment variable is missing."
    )

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256",
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "30",
    )
)

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv(
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "7",
    )
)

# ==========================================================
# External Forwarding (Optional)
# ==========================================================
EXTERNAL_ENDPOINT = os.getenv(
    "EXTERNAL_ENDPOINT",
)

EXTERNAL_TIMEOUT = int(
    os.getenv(
        "EXTERNAL_TIMEOUT",
        "10",
    )
)

# ==========================================================
# Logging
# ==========================================================
LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
)

LOG_FILE = os.getenv(
    "LOG_FILE",
    "logs/app.log",
)

# ==========================================================
# Sentry
# ==========================================================
SENTRY_DSN = os.getenv(
    "SENTRY_DSN",
)