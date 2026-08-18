from datetime import datetime, timezone
import logging
from math import ceil
import time
from typing import Optional
import httpx
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app import models, schemas

logger = logging.getLogger("sms_backend")

# Shared async client for endpoint validation
async_client = httpx.AsyncClient(timeout=10.0)


# ==========================================================
# UTILS / HELPER FUNCTIONS
# ==========================================================

def parse_ms_timestamp(val) -> Optional[datetime]:
    if val is None:
        return None
    try:
        val_float = float(val)
        if len(str(int(val_float))) >= 13:
            val_float = val_float / 1000.0

        return datetime.fromtimestamp(val_float, tz=timezone.utc)
    except Exception as e:
        logger.error(f"Failed to parse timestamp {val}: {e}")
        return None


def parse_epoch_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        val_float = float(val)
        if len(str(int(val_float))) < 13:
            val_float = val_float * 1000.0
        return int(val_float)
    except Exception as e:
        logger.error(f"Failed to parse epoch int {val}: {e}")
        return None


# ==========================================================
# SETTINGS (Per-Device)
# ==========================================================

def get_settings(db: Session, device_id: str) -> models.InstanceSettings:
    settings = (
        db.query(models.InstanceSettings)
        .filter(models.InstanceSettings.device_id == device_id)
        .first()
    )

    if settings is None:
        settings = models.InstanceSettings(device_id=device_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


def update_settings(
    db: Session,
    device_id: str,
    settings: schemas.EndpointSettings,
) -> models.InstanceSettings:
    instance = get_settings(db, device_id)
    instance.storage_endpoint = settings.storage_endpoint
    instance.storage_api_key = settings.storage_api_key
    db.commit()
    db.refresh(instance)
    return instance


# ==========================================================
# ASYNC TEST STORAGE ENDPOINT
# ==========================================================

async def test_storage_endpoint_async(
    endpoint: str, api_key: Optional[str] = None
) -> dict:
    endpoint = (endpoint or "").strip()

    if not endpoint:
        return {
            "success": False,
            "message": "Storage endpoint is required.",
            "status_code": None,
        }

    if not (endpoint.startswith("http://") or endpoint.startswith("https://")):
        return {
            "success": False,
            "message": "URL must start with http:// or https://",
            "status_code": None,
        }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    # Format ISO 8601 string with UTC offset for backends expecting strict datetime fields
    now_iso = datetime.now(timezone.utc).isoformat()

    payload = {
        "id": "00000000-0000-0000-0000-000000000000",
        "sender": "TEST_PING",
        "message": "This is a backend test connection",
        "device_id": "fastapi-backend-test",
        "received_at": now_iso,
        "timestamp": now_iso,
    }

    try:
        response = await async_client.post(
            endpoint,
            json=payload,
            headers=headers,
        )

        try:
            res_json = response.json()
            status_text = res_json.get("status")
        except Exception:
            res_json = {}
            status_text = None

        is_success = (200 <= response.status_code < 300) or status_text in [
            "success",
            "duplicate",
        ]

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
            500: "Upstream server error (500 Internal Server Error).",
        }

        err_msg = status_messages.get(
            response.status_code, f"Endpoint returned HTTP {response.status_code}."
        )
        logger.warning(f"Storage endpoint test failed for {endpoint} with status {response.status_code}: {err_msg}")

        return {
            "success": False,
            "message": err_msg,
            "status_code": response.status_code,
        }

    except httpx.TimeoutException:
        logger.error(f"Storage endpoint connection timed out for {endpoint}")
        return {"success": False, "message": "Connection timed out.", "status_code": None}
    except httpx.RequestError as e:
        logger.error(f"Network error testing storage endpoint {endpoint}: {e}")
        return {"success": False, "message": f"Network error: {str(e)}", "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error testing storage endpoint {endpoint}: {e}")
        return {"success": False, "message": str(e), "status_code": None}


# ==========================================================
# CREATE & UPDATE SMS
# ==========================================================

def create_sms(db: Session, sms: schemas.SmsCreate) -> tuple[models.SMS, bool]:
    existing = db.query(models.SMS).filter(models.SMS.id == sms.id).first()
    if existing:
        return existing, True

    raw_received = sms.received_at
    now_dt = datetime.now(timezone.utc)
    now_ms = int(now_dt.timestamp() * 1000)

    parsed_received = parse_epoch_int(raw_received) or now_ms
    parsed_timestamp = parse_ms_timestamp(raw_received) or now_dt

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


def mark_success(db: Session, sms_id: str, response_code: int) -> Optional[models.SMS]:
    sms = db.query(models.SMS).filter(models.SMS.id == sms_id).first()
    if not sms:
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
    if not sms:
        return None

    sms.status = "failed"
    sms.forwarded = False
    sms.error = error

    db.commit()
    db.refresh(sms)
    return sms


# ==========================================================
# RETRIEVAL & UTILITIES
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
        search_pattern = f"%{search}%"
        query = query.filter(
            (models.SMS.sender.ilike(search_pattern))
            | (models.SMS.message.ilike(search_pattern))
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
    sms = get_sms(db, sms_id, device_id)
    if not sms:
        return False

    sms.deleted = True
    db.commit()
    return True


def clear_cache(db: Session, device_id: str) -> bool:
    db.query(models.SMS).filter(
        models.SMS.device_id == device_id,
        models.SMS.deleted == False,
    ).update({"deleted": True}, synchronize_session=False)
    db.commit()
    return True


def dashboard_stats(db: Session, device_id: str) -> dict:
    # Single-query conditional aggregation
    stats = (
        db.query(
            func.coalesce(func.sum(case((models.SMS.status == "pending", 1), else_=0)), 0).label("pending"),
            func.coalesce(func.sum(case((models.SMS.status == "success", 1), else_=0)), 0).label("success"),
            func.coalesce(func.sum(case((models.SMS.status == "failed", 1), else_=0)), 0).label("failed"),
        )
        .filter(
            models.SMS.device_id == device_id,
            models.SMS.deleted == False,
        )
        .first()
    )

    pending = int(stats.pending) if stats else 0
    success = int(stats.success) if stats else 0
    failed = int(stats.failed) if stats else 0

    return {
        "pending": pending,
        "success": success,
        "failed": failed,
        "total": pending + success + failed,
    }