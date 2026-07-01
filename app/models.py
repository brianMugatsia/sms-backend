from sqlalchemy import Column, String, DateTime, func
from typing import Optional
from datetime import datetime
from app.database import Base
from pydantic import BaseModel

# SQLAlchemy models
class SmsModel(Base):
    __tablename__ = "sms"

    id = Column(String(36), primary_key=True, index=True)
    sender = Column(String(255), nullable=False)
    message = Column(String(500), nullable=False)
    device_id = Column(String(255), nullable=False)
    #  Store UTC timestamps, timezone-aware
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="user")  # "admin" or "user"

# Pydantic schemas
class Sms(BaseModel):
    sender: str
    message: str
    device_id: str
    role: str | None = None
    read: bool = False
    timestamp: Optional[datetime] = None

class User(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[str] = None 

class LoginRequest(BaseModel):
    username: str
    password: str
