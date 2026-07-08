from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    BigInteger,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.database import Base


# ==========================================================
# INSTANCE SETTINGS
# Only one row exists
# ==========================================================

class InstanceSettings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
    )

    storage_endpoint: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    storage_api_key: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


# ==========================================================
# SMS CACHE
# This is NOT permanent storage.
# Used only for dashboard display.
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
    )

    received_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )

    # ------------------------------------------------------
    # Dashboard status
    # ------------------------------------------------------

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
    )

    forwarded: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    response_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )