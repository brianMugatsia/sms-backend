from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ==========================================================
# HEALTH
# ==========================================================

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# ==========================================================
# SETTINGS
# ==========================================================

class EndpointSettings(BaseModel):
    storage_endpoint: Optional[str] = None
    storage_api_key: Optional[str] = None


# ==========================================================
# SMS RECEIVED FROM PHONE
# ==========================================================

class SmsCreate(BaseModel):
    id: str
    sender: str
    message: str
    device_id: str
    received_at: int


# ==========================================================
# SMS CACHE RESPONSE
# ==========================================================

class SmsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sender: str
    message: str
    device_id: str

    received_at: int
    timestamp: datetime

    # Dashboard status
    status: str
    forwarded: bool

    response_code: Optional[int] = None
    error: Optional[str] = None


# ==========================================================
# PAGINATION
# ==========================================================

class Pagination(BaseModel):
    page: int
    size: int
    total: int
    pages: int


# ==========================================================
# SMS LIST
# ==========================================================

class SmsListResponse(BaseModel):
    items: list[SmsResponse]
    pagination: Pagination


# ==========================================================
# WEBSOCKET MESSAGE
# ==========================================================

class BroadcastSms(BaseModel):
    id: str
    sender: str
    message: str
    device_id: str

    received_at: int
    timestamp: datetime

    status: str
    forwarded: bool

    response_code: Optional[int] = None
    error: Optional[str] = None


# ==========================================================
# SIMPLE RESPONSE
# ==========================================================

class MessageResponse(BaseModel):
    success: bool
    message: str