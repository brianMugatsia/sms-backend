from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, crud, database, auth
from datetime import timedelta
from app.auth import get_current_user

from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/users/register")
async def register_user(user: models.User, db: Session = Depends(get_db)):
    saved = crud.create_user(db, user)
    return {"status": "User registered", "id": saved.id}

@router.post("/users/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = crud.authenticate_user(
        db,
        form_data.username,
        form_data.password
    )

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = auth.create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=30)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/users/refresh")
async def refresh_token(current_user=Depends(get_current_user)):
    new_access_token = auth.create_access_token(
        data={"sub": current_user.username},
        expires_delta=timedelta(minutes=30)
    )
    return {"access_token": new_access_token, "token_type": "bearer"}
