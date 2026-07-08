from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter()


# ==========================================================
# GET SETTINGS
# ==========================================================

@router.get(
    "/settings",
    response_model=schemas.EndpointSettings,
)
def get_settings(
    db: Session = Depends(get_db),
):

    settings = crud.get_settings(db)

    return schemas.EndpointSettings(
        storage_endpoint=settings.storage_endpoint,
        storage_api_key=settings.storage_api_key,
    )


# ==========================================================
# UPDATE SETTINGS
# ==========================================================

@router.put(
    "/settings",
    response_model=schemas.EndpointSettings,
)
def update_settings(
    settings: schemas.EndpointSettings,
    db: Session = Depends(get_db),
):

    updated = crud.update_settings(
        db=db,
        settings=settings,
    )

    return schemas.EndpointSettings(
        storage_endpoint=updated.storage_endpoint,
        storage_api_key=updated.storage_api_key,
    )