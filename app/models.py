from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo
from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    BigInteger,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

NAIROBI_TZ = ZoneInfo("Africa/Nairobi")


def nairobi_now() -> datetime:
    return datetime.now(NAIROBI_TZ)


# ==========================================================
# INSTANCE SETTINGS
# Single configuration row table
# ==========================================================

class InstanceSettings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
    )

    storage_endpoint: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    storage_api_key: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=nairobi_now,
        onupdate=nairobi_now,
    )


# ==========================================================
# SMS CACHE
# Lightweight diagnostic storage for WebSockets & dashboard
# ==========================================================

class SMS(Base):
    __tablename__ = "sms_cache"

    id: Mapped[str] = mapped_column(
        String(120),
        primary_key=True,
    )

    sender: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    device_id: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    received_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=nairobi_now,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
    )

    forwarded: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    response_code: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Soft-delete flag: when True, the row is hidden from that device's
    # dashboard, but the record is permanently retained in the database
    # for future reference (audit, disputes, debugging).
    deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )