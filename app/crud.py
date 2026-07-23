from datetime import datetime
import logging
from math import ceil
import time
from typing import Optional
from sqlalchemy.orm import Session
from urllib.parse import urlparse
import requests
from requests.exceptions import (
    ConnectionError,
    InvalidURL,
    MissingSchema,
    SSLError,
    Timeout,
)

from app import models, schemas


# ==========================================================
# UTILS / HELPER FUNCTIONS
# ==========================================================

def parse_ms_timestamp(val) -> Optional[str]:
    """
    Safely converts incoming millisecond or second epoch timestamps
    into a standardized string (YYYY-MM-DD HH:MM:SS) for DateTime columns.
    """
    if val is None:
        return None
    try:
        val_float = float(val)
        if len(str(int(val_float))) >= 13:
            val_float = val_float / 1000.0

        dt = datetime.fromtimestamp(val_float)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logging.error(f"Failed to parse timestamp {val}: {e}")
        return None


def parse_epoch_int(val) -> Optional[int]:
    """
    Safely converts incoming epoch timestamps (seconds or milliseconds)
    into a standardized epoch-milliseconds integer, for BigInteger columns
    like `received_at`.
    """
    if val is None:
        return None
    try:
        val_float = float(val)
        if len(str(int(val_float))) < 13:
            val_float = val_float * 1000.0
        return int(val_float)
    except Exception as e:
        logging.error(f"Failed to parse epoch int {val}: {e}")
        return None


# ==========================================================
# SETTINGS
# ==========================================================

def get_settings(db: Session) -> models.InstanceSettings:
    settings = (
        db.query(models.InstanceSettings)
        .filter(models.InstanceSettings.id == 1)
        .first()
    )

    if settings is None:
        settings = models.InstanceSettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


def update_settings(db: Session, settings: schemas.EndpointSettings) -> models.InstanceSettings:
    instance = get_settings(db)
    instance.storage_endpoint = settings.storage_endpoint
    instance.storage_api_key = settings.storage_api_key
    db.commit()
    db.refresh(instance)
    return instance


# ==========================================================
# TEST STORAGE ENDPOINT
# ==========================================================

def test_storage_endpoint(endpoint: str, api_key: Optional[str] = None) -> dict:
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

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    is_unitas = "unitas/payment" in endpoint

    if is_unitas:
        payload = {
            "id": "00000000-0000-0000-0000-000000000000",
            "sender": "TEST_PING",
            "message": "This is a backend test connection",
            "device_id": "fastapi-backend-test",
            "received_at": int(time.time() * 1000)
        }
    else:
        payload = {"ping": True}

    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=10,
        )

        try:
            res_json = response.json()
            status_text = res_json.get("status")
        except Exception:
            res_json = {}
            status_text = None

        is_success = (
            (200 <= response.status_code < 300) or
            status_text in ["success", "duplicate"]
        )

        if is_success:
            message = "Connection successful."
            if status_text == "duplicate":
                message = "Endpoint verified (Duplicate transaction test caught successfully)."
            elif res_json.get("message"):
                message = res_json.get("message")

            return {
                "success": True,
                "message": message,
                "status_code": response.status_code,
            }

        status_messages = {
            401: "Authentication failed (401 Unauthorized).",
            403: "Access denied (403 Forbidden).",
            404: "Endpoint not found (404).",
        }

        if status_text in ["success", "duplicate"]:
            return {
                "success": True,
                "message": "Endpoint verified.",
                "status_code": response.status_code,
            }

        return {
            "success": False,
            "message": status_messages.get(response.status_code, f"Endpoint returned HTTP {response.status_code}."),
            "status_code": response.status_code,
        }

    except (MissingSchema, InvalidURL):
        return {"success": False, "message": "Invalid URL.", "status_code": None}
    except Timeout:
        return {"success": False, "message": "Connection timed out.", "status_code": None}
    except ConnectionError:
        return {"success": False, "message": "Unable to connect to the server.", "status_code": None}
    except SSLError:
        return {"success": False, "message": "SSL certificate error.", "status_code": None}
    except Exception as e:
        return {"success": False, "message": str(e), "status_code": None}


# ==========================================================
# CREATE SMS CACHE
# ==========================================================

def create_sms(db: Session, sms: schemas.SmsCreate) -> tuple[models.SMS, bool]:
    # Intentionally NOT filtering by `deleted` here — if the same sms.id
    # comes in again (retry/duplicate from the native worker), we want to
    # recognize it as existing even if the user had soft-deleted it,
    # rather than creating a second row with the same id.
    existing = db.query(models.SMS).filter(models.SMS.id == sms.id).first()
    if existing:
        return existing, True

    raw_received = getattr(sms, "received_at", None)
    raw_timestamp = getattr(sms, "timestamp", None) or raw_received

    now_dt = datetime.utcnow()
    now_ms = int(now_dt.timestamp() * 1000)

    parsed_received = parse_epoch_int(raw_received)
    if parsed_received is None:
        parsed_received = now_ms

    parsed_timestamp_str = parse_ms_timestamp(raw_timestamp)
    if parsed_timestamp_str:
        parsed_timestamp = datetime.strptime(parsed_timestamp_str, '%Y-%m-%d %H:%M:%S')
    else:
        parsed_timestamp = now_dt

    sms_record = models.SMS(
        id=sms.id,
        sender=sms.sender,
        message=sms.message,
        device_id=sms.device_id,
        received_at=parsed_received,
        timestamp=parsed_timestamp,
        status="pending",
        forwarded=False,
        deleted=False,
    )

    db.add(sms_record)
    db.commit()
    db.refresh(sms_record)
    return sms_record, False


# ==========================================================
# STATUS MODIFIERS
# ==========================================================

def mark_success(db: Session, sms_id: str, response_code: int) -> Optional[models.SMS]:
    sms = db.query(models.SMS).filter(models.SMS.id == sms_id).first()
    if sms is None:
        return None

    sms.status = "success"
    sms.forwarded = True
    sms.response_code = response_code
    sms.error = None

    db.commit()
    db.refresh(sms)
    return sms


def mark_failed(db: Session, sms_id: str, error: str) -> Optional[models.SMS]:
    sms = db.query(models.SMS).filter(models.SMS.id == sms_id).first()
    if sms is None:
        return None

    sms.status = "failed"
    sms.forwarded = False
    sms.error = error

    db.commit()
    db.refresh(sms)
    return sms


# ==========================================================
# RETRIEVAL & UTILITIES (scoped by device_id, soft-delete aware)
# ==========================================================

def get_sms(db: Session, sms_id: str, device_id: str) -> Optional[models.SMS]:
    return (
        db.query(models.SMS)
        .filter(
            models.SMS.id == sms_id,
            models.SMS.device_id == device_id,
            models.SMS.deleted == False,
        )
        .first()
    )


def list_sms(
    db: Session,
    device_id: str,
    page: int = 1,
    size: int = 50,
    search: Optional[str] = None,
) -> dict:
    query = db.query(models.SMS).filter(
        models.SMS.device_id == device_id,
        models.SMS.deleted == False,
    )

    if search:
        query = query.filter(
            (models.SMS.sender.ilike(f"%{search}%"))
            | (models.SMS.message.ilike(f"%{search}%"))
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


def delete_sms(db: Session, sms_id: str, device_id: str) -> bool:
    """
    Soft delete: the row is NEVER removed from the database. It's only
    flagged as `deleted`, which hides it from this device's dashboard
    going forward. The record is retained permanently for future reference.
    """
    sms = get_sms(db, sms_id, device_id)
    if sms is None:
        return False

    sms.deleted = True
    db.commit()
    return True


def clear_cache(db: Session, device_id: str) -> bool:
    """
    "Clear all" for a device — soft-deletes every non-deleted row belonging
    to that device_id. Nothing is physically removed from the database.
    """
    db.query(models.SMS).filter(
        models.SMS.device_id == device_id,
        models.SMS.deleted == False,
    ).update({"deleted": True})
    db.commit()
    return True


def dashboard_stats(db: Session, device_id: str) -> dict:
    base = db.query(models.SMS).filter(
        models.SMS.device_id == device_id,
        models.SMS.deleted == False,
    )

    pending = base.filter(models.SMS.status == "pending").count()
    success = base.filter(models.SMS.status == "success").count()
    failed = base.filter(models.SMS.status == "failed").count()

    return {
        "pending": pending,
        "success": success,
        "failed": failed,
        "total": pending + success + failed,
    }