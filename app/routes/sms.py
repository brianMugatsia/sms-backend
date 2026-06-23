from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from app import models, crud, database, auth
from app.websocket import manager

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")

# Dependency: DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency: Current user from JWT
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    print("=" * 60)
    print("TOKEN RECEIVED:", token)

    payload = auth.decode_access_token(token)
    print("PAYLOAD:", payload)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    username = payload.get("sub")
    print("USERNAME:", username)

    user = db.query(models.UserModel).filter(
        models.UserModel.username == username
    ).first()

    print("USER FOUND:", user)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

# Forward SMS (any authenticated user)
@router.post("/sms/forward")
async def forward_sms(
    sms: models.Sms,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        saved = crud.save_sms(db, sms)

        await manager.broadcast({
            "id": saved.id,
            "sender": sms.sender,
            "message": sms.message,
            "device_id": sms.device_id,
            "forwarded_by": current_user.username,
            "role": current_user.role
        })

        return {
            "status": "SMS forwarded",
            "id": saved.id,
            "sender": current_user.username,
            "role": current_user.role
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving SMS: {str(e)}"
        )

# List SMS (any authenticated user)
@router.get("/sms/list")
async def list_sms(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        return crud.get_all_sms(db)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching SMS: {str(e)}"
        )