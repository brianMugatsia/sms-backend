from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo
from pydantic import BaseModel, ConfigDict, Field, field_serializer

NAIROBI_TZ = ZoneInfo("Africa/Nairobi")


def to_nairobi(value: datetime) -> datetime:
    """
    Normalizes any datetime (naive or aware) to an aware Africa/Nairobi datetime.
    Naive datetimes (e.g. from SQLite) are treated as UTC before shifting to EAT.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(NAIROBI_TZ)


# ==========================================================
# HEALTH & SETTINGS
# ==========================================================

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class EndpointSettings(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: str = Field(..., min_length=1, max_length=150)
    storage_endpoint: Optional[str] = Field(None, max_length=500)
    storage_api_key: Optional[str] = Field(None, max_length=500)


# ==========================================================
# SMS PAYLOADS
# ==========================================================

class SmsCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=120)
    sender: str = Field(..., min_length=1, max_length=100)
    message: str
    device_id: str = Field(..., min_length=1, max_length=150)
    received_at: int


class SmsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return to_nairobi(value).isoformat()


# ==========================================================
# LISTS & BROADCASTS
# ==========================================================

class Pagination(BaseModel):
    page: int
    size: int
    total: int
    pages: int


class SmsListResponse(BaseModel):
    items: list[SmsResponse]
    pagination: Pagination


class BroadcastSms(SmsResponse):
    pass


# ==========================================================
# TESTING & UTILITIES
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