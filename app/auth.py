import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

load_dotenv()

# ==========================================================
# JWT SETTINGS
# ==========================================================
SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
)

# ==========================================================
# PASSWORD HASHING
# ==========================================================
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/users/login"
)


# ==========================================================
# PASSWORD HELPERS
# ==========================================================
def verify_password(
    plain_password: str,
    hashed_password: str,
):

    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


def get_password_hash(
    password: str,
):

    return pwd_context.hash(password)


# ==========================================================
# ACCESS TOKEN
# ==========================================================
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
):

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    to_encode.update(
        {
            "exp": expire,
            "type": "access",
        }
    )

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


# ==========================================================
# REFRESH TOKEN
# ==========================================================
def create_refresh_token(
    data: dict,
):

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )

    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",
        }
    )

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


# ==========================================================
# TOKEN DECODER
# ==========================================================
def decode_token(
    token: str,
):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        return payload

    except JWTError:

        return None


# ==========================================================
# CURRENT USER
# ==========================================================
def get_current_user(
    token: str = Depends(oauth2_scheme),
):

    payload = decode_token(token)

    if payload is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    return {
        "user_id": payload.get("user_id"),
        "username": payload.get("sub"),
        "role": payload.get("role", "user"),
        "token_type": payload.get("type", "access"),
    }


# ==========================================================
# REFRESH USER
# ==========================================================
def get_current_refresh_user(
    token: str = Depends(oauth2_scheme),
):

    payload = decode_token(token)

    if payload is None:

        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token",
        )

    if payload.get("type") != "refresh":

        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token",
        )

    return {
        "user_id": payload.get("user_id"),
        "username": payload.get("sub"),
        "role": payload.get("role"),
    }