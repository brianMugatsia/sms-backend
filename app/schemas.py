from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


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
    model_config = ConfigDict(from_attributes=True)

    storage_endpoint: Optional[str] = Field(None, max_length=500)
    storage_api_key: Optional[str] = Field(None, max_length=500)


# ==========================================================
# SMS RECEIVED FROM PHONE
# ==========================================================

class SmsCreate(BaseModel):
    # Field constraints protect your database from buffer issues/invalid writes
    id: str = Field(..., min_length=1, max_length=120)
    sender: str = Field(..., min_length=1, max_length=100)
    message: str
    device_id: str = Field(..., min_length=1, max_length=150)
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
# WEBSOCKET MESSAGE (Inherits from SmsResponse to stay DRY)
# ==========================================================

class BroadcastSms(SmsResponse):
    pass


# ==========================================================
# SIMPLE RESPONSE / ENDPOINT TESTING
# ==========================================================

class MessageResponse(BaseModel):
    success: bool
    message: str


class EndpointTestRequest(BaseModel):
    storage_endpoint: str = Field(..., min_length=1, max_length=500)
    storage_api_key: Optional[str] = Field(None, max_length=500)


class EndpointTestResponse(BaseModel):
    success: bool
    message: str
    status_code: Optional[int] = None