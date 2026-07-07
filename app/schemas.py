from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


# ==========================================================
# HEALTH
# ==========================================================
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# ==========================================================
# AUTH
# ==========================================================
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ==========================================================
# USERS
# ==========================================================
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "user"

    
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: str

    storage_endpoint: Optional[str]
    dashboard_endpoint: Optional[str]

    created_at: datetime
    updated_at: datetime

class EndpointSettings(BaseModel):
    storage_endpoint: Optional[str] = None
    storage_api_key: Optional[str] = None

    dashboard_endpoint: Optional[str] = None
    dashboard_api_key: Optional[str] = None
# ==========================================================
# DEVICES
# ==========================================================
class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    device_name: Optional[str]
    last_seen: datetime
    created_at: datetime


# ==========================================================
# SMS CREATE
# ==========================================================
class SmsCreate(BaseModel):
    id: str
    sender: str
    message: str
    device_id: str
    received_at: int


# ==========================================================
# SMS RESPONSE
# ==========================================================
class SmsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sender: str
    message: str
    device_id: str
    user_id: int

    received_at: int
    timestamp: datetime

    read: bool


# ==========================================================
# SMS UPDATE
# ==========================================================
class SmsUpdate(BaseModel):
    read: bool


# ==========================================================
# PAGINATION
# ==========================================================
class Pagination(BaseModel):
    page: int
    size: int
    total: int
    pages: int


# ==========================================================
# SMS LIST RESPONSE
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

    user_id: int

    received_at: int
    timestamp: datetime

    read: bool


# ==========================================================
# SIMPLE MESSAGE
# ==========================================================
class MessageResponse(BaseModel):
    success: bool
    message: str


# ==========================================================
# DUPLICATE RESPONSE
# ==========================================================
class DuplicateSmsResponse(BaseModel):
    success: bool
    duplicate: bool
    sms: SmsResponse

