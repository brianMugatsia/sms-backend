from typing import Optional
import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.config import EXTERNAL_TIMEOUT
from app.database import get_db
from app.websocket import manager

router = APIRouter()
logger = logging.getLogger("sms_backend")

# Shared AsyncClient for connection pooling
async_client = httpx.AsyncClient(timeout=EXTERNAL_TIMEOUT)


# ==========================================================
# FORWARD SMS (ASYNCHRONOUS)
# ==========================================================

async def forward_sms_async(endpoint: str, api_key: Optional[str], payload: dict) -> httpx.Response:
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["X-API-Key"] = api_key

    logger.info(
        "[FORWARD] POST %s | device_id=%s sms_id=%s",
        endpoint,
        payload.get("device_id"),
        payload.get("id"),
    )
    logger.debug("[FORWARD] Payload: %s", payload)

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


# ==========================================================
# RECEIVE SMS
# ==========================================================

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

    # Save to cache database
    sms_record, duplicate = crud.create_sms(db=db, sms=sms)

    if duplicate:
        logger.info(
            "[RECEIVE] Duplicate SMS ignored | sms_id=%s",
            sms.id,
        )
        return {
            "success": True,
            "duplicate": True,
        }

    payload = {
        "id": sms_record.id,
        "sender": sms_record.sender,
        "message": sms_record.message,
        "device_id": sms_record.device_id,
        "received_at": sms_record.received_at,
        "timestamp": sms_record.timestamp.isoformat(),
        "status": "pending",
        "forwarded": False,
        "response_code": None,
        "error": None,
    }

    logger.info("[RECEIVE] Saved SMS as pending | sms_id=%s", sms_record.id)
    
    # Notify connected WebSockets immediately
    await manager.broadcast(payload)

    settings = crud.get_settings(db)
    logger.info(
        "[RECEIVE] Configured storage_endpoint=%s | sms_id=%s",
        settings.storage_endpoint or "<not configured>",
        sms_record.id,
    )

    if not settings.storage_endpoint:
        logger.warning(
            "[RECEIVE] No storage endpoint configured, marking failed | sms_id=%s",
            sms_record.id,
        )
        crud.mark_failed(db, sms_record.id, "No endpoint configured")
        
        updated_sms = crud.get_sms(db, sms_record.id)
        await manager.broadcast(
            schemas.SmsResponse.model_validate(updated_sms).model_dump(mode="json")
        )
        return {
            "success": False,
            "message": "No endpoint configured",
        }

    try:
        # Non-blocking async outbound request
        response = await forward_sms_async(
            settings.storage_endpoint,
            settings.storage_api_key,
            payload,
        )

        logger.info(
            "[RECEIVE] Forward succeeded | sms_id=%s status_code=%s",
            sms_record.id,
            response.status_code,
        )
        crud.mark_success(db, sms_record.id, response.status_code)

    except Exception as e:
        logger.error(
            "[RECEIVE] Forward failed | sms_id=%s endpoint=%s error=%s",
            sms_record.id,
            settings.storage_endpoint,
            str(e),
        )
        logger.exception(e)
        crud.mark_failed(db, sms_record.id, str(e))

    # Retrieve and broadcast finalized status
    final_sms = crud.get_sms(db, sms_record.id)
    logger.info(
        "[RECEIVE] Final status | sms_id=%s status=%s response_code=%s error=%s",
        final_sms.id,
        final_sms.status,
        final_sms.response_code,
        final_sms.error,
    )

    final_payload = schemas.SmsResponse.model_validate(final_sms).model_dump(mode="json")
    await manager.broadcast(final_payload)

    return schemas.SmsResponse.model_validate(final_sms)


# ==========================================================
# OTHER ENDPOINTS (unchanged but cleaned)
# ==========================================================

@router.get("/sms/list", response_model=schemas.SmsListResponse)
def list_sms(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.list_sms(db, page, size, search)


@router.get("/sms/{sms_id}", response_model=schemas.SmsResponse)
def get_sms(sms_id: str, db: Session = Depends(get_db)):
    sms = crud.get_sms(db, sms_id)
    if sms is None:
        raise HTTPException(status_code=404, detail="SMS not found")
    return sms


@router.delete("/sms/{sms_id}")
def delete_sms(sms_id: str, db: Session = Depends(get_db)):
    if not crud.delete_sms(db, sms_id):
        raise HTTPException(status_code=404, detail="SMS not found")
    return {"success": True}


@router.delete("/sms")
def clear_sms(db: Session = Depends(get_db)):
    crud.clear_cache(db)
    return {"success": True, "message": "Dashboard cache cleared"}


@router.get("/sms/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    return crud.dashboard_stats(db)