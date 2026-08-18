from typing import Optional
import logging
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.config import EXTERNAL_TIMEOUT
from app.database import get_db
from app.websocket import manager

router = APIRouter()
logger = logging.getLogger("sms_backend")

async_client = httpx.AsyncClient(timeout=EXTERNAL_TIMEOUT)


def to_iso_string(val) -> str:
    """Safely converts datetime objects, epoch numbers, or string integers into an ISO 8601 string."""
    if val is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, (int, float)):
        ts = val / 1000.0 if val > 1e11 else float(val)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    if isinstance(val, str):
        val_str = val.strip()
        if val_str.isdigit() or (val_str.replace(".", "", 1).isdigit() and val_str.count(".") < 2):
            ts = float(val_str)
            ts = ts / 1000.0 if ts > 1e11 else ts
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        return val_str
    return datetime.now(timezone.utc).isoformat()


async def forward_sms_async(endpoint: str, api_key: Optional[str], payload: dict) -> httpx.Response:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    logger.info(
        "[FORWARD] POST %s | device_id=%s sms_id=%s",
        endpoint,
        payload.get("device_id"),
        payload.get("id"),
    )

    response = await async_client.post(
        endpoint,
        json=payload,
        headers=headers,
    )

    logger.info(
        "[FORWARD] Response status=%s | sms_id=%s",
        response.status_code,
        payload.get("id"),
    )

    try:
        body_preview = response.text[:1000]
    except Exception:
        body_preview = "<unreadable response body>"

    logger.info(
        "[FORWARD] Response body (truncated to 1000 chars): %s",
        body_preview,
    )

    response.raise_for_status()
    return response


@router.post("/sms/forward")
async def receive_sms(
    sms: schemas.SmsCreate,
    db: Session = Depends(get_db),
):
    logger.info(
        "[RECEIVE] Incoming SMS from device_id=%s sender=%s sms_id=%s",
        sms.device_id,
        sms.sender,
        sms.id,
    )

    sms_record, duplicate = crud.create_sms(db=db, sms=sms)

    if duplicate:
        logger.info("[RECEIVE] Duplicate SMS ignored | sms_id=%s", sms.id)
        return {"success": True, "duplicate": True}

    # Safe timestamp handling for both received_at and timestamp fields
    received_at_iso = to_iso_string(getattr(sms_record, "received_at", None))
    timestamp_iso = to_iso_string(getattr(sms_record, "timestamp", None))

    payload = {
        "id": sms_record.id,
        "sender": sms_record.sender,
        "message": sms_record.message,
        "device_id": sms_record.device_id,
        "received_at": received_at_iso,
        "timestamp": timestamp_iso,
        "status": "pending",
        "forwarded": False,
        "response_code": None,
        "error": None,
    }

    logger.info("[RECEIVE] Saved SMS as pending | sms_id=%s", sms_record.id)

    # Broadcast to device-specific WebSocket pool
    await manager.broadcast_to_device(sms_record.device_id, payload)

    # Device-scoped Settings lookup
    settings = crud.get_settings(db, sms_record.device_id)
    logger.info(
        "[RECEIVE] Configured storage_endpoint=%s | device_id=%s sms_id=%s",
        settings.storage_endpoint or "<not configured>",
        sms_record.device_id,
        sms_record.id,
    )

    if not settings.storage_endpoint:
        logger.warning(
            "[RECEIVE] No storage endpoint configured, marking failed | device_id=%s sms_id=%s",
            sms_record.device_id,
            sms_record.id,
        )
        crud.mark_failed(db, sms_record.id, "No endpoint configured")

        updated_sms = crud.get_sms(db, sms_record.id, sms_record.device_id)
        await manager.broadcast_to_device(
            sms_record.device_id,
            schemas.SmsResponse.model_validate(updated_sms).model_dump(mode="json"),
        )
        return {"success": False, "message": "No endpoint configured"}

    try:
        response = await forward_sms_async(
            settings.storage_endpoint,
            settings.storage_api_key,
            payload,
        )

        logger.info(
            "[RECEIVE] Forward succeeded | device_id=%s sms_id=%s status_code=%s",
            sms_record.device_id,
            sms_record.id,
            response.status_code,
        )
        crud.mark_success(db, sms_record.id, response.status_code)

    except httpx.HTTPStatusError as e:
        # Extract the exact response body text returned by the destination endpoint
        response_text = e.response.text if e.response is not None else str(e)
        error_message = f"HTTP {e.response.status_code}: {response_text[:300]}"

        logger.error(
            "[RECEIVE] Forward HTTP error | device_id=%s sms_id=%s status=%s detail=%s",
            sms_record.device_id,
            sms_record.id,
            e.response.status_code if e.response else "N/A",
            response_text[:500],
        )
        crud.mark_failed(db, sms_record.id, error_message)

    except httpx.RequestError as e:
        # Network errors (DNS failure, timeout, host unreachable)
        logger.error(
            "[RECEIVE] Forward network failure | device_id=%s sms_id=%s error=%s",
            sms_record.device_id,
            sms_record.id,
            str(e),
        )
        crud.mark_failed(db, sms_record.id, f"Network Error: {str(e)[:250]}")

    except Exception as e:
        # Unexpected internal runtime errors
        logger.error(
            "[RECEIVE] Forward unexpected error | device_id=%s sms_id=%s error=%s",
            sms_record.device_id,
            sms_record.id,
            str(e),
        )
        logger.exception(e)
        crud.mark_failed(db, sms_record.id, f"Unexpected Error: {str(e)[:250]}")

    final_sms = crud.get_sms(db, sms_record.id, sms_record.device_id)
    final_payload = schemas.SmsResponse.model_validate(final_sms).model_dump(mode="json")

    await manager.broadcast_to_device(final_sms.device_id, final_payload)

    return schemas.SmsResponse.model_validate(final_sms)


# ==========================================================
# QUERY ENDPOINTS
# ==========================================================

@router.get("/sms/list", response_model=schemas.SmsListResponse)
def list_sms(
    device_id: str = Query(...),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.list_sms(db, device_id, page, size, search)


@router.get("/sms", response_model=schemas.SmsListResponse)
@router.get("/sms/", response_model=schemas.SmsListResponse, include_in_schema=False)
def dashboard_refresh_alias(
    device_id: str = Query(...),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.list_sms(db, device_id, page, size, search)


@router.get("/sms/{sms_id}", response_model=schemas.SmsResponse)
def get_sms(sms_id: str, device_id: str = Query(...), db: Session = Depends(get_db)):
    sms = crud.get_sms(db, sms_id, device_id)
    if sms is None:
        raise HTTPException(status_code=404, detail="SMS not found")
    return sms


@router.delete("/sms/{sms_id}")
def delete_sms(sms_id: str, device_id: str = Query(...), db: Session = Depends(get_db)):
    if not crud.delete_sms(db, sms_id, device_id):
        raise HTTPException(status_code=404, detail="SMS not found")
    return {"success": True}


@router.delete("/sms")
def clear_sms(device_id: str = Query(...), db: Session = Depends(get_db)):
    crud.clear_cache(db, device_id)
    return {"success": True, "message": "Dashboard cache cleared"}


@router.get("/sms/stats")
def dashboard_stats(device_id: str = Query(...), db: Session = Depends(get_db)):
    return crud.dashboard_stats(db, device_id)