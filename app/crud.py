# from sqlalchemy.orm import Session
# from app.models import UserModel
# from app import models
# from datetime import datetime
# import pytz
# import uuid
# from app.auth import get_password_hash, verify_password

# # Define Nairobi timezone
# nairobi_tz = pytz.timezone("Africa/Nairobi")

# def save_sms(db: Session, sms: models.Sms):
#     sms_entry = models.SmsModel(
#         id=str(uuid.uuid4()),
#         sender=sms.sender,
#         message=sms.message,
#         device_id=sms.device_id,
#         timestamp=datetime.utcnow()  # store UTC in DB
#     )
#     db.add(sms_entry)
#     db.commit()
#     db.refresh(sms_entry)
#     if sms_entry.timestamp:
#         sms_entry.timestamp = sms_entry.timestamp.replace(tzinfo=pytz.utc).astimezone(nairobi_tz)
#     return sms_entry

# def get_all_sms(db: Session):
#     sms_list = db.query(models.SmsModel).all()
#     for sms in sms_list:
#         if sms.timestamp:
#             sms.timestamp = sms.timestamp.replace(tzinfo=pytz.utc).astimezone(nairobi_tz)
#     return sms_list

# def create_user(db: Session, user: models.User):
#     user_entry = models.UserModel(
#         id=str(uuid.uuid4()),
#         username=user.username,
#         email=user.email,
#         hashed_password=get_password_hash(user.password),
#         role=user.role or "user"
#     )
#     db.add(user_entry)
#     db.commit()
#     db.refresh(user_entry)
#     return user_entry

# def authenticate_user(db: Session, username: str, password: str):
#     user = db.query(UserModel).filter(UserModel.username == username).first()
#     if not user or not verify_password(password, user.hashed_password):
#         return None
#     return user

# def get_users(db: Session):
#     return db.query(models.UserModel).all()
