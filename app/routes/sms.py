from typing import Optional
import logging

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import auth, crud, schemas, models
from app.config import EXTERNAL_ENDPOINT, EXTERNAL_TIMEOUT
from app.database import get_db
from app.websocket import manager

router = APIRouter()

logger = logging.getLogger("sms_backend")
session = requests.Session()






# FORWARD TO USER STORAGE ENDPOINT

def forward_to_external(
    user: models.User,
    payload: dict,
):
    endpoint = user.storage_endpoint

    if not endpoint:
        endpoint = EXTERNAL_ENDPOINT

    if not endpoint:
        return None

    headers = {
        "Content-Type": "application/json",
    }

    if user.storage_api_key:
        headers["X-API-Key"] = user.storage_api_key
    try:
        response = session.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=EXTERNAL_TIMEOUT,
        )

        response.raise_for_status()

        try:
            return response.json()
        except Exception:
            return {"status": response.status_code}

    except requests.RequestException:
        logger.exception("External forwarding failed")
        return None

# ==========================================================
# RECEIVE SMS
# ==========================================================
@router.post("/sms/forward")
async def receive_sms(
    sms: schemas.SmsCreate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):

    sms_record, duplicate = crud.create_sms(
        db=db,
        sms=sms,
        user_id=current_user["user_id"],
    )

    user = crud.get_user_by_id(
        db,
        current_user["user_id"],
    )
     
    if user is None:
       raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
    )
    

    if duplicate:

        return {
            "success": True,
            "duplicate": True,
            "sms": sms_record,
        }

    payload = {
        "id": sms_record.id,
        "sender": sms_record.sender,
        "message": sms_record.message,
        "device_id": sms_record.device_id,
        "user_id": sms_record.user_id,
        "received_at": sms_record.received_at,
        "timestamp": sms_record.timestamp.isoformat(),
        "read": sms_record.read,
    }

    # Broadcast to dashboards
    await manager.broadcast(payload)

    external_response = forward_to_external(
        user=user,
        payload=payload,
    )
    return {
        "success": True,
        "duplicate": False,
        "sms": sms_record,
        "external": external_response,
    }


# ==========================================================
# SMS LIST
# ==========================================================
@router.get(
    "/sms/list",
    response_model=schemas.SmsListResponse,
)
def list_sms(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):

    return crud.list_sms(
        db=db,
        page=page,
        size=size,
        user_id=current_user["user_id"],
        role=current_user["role"],
        search=search,
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
    current_user=Depends(auth.get_current_user),
):

    if current_user["role"] == "admin":

        sms = crud.get_sms(
            db,
            sms_id,
        )

    else:

        sms = crud.get_user_sms(
            db,
            sms_id,
            current_user["user_id"],
        )

    if sms is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SMS not found",
        )

    return sms


# ==========================================================
# DELETE SMS
# ==========================================================
@router.delete(
    "/sms/{sms_id}",
    response_model=schemas.MessageResponse,
)
def delete_sms(
    sms_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):

    if current_user["role"] == "admin":

        sms = crud.get_sms(
            db,
            sms_id,
        )

    else:

        sms = crud.get_user_sms(
            db,
            sms_id,
            current_user["user_id"],
        )

    if sms is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SMS not found",
        )

    crud.delete_sms(
        db,
        sms_id,
    )

    return {
        "success": True,
        "message": "SMS deleted",
    }


# ==========================================================
# MARK READ
# ==========================================================
@router.put(
    "/sms/{sms_id}/read",
    response_model=schemas.SmsResponse,
)
def mark_read(
    sms_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):

    if current_user["role"] != "admin":

        sms = crud.get_user_sms(
            db,
            sms_id,
            current_user["user_id"],
        )

        if sms is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SMS not found",
            )

    sms = crud.mark_sms_read(
        db,
        sms_id,
    )

    if sms is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SMS not found",
        )

    return sms


# ==========================================================
# MARK UNREAD
# ==========================================================
@router.put(
    "/sms/{sms_id}/unread",
    response_model=schemas.SmsResponse,
)
def mark_unread(
    sms_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):

    if current_user["role"] != "admin":

        sms = crud.get_user_sms(
            db,
            sms_id,
            current_user["user_id"],
        )

        if sms is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SMS not found",
            )

    sms = crud.mark_sms_unread(
        db,
        sms_id,
    )

    if sms is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SMS not found",
        )

    return sms