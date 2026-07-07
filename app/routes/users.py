from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import auth, crud, schemas
from app.database import get_db

router = APIRouter()


# ==========================================================
# REGISTER
# ==========================================================
@router.post(
    "/users/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    try:
        return crud.create_user(db, user)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ==========================================================
# LOGIN
# ==========================================================
@router.post(
    "/users/login",
    response_model=schemas.TokenResponse,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = crud.authenticate_user(
        db,
        form_data.username,
        form_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    access_token = auth.create_access_token(
        {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role,
        },
        expires_delta=timedelta(minutes=30),
    )

    refresh_token = auth.create_refresh_token(
        {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role,
        }
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 1800,
    }


# ==========================================================
# REFRESH TOKEN
# ==========================================================
@router.post("/users/refresh")
def refresh_token(
    current_user=Depends(auth.get_current_refresh_user),
):
    access_token = auth.create_access_token(
        {
            "sub": current_user["username"],
            "user_id": current_user["user_id"],
            "role": current_user["role"],
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800,
    }


# ==========================================================
# CURRENT USER
# ==========================================================
@router.get(
    "/users/me",
    response_model=schemas.UserResponse,
)
def current_user(
    db: Session = Depends(get_db),
    token_user=Depends(auth.get_current_user),
):
    user = crud.get_user_by_id(
        db,
        token_user["user_id"],
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return user


# ==========================================================
# GET USER ENDPOINT SETTINGS
# ==========================================================
@router.get(
    "/users/endpoints",
    response_model=schemas.EndpointSettings,
)
def get_endpoint_settings(
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    user = crud.get_endpoint_settings(
        db,
        current_user["user_id"],
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return schemas.EndpointSettings(
        storage_endpoint=user.storage_endpoint,
        storage_api_key=user.storage_api_key,
        dashboard_endpoint=user.dashboard_endpoint,
        dashboard_api_key=user.dashboard_api_key,
    )


# ==========================================================
# UPDATE USER ENDPOINT SETTINGS
# ==========================================================
@router.put(
    "/users/endpoints",
    response_model=schemas.EndpointSettings,
)
def update_endpoint_settings(
    settings: schemas.EndpointSettings,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    user = crud.update_endpoint_settings(
        db=db,
        user_id=current_user["user_id"],
        settings=settings,
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return schemas.EndpointSettings(
        storage_endpoint=user.storage_endpoint,
        storage_api_key=user.storage_api_key,
        dashboard_endpoint=user.dashboard_endpoint,
        dashboard_api_key=user.dashboard_api_key,
    )


# ==========================================================
# LIST USERS (ADMIN)
# ==========================================================
@router.get(
    "/users",
    response_model=list[schemas.UserResponse],
)
def list_users(
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return crud.get_users(db)