import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# ---------------------------------------------------------
# Load Environment
# ---------------------------------------------------------
load_dotenv()

logger = logging.getLogger("sms_backend")

# ---------------------------------------------------------
# JWT Configuration
# ---------------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET", "fallback-secret")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
)

# ---------------------------------------------------------
# Password Hashing
# ---------------------------------------------------------
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)

# ---------------------------------------------------------
# OAuth2
# ---------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/users/login"
)

# ---------------------------------------------------------
# Password Helpers
# ---------------------------------------------------------
def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ---------------------------------------------------------
# JWT Helpers
# ---------------------------------------------------------
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:

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


def create_refresh_token(
    data: dict,
) -> str:

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


def decode_access_token(
    token: str,
):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        return payload

    except JWTError as e:

        logger.warning(
            "JWT decode failed: %s",
            str(e),
        )

        return None


# ---------------------------------------------------------
# Authentication Dependency
# ---------------------------------------------------------
def get_current_user(
    token: str = Depends(oauth2_scheme),
):

    payload = decode_access_token(token)

    if payload is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    username = payload.get("sub")

    if not username:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    return {
        "username": username,
        "role": payload.get("role", "user"),
        "token_type": payload.get("type", "access"),
    }