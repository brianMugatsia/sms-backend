from math import ceil
from typing import Optional

from sqlalchemy.orm import Session

from app import models, schemas

from urllib.parse import urlparse

import requests
from requests.exceptions import (
    ConnectionError,
    InvalidURL,
    MissingSchema,
    SSLError,
    Timeout,
)


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
# TEST STORAGE ENDPOINT
# ==========================================================

def test_storage_endpoint(
    endpoint: str,
    api_key: str | None = None,
):
    """
    Tests whether a storage endpoint is reachable.

    Returns:
        {
            "success": bool,
            "message": str,
            "status_code": int | None
        }
    """

    endpoint = (endpoint or "").strip()

    if not endpoint:
        return {
            "success": False,
            "message": "Storage endpoint is required.",
            "status_code": None,
        }

    parsed = urlparse(endpoint)

    if parsed.scheme not in ("http", "https"):
        return {
            "success": False,
            "message": "URL must start with http:// or https://",
            "status_code": None,
        }

    headers = {}

    if api_key:
        headers["X-API-Key"] = api_key

    try:
        response = requests.post(
            endpoint,
            json={"ping": True},
            headers=headers,
            timeout=10,
        )

        if 200 <= response.status_code < 300:
            return {
                "success": True,
                "message": "Connection successful.",
                "status_code": response.status_code,
            }

        if response.status_code == 401:
            return {
                "success": False,
                "message": "Authentication failed (401 Unauthorized).",
                "status_code": response.status_code,
            }

        if response.status_code == 403:
            return {
                "success": False,
                "message": "Access denied (403 Forbidden).",
                "status_code": response.status_code,
            }

        if response.status_code == 404:
            return {
                "success": False,
                "message": "Endpoint not found (404).",
                "status_code": response.status_code,
            }

        return {
            "success": False,
            "message": f"Endpoint returned HTTP {response.status_code}.",
            "status_code": response.status_code,
        }

    except MissingSchema:
        return {
            "success": False,
            "message": "Invalid URL.",
            "status_code": None,
        }

    except InvalidURL:
        return {
            "success": False,
            "message": "Invalid URL.",
            "status_code": None,
        }

    except Timeout:
        return {
            "success": False,
            "message": "Connection timed out.",
            "status_code": None,
        }

    except ConnectionError:
        return {
            "success": False,
            "message": "Unable to connect to the server.",
            "status_code": None,
        }

    except SSLError:
        return {
            "success": False,
            "message": "SSL certificate error.",
            "status_code": None,
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "status_code": None,
        }
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