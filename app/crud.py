from sqlalchemy.orm import Session
from app.models import UserModel
from app import models
import uuid
from app.auth import get_password_hash, verify_password


def save_sms(db: Session, sms: models.Sms):
    sms_entry = models.SmsModel(
        id=str(uuid.uuid4()),
        sender=sms.sender,
        message=sms.message,
        device_id=sms.device_id
    )
    db.add(sms_entry)
    db.commit()
    db.refresh(sms_entry)
    return sms_entry

def get_all_sms(db: Session):
    return db.query(models.SmsModel).all()

def create_user(db: Session, user: models.User):
    user_entry = models.UserModel(
        id=str(uuid.uuid4()),
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        role=user.role
    )
    db.add(user_entry)
    db.commit()
    db.refresh(user_entry)
    return user_entry
def authenticate_user(db: Session, username: str, password: str):
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def get_users(db: Session):
    return db.query(models.UserModel).all()
