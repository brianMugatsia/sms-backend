from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from app import models, crud, database, auth
from app.websocket import manager
import logging
import pytz

router = APIRouter()
logger = logging.getLogger("sms_backend")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")

# Nairobi timezone
nairobi_tz = pytz.timezone("Africa/Nairobi")

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
    try:
        print("TOKEN RECEIVED:", token)

        payload = auth.decode_access_token(token)

        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")

        username = payload.get("sub")

        user = db.query(models.UserModel).filter(
            models.UserModel.username == username
        ).first()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except Exception as e:
        print("AUTH ERROR:", str(e))
        raise HTTPException(status_code=401, detail="Auth failed")

# Forward SMS (any authenticated user)
@router.post("/sms/forward")
async def forward_sms(
    sms: models.Sms,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        saved = crud.save_sms(db, sms)

        # Refresh to load DB defaults like timestamp
        db.refresh(saved)

        # Convert UTC timestamp to Nairobi time
        timestamp_nairobi = (
            saved.timestamp.astimezone(nairobi_tz).isoformat()
            if saved.timestamp else None
        )

        # Broadcast to all connected clients
        await manager.broadcast({
            "id": saved.id,
            "sender": saved.sender,
            "message": saved.message,
            "device_id": saved.device_id,
            "forwarded_by": current_user.username,
            "role": current_user.role,
            "timestamp": timestamp_nairobi
        })

        logger.info(f"Broadcasted SMS {saved.id} from {saved.sender}")

        return {
            "status": "SMS forwarded",
            "id": saved.id,
            "sender": current_user.username,
            "role": current_user.role,
            "timestamp": timestamp_nairobi
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
        sms_list = crud.get_all_sms(db)

        # Convert each timestamp to Nairobi time
        for sms in sms_list:
            if sms.timestamp:
                sms.timestamp = sms.timestamp.astimezone(nairobi_tz)

        return sms_list
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching SMS: {str(e)}"
        )
