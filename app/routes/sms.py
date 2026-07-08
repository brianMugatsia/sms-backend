from typing import Optional
import logging

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.config import EXTERNAL_TIMEOUT
from app.database import get_db
from app.websocket import manager

router = APIRouter()

logger = logging.getLogger("sms_backend")
session = requests.Session()


# ==========================================================
# FORWARD SMS
# ==========================================================

def forward_sms(endpoint, api_key, payload):

    headers = {
        "Content-Type": "application/json",
    }

    if api_key:
        headers["X-API-Key"] = api_key

    response = session.post(
        endpoint,
        json=payload,
        headers=headers,
        timeout=EXTERNAL_TIMEOUT,
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

    # --------------------------------------------
    # Save to dashboard cache
    # --------------------------------------------

    sms_record, duplicate = crud.create_sms(
        db=db,
        sms=sms,
    )

    if duplicate:

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

    # --------------------------------------------
    # Dashboard immediately sees pending SMS
    # --------------------------------------------

    await manager.broadcast(payload)

    settings = crud.get_settings(db)

    if not settings.storage_endpoint:

        crud.mark_failed(
            db,
            sms_record.id,
            "No endpoint configured",
        )

        sms = crud.get_sms(db, sms_record.id)

        await manager.broadcast(schemas.SmsResponse.model_validate(sms).model_dump())

        return {
            "success": False,
            "message": "No endpoint configured",
        }

    try:

        response = forward_sms(
            settings.storage_endpoint,
            settings.storage_api_key,
            payload,
        )

        crud.mark_success(
            db,
            sms_record.id,
            response.status_code,
        )

    except Exception as e:

        logger.exception(e)

        crud.mark_failed(
            db,
            sms_record.id,
            str(e),
        )

    sms = crud.get_sms(
        db,
        sms_record.id,
    )

    await manager.broadcast(
        schemas.SmsResponse.model_validate(sms).model_dump()
    )

    return schemas.SmsResponse.model_validate(sms)


# ==========================================================
# SMS LIST
# ==========================================================

@router.get(
    "/sms/list",
    response_model=schemas.SmsListResponse,
)
def list_sms(
    page: int = Query(1),
    size: int = Query(50),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):

    return crud.list_sms(
        db,
        page,
        size,
        search,
    )


# ==========================================================
# GET SMS
# ==========================================================

@router.get(
    "/sms/{sms_id}",
    response_model=schemas.SmsResponse,
)
def get_sms(
    sms_id: str,
    db: Session = Depends(get_db),
):

    sms = crud.get_sms(
        db,
        sms_id,
    )

    if sms is None:

        raise HTTPException(
            status_code=404,
            detail="SMS not found",
        )

    return sms


# ==========================================================
# DELETE ONE SMS
# ==========================================================

@router.delete(
    "/sms/{sms_id}",
)
def delete_sms(
    sms_id: str,
    db: Session = Depends(get_db),
):

    if not crud.delete_sms(
        db,
        sms_id,
    ):

        raise HTTPException(
            status_code=404,
            detail="SMS not found",
        )

    return {
        "success": True,
    }


# ==========================================================
# CLEAR CACHE
# ==========================================================

@router.delete("/sms")
def clear_sms(
    db: Session = Depends(get_db),
):

    crud.clear_cache(db)

    return {
        "success": True,
        "message": "Dashboard cache cleared",
    }


# ==========================================================
# DASHBOARD STATS
# ==========================================================

@router.get("/sms/stats")
def dashboard_stats(
    db: Session = Depends(get_db),
):

    return crud.dashboard_stats(db)