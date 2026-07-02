from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from app import models, auth
from app.websocket import manager
import logging
import pytz
import requests

router = APIRouter()
logger = logging.getLogger("sms_backend")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")
nairobi_tz = pytz.timezone("Africa/Nairobi")

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = auth.decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"username": payload.get("sub")}

def send_to_external_endpoint(data: dict):
    url = "https://endpint.roberms.com/roberms/aop/"
    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        external_json = response.json()

        # Log responseId and responseTimeStamp if present
        resp_id = external_json.get("responseId")
        resp_ts = external_json.get("responseTimeStamp")
        logger.info(f"External response: responseId={resp_id}, responseTimeStamp={resp_ts}")

        return external_json
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send SMS to external endpoint: {e}")
        return {"error": "External endpoint unreachable", "detail": str(e)}

@router.post("/sms/forward")
async def forward_sms(sms: models.Sms, current_user=Depends(get_current_user)):
    sms_payload = {
        "sender": sms.sender,
        "message": sms.message,
        "device_id": sms.device_id,
        "forwarded_by": current_user["username"],
        "role": sms.role or "user",
        "timestamp": sms.timestamp.astimezone(nairobi_tz).isoformat() if sms.timestamp else None
    }

    external_response = send_to_external_endpoint(sms_payload)

    # Flattened broadcast payload for frontend
    broadcast_payload = {
        "sender": sms_payload["sender"],
        "message": sms_payload["message"],
        "device_id": sms_payload["device_id"],
        "forwarded_by": sms_payload["forwarded_by"],
        "role": sms_payload["role"],
        "timestamp": sms_payload["timestamp"],
        "responseId": external_response.get("responseId"),
        "responseTimeStamp": external_response.get("responseTimeStamp"),
        "statusCode": external_response.get("responseParam", {}).get("statusCode"),
        "description": external_response.get("responseParam", {}).get("description"),
    }

    logger.info(f"Broadcasting flattened SMS payload: {broadcast_payload}")
    await manager.broadcast(broadcast_payload)

    if "error" in external_response:
        raise HTTPException(status_code=502, detail=external_response)

    return {"status": "SMS sent to external endpoint", "external_response": external_response}

@router.get("/sms/list")
async def list_sms(current_user=Depends(get_current_user)):
    url = "https://endpint.roberms.com/roberms/aop/"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        external_json = response.json()

        # Log responseId and responseTimeStamp if present
        resp_id = external_json.get("responseId")
        resp_ts = external_json.get("responseTimeStamp")
        logger.info(f"External list response: responseId={resp_id}, responseTimeStamp={resp_ts}")

        return external_json
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch SMS from external endpoint: {e}")
        raise HTTPException(status_code=502, detail={"error": "External endpoint unreachable", "detail": str(e)})
