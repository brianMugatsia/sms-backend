import os

EXTERNAL_ENDPOINT = os.getenv(
    "ENDPOINT_URL",
    "https://endpint.roberms.com/roberms/aop/"
)

EXTERNAL_TIMEOUT = int(
    os.getenv("EXTERNAL_TIMEOUT", 10)
)

SERVICE_NAME = "SMS Forwarding Backend"

SERVICE_VERSION = "2.0.0"