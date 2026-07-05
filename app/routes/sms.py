from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app import auth, models
from app.config import (
    EXTERNAL_ENDPOINT,
    EXTERNAL_TIMEOUT,
    SERVICE_NAME,
    SERVICE_VERSION,
)
from app.idempotency import processed_sms
from app.websocket import manager

import logging
import os
import pytz
import requests

router = APIRouter()
logger = logging.getLogger("sms_backend")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")

nairobi_tz = pytz.timezone("Africa/Nairobi")

# Reuse HTTP connections
session = requests.Session()


def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = auth.decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    return {"username": payload.get("sub")}


@router.get("/health")
async def health():
    """
    Used by Android app before uploading queued SMS.
    """

    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
    }


def send_to_external_endpoint(data: dict):

    try:

        response = session.post(
            EXTERNAL_ENDPOINT,
            json=data,
            timeout=EXTERNAL_TIMEOUT,
        )

        response.raise_for_status()

        external_json = response.json()

        logger.info(
            "External responseId=%s responseTimeStamp=%s",
            external_json.get("responseId"),
            external_json.get("responseTimeStamp"),
        )

        return external_json

    except requests.exceptions.RequestException as e:

        logger.exception("External endpoint failed")

        raise HTTPException(
            status_code=502,
            detail={
                "error": "External endpoint unavailable",
                "message": str(e),
            },
        )


@router.post("/sms/forward")
async def forward_sms(
    sms: models.Sms,
    current_user=Depends(get_current_user),
):

    logger.info(
        "[%s] SMS received from %s",
        sms.id,
        sms.sender,
    )

    # -----------------------------
    # Duplicate protection
    # -----------------------------
    if processed_sms.exists(sms.id):

        logger.info(
            "[%s] Duplicate ignored",
            sms.id,
        )

        return {
            "success": True,
            "duplicate": True,
            "id": sms.id,
        }

    timestamp = (
        sms.timestamp.astimezone(nairobi_tz).isoformat()
        if sms.timestamp
        else None
    )

    sms_payload = {
        "id": sms.id,
        "sender": sms.sender,
        "message": sms.message,
        "device_id": sms.device_id,
        "received_at": sms.received_at,
        "forwarded_by": current_user["username"],
        "role": sms.role or "user",
        "timestamp": timestamp,
    }

    logger.info(
        "[%s] Sending to storage server...",
        sms.id,
    )

    external_response = send_to_external_endpoint(
        sms_payload
    )

    logger.info(
        "[%s] Storage server accepted SMS",
        sms.id,
    )

    processed_sms.add(sms.id)

    broadcast_payload = {
        "id": sms.id,
        "sender": sms.sender,
        "message": sms.message,
        "device_id": sms.device_id,
        "received_at": sms.received_at,
        "forwarded_by": current_user["username"],
        "role": sms.role or "user",
        "timestamp": timestamp,
        "responseId": external_response.get("responseId"),
        "responseTimeStamp": external_response.get(
            "responseTimeStamp"
        ),
        "statusCode": external_response.get(
            "responseParam",
            {},
        ).get("statusCode"),
        "description": external_response.get(
            "responseParam",
            {},
        ).get("description"),
    }

    logger.info(
        "[%s] Broadcasting to dashboard",
        sms.id,
    )

    await manager.broadcast(broadcast_payload)

    logger.info(
        "[%s] Processing completed",
        sms.id,
    )

    return {
        "success": True,
        "id": sms.id,
        "responseId": external_response.get("responseId"),
        "responseTimeStamp": external_response.get(
            "responseTimeStamp"
        ),
    }


@router.get("/sms/list")
async def list_sms(
    current_user=Depends(get_current_user),
):

    try:

        response = session.get(
            EXTERNAL_ENDPOINT,
            timeout=EXTERNAL_TIMEOUT,
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:

        logger.exception(
            "Unable to fetch SMS"
        )

        raise HTTPException(
            status_code=502,
            detail={
                "error": "External endpoint unavailable",
                "message": str(e),
            },
        )