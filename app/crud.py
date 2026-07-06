from datetime import datetime
from math import ceil
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auth, models, schemas


# ==========================================================
# USERS
# ==========================================================
def get_user_by_id(
    db: Session,
    user_id: int,
):
    return (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )


def get_user_by_username(
    db: Session,
    username: str,
):
    return (
        db.query(models.User)
        .filter(models.User.username == username)
        .first()
    )


def get_user_by_email(
    db: Session,
    email: str,
):
    return (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )


def get_users(
    db: Session,
):
    return (
        db.query(models.User)
        .order_by(models.User.username)
        .all()
    )


def create_user(
    db: Session,
    user: schemas.UserCreate,
):

    if get_user_by_username(db, user.username):
        raise ValueError("Username already exists")

    if get_user_by_email(db, user.email):
        raise ValueError("Email already exists")

    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=auth.get_password_hash(
            user.password
        ),
        role=user.role,
        endpoint_url=user.endpoint_url,
    )

    db.add(db_user)

    db.commit()

    db.refresh(db_user)

    return db_user


def authenticate_user(
    db: Session,
    username: str,
    password: str,
):

    user = get_user_by_username(
        db,
        username,
    )

    if user is None:
        return None

    if not auth.verify_password(
        password,
        user.hashed_password,
    ):
        return None

    return user


# ==========================================================
# DEVICES
# ==========================================================
def get_device(
    db: Session,
    device_id: str,
):

    return (
        db.query(models.Device)
        .filter(
            models.Device.device_id == device_id
        )
        .first()
    )


def register_device(
    db: Session,
    device_id: str,
):

    device = get_device(
        db,
        device_id,
    )

    if device:

        device.last_seen = datetime.utcnow()

        db.commit()

        db.refresh(device)

        return device

    device = models.Device(
        device_id=device_id,
        last_seen=datetime.utcnow(),
    )

    db.add(device)

    db.commit()

    db.refresh(device)

    return device


# ==========================================================
# SMS
# ==========================================================
def sms_exists(
    db: Session,
    sms_id: str,
):

    return (
        db.query(models.SMS)
        .filter(models.SMS.id == sms_id)
        .first()
    )


def create_sms(
    db: Session,
    sms: schemas.SmsCreate,
    user_id: int,
):

    existing = sms_exists(
        db,
        sms.id,
    )

    if existing:
        return existing, True

    register_device(
        db,
        sms.device_id,
    )

    db_sms = models.SMS(
        id=sms.id,
        sender=sms.sender,
        message=sms.message,
        device_id=sms.device_id,
        user_id=user_id,
        received_at=sms.received_at,
        timestamp=datetime.utcnow(),
        read=False,
    )

    db.add(db_sms)

    try:

        db.commit()

        db.refresh(db_sms)

    except IntegrityError:

        db.rollback()

        existing = sms_exists(
            db,
            sms.id,
        )

        if existing:
            return existing, True

        raise

    return db_sms, False


def get_sms(
    db: Session,
    sms_id: str,
):

    return (
        db.query(models.SMS)
        .filter(
            models.SMS.id == sms_id
        )
        .first()
    )


def get_user_sms(
    db: Session,
    sms_id: str,
    user_id: int,
):

    return (
        db.query(models.SMS)
        .filter(
            models.SMS.id == sms_id,
            models.SMS.user_id == user_id,
        )
        .first()
    )
# ==========================================================
# SMS LIST
# ==========================================================
def list_sms(
    db: Session,
    page: int,
    size: int,
    user_id: int,
    role: str,
    search: Optional[str] = None,
):

    query = db.query(models.SMS)

    # Admins see everything
    if role != "admin":
        query = query.filter(
            models.SMS.user_id == user_id
        )

    # Search sender or message
    if search:
        search = search.strip()

        query = query.filter(
            or_(
                models.SMS.sender.ilike(f"%{search}%"),
                models.SMS.message.ilike(f"%{search}%"),
            )
        )

    total = query.count()

    pages = max(1, ceil(total / size))

    items = (
        query.order_by(models.SMS.timestamp.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "items": items,
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "pages": pages,
        },
    }


# ==========================================================
# DELETE SMS
# ==========================================================
def delete_sms(
    db: Session,
    sms_id: str,
):

    sms = get_sms(
        db,
        sms_id,
    )

    if sms is None:
        return None

    db.delete(sms)

    db.commit()

    return sms


# ==========================================================
# MARK READ
# ==========================================================
def mark_sms_read(
    db: Session,
    sms_id: str,
):

    sms = get_sms(
        db,
        sms_id,
    )

    if sms is None:
        return None

    if sms.read:
        return sms

    sms.read = True

    db.commit()

    db.refresh(sms)

    return sms


# ==========================================================
# MARK UNREAD
# ==========================================================
def mark_sms_unread(
    db: Session,
    sms_id: str,
):

    sms = get_sms(
        db,
        sms_id,
    )

    if sms is None:
        return None

    if not sms.read:
        return sms

    sms.read = False

    db.commit()

    db.refresh(sms)

    return sms


# ==========================================================
# USER SMS COUNT
# ==========================================================
def get_user_sms_count(
    db: Session,
    user_id: int,
):

    return (
        db.query(models.SMS)
        .filter(
            models.SMS.user_id == user_id
        )
        .count()
    )


# ==========================================================
# TOTAL SMS COUNT
# ==========================================================
def get_total_sms_count(
    db: Session,
):

    return (
        db.query(models.SMS)
        .count()
    )


# ==========================================================
# UNREAD SMS COUNT
# ==========================================================
def get_unread_sms_count(
    db: Session,
    user_id: Optional[int] = None,
):

    query = db.query(models.SMS).filter(
        models.SMS.read.is_(False)
    )

    if user_id is not None:
        query = query.filter(
            models.SMS.user_id == user_id
        )

    return query.count()


# ==========================================================
# USER READ SMS COUNT
# ==========================================================
def get_read_sms_count(
    db: Session,
    user_id: Optional[int] = None,
):

    query = db.query(models.SMS).filter(
        models.SMS.read.is_(True)
    )

    if user_id is not None:
        query = query.filter(
            models.SMS.user_id == user_id
        )

    return query.count()


# ==========================================================
# DELETE ALL USER SMS
# ==========================================================
def delete_all_user_sms(
    db: Session,
    user_id: int,
):

    deleted = (
        db.query(models.SMS)
        .filter(
            models.SMS.user_id == user_id
        )
        .delete(
            synchronize_session=False
        )
    )

    db.commit()

    return deleted


# ==========================================================
# DELETE ALL SMS (ADMIN)
# ==========================================================
def delete_all_sms(
    db: Session,
):

    deleted = (
        db.query(models.SMS)
        .delete(
            synchronize_session=False
        )
    )

    db.commit()

    return deleted