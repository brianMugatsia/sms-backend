from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app import models, auth
import requests
import logging

router = APIRouter()
logger = logging.getLogger("sms_backend")

def send_to_external_endpoint(data: dict):
    url = "https://endpint.roberms.com/roberms/aop/"
    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        external_json = response.json()

        # Log responseId and responseTimeStamp if present
        resp_id = external_json.get("responseId")
        resp_ts = external_json.get("responseTimeStamp")
        logger.info(f"External user response: responseId={resp_id}, responseTimeStamp={resp_ts}")

        return external_json
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send user data to external endpoint: {e}")
        return {"error": "External endpoint unreachable", "detail": str(e)}

@router.post("/users/register")
async def register_user(user: models.User):
    external_response = send_to_external_endpoint(user.dict())
    if "error" in external_response:
        raise HTTPException(status_code=502, detail=external_response)
    return {"status": "User forwarded to external endpoint", "external_response": external_response}

@router.post("/users/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    access_token = auth.create_access_token(
        data={"sub": form_data.username},
        expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}

#  New refresh endpoint
@router.post("/users/refresh")
async def refresh_token(current_user=Depends(auth.get_current_user)):
    try:
        new_token = auth.create_access_token(
            data={"sub": current_user["username"]},
            expires_delta=timedelta(minutes=30)
        )
        return {"access_token": new_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(status_code=401, detail="Could not refresh token")
