from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database import Base


# ==========================================================
# USERS
# ==========================================================
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False,
    )

    endpoint_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    sms_messages = relationship(
        "SMS",
        back_populates="owner",
        cascade="all, delete-orphan",
    )


# ==========================================================
# DEVICES
# ==========================================================
class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    device_id: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False,
    )

    device_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    last_seen: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    sms_messages = relationship(
        "SMS",
        back_populates="device",
    )


# ==========================================================
# SMS
# ==========================================================
class SMS(Base):
    __tablename__ = "sms"

    id: Mapped[str] = mapped_column(
        String(120),
        primary_key=True,
    )

    sender: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.device_id"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    received_at: Mapped[int] = mapped_column(
        nullable=False,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )

    read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    owner = relationship(
        "User",
        back_populates="sms_messages",
    )

    device = relationship(
        "Device",
        back_populates="sms_messages",
    )


# ==========================================================
# DATABASE INDEXES
# ==========================================================
Index(
    "idx_sms_user_timestamp",
    SMS.user_id,
    SMS.timestamp.desc(),
)

Index(
    "idx_sms_sender",
    SMS.sender,
)

Index(
    "idx_sms_device",
    SMS.device_id,
)