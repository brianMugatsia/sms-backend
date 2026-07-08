from math import ceil
from typing import Optional

from sqlalchemy.orm import Session

from app import models, schemas


# ==========================================================
# SETTINGS
# ==========================================================

def get_settings(db: Session):

    settings = (
        db.query(models.InstanceSettings)
        .filter(models.InstanceSettings.id == 1)
        .first()
    )

    if settings is None:

        settings = models.InstanceSettings(
            id=1,
        )

        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


def update_settings(
    db: Session,
    settings: schemas.EndpointSettings,
):

    instance = get_settings(db)

    instance.storage_endpoint = settings.storage_endpoint
    instance.storage_api_key = settings.storage_api_key

    db.commit()
    db.refresh(instance)

    return instance


# ==========================================================
# CREATE SMS CACHE
# ==========================================================

def create_sms(
    db: Session,
    sms: schemas.SmsCreate,
):

    existing = (
        db.query(models.SMS)
        .filter(models.SMS.id == sms.id)
        .first()
    )

    if existing:
        return existing, True

    sms_record = models.SMS(
        id=sms.id,
        sender=sms.sender,
        message=sms.message,
        device_id=sms.device_id,
        received_at=sms.received_at,
        status="pending",
        forwarded=False,
    )

    db.add(sms_record)
    db.commit()
    db.refresh(sms_record)

    return sms_record, False


# ==========================================================
# UPDATE SUCCESS
# ==========================================================

def mark_success(
    db: Session,
    sms_id: str,
    response_code: int,
):

    sms = (
        db.query(models.SMS)
        .filter(models.SMS.id == sms_id)
        .first()
    )

    if sms is None:
        return None

    sms.status = "success"
    sms.forwarded = True
    sms.response_code = response_code
    sms.error = None

    db.commit()
    db.refresh(sms)

    return sms


# ==========================================================
# UPDATE FAILED
# ==========================================================

def mark_failed(
    db: Session,
    sms_id: str,
    error: str,
):

    sms = (
        db.query(models.SMS)
        .filter(models.SMS.id == sms_id)
        .first()
    )

    if sms is None:
        return None

    sms.status = "failed"
    sms.forwarded = False
    sms.error = error

    db.commit()
    db.refresh(sms)

    return sms


# ==========================================================
# GET SMS
# ==========================================================

def get_sms(
    db: Session,
    sms_id: str,
):

    return (
        db.query(models.SMS)
        .filter(models.SMS.id == sms_id)
        .first()
    )


# ==========================================================
# LIST SMS
# ==========================================================

def list_sms(
    db: Session,
    page: int = 1,
    size: int = 50,
    search: Optional[str] = None,
):

    query = db.query(models.SMS)

    if search:

        query = query.filter(
            (models.SMS.sender.ilike(f"%{search}%"))
            |
            (models.SMS.message.ilike(f"%{search}%"))
        )

    total = query.count()

    pages = ceil(total / size) if total else 1

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

    sms = get_sms(db, sms_id)

    if sms is None:
        return False

    db.delete(sms)
    db.commit()

    return True


# ==========================================================
# CLEAR CACHE
# ==========================================================

def clear_cache(db: Session):

    db.query(models.SMS).delete()

    db.commit()

    return True


# ==========================================================
# COUNTS
# ==========================================================

def dashboard_stats(db: Session):

    pending = (
        db.query(models.SMS)
        .filter(models.SMS.status == "pending")
        .count()
    )

    success = (
        db.query(models.SMS)
        .filter(models.SMS.status == "success")
        .count()
    )

    failed = (
        db.query(models.SMS)
        .filter(models.SMS.status == "failed")
        .count()
    )

    return {
        "pending": pending,
        "success": success,
        "failed": failed,
        "total": pending + success + failed,
    }