from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class Sms(BaseModel):
    sender: str
    message: str
    device_id: str
    role: Optional[str] = None
    read: bool = False
    timestamp: Optional[datetime] = None

class User(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[str] = None
    #  Optional: allow per-user endpoint configuration
    endpoint_url: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str
