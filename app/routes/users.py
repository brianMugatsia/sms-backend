from datetime import timedelta
import logging

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app import auth, models
from app.config import (
    EXTERNAL_ENDPOINT,
    EXTERNAL_TIMEOUT,
)

router = APIRouter()
logger = logging.getLogger("sms_backend")

# ---------------------------------------------------------
# Shared HTTP session
# ---------------------------------------------------------
session = requests.Session()


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

        logger.exception("External endpoint unavailable")

        raise HTTPException(
            status_code=502,
            detail={
                "error": "External endpoint unavailable",
                "message": str(e),
            },
        )


# ---------------------------------------------------------
# Register
# ---------------------------------------------------------
@router.post("/users/register")
async def register_user(user: models.User):

    payload = {
        "username": user.username,
        "email": user.email,
        "password": user.password,
        "role": user.role,
        "endpoint_url": user.endpoint_url,
    }

    logger.info(
        "Registering user %s",
        user.username,
    )

    external_response = send_to_external_endpoint(payload)

    return {
        "success": True,
        "responseId": external_response.get("responseId"),
        "responseTimeStamp": external_response.get(
            "responseTimeStamp"
        ),
    }


# ---------------------------------------------------------
# Login
# ---------------------------------------------------------
@router.post("/users/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
):

    logger.info(
        "Login requested by %s",
        form_data.username,
    )

    #
    # In production this should validate against
    # your authentication service/database.
    #

    access_token = auth.create_access_token(
        data={
            "sub": form_data.username,
            "role": "user",
        },
        expires_delta=timedelta(minutes=30),
    )

    refresh_token = auth.create_refresh_token(
        {
            "sub": form_data.username,
            "role": "user",
        }
    )

    logger.info(
        "Login successful for %s",
        form_data.username,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 1800,
    }


# ---------------------------------------------------------
# Refresh Token
# ---------------------------------------------------------
@router.post("/users/refresh")
async def refresh_token(
    current_user=Depends(auth.get_current_user),
):

    logger.info(
        "Refreshing token for %s",
        current_user["username"],
    )

    access_token = auth.create_access_token(
        data={
            "sub": current_user["username"],
            "role": current_user["role"],
        },
        expires_delta=timedelta(minutes=30),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800,
    }


# ---------------------------------------------------------
# Current User
# ---------------------------------------------------------
@router.get("/users/me")
async def current_user(
    user=Depends(auth.get_current_user),
):

    return {
        "username": user["username"],
        "role": user["role"],
    }