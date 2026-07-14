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


# ==========================================================
# TEST STORAGE ENDPOINT
# ==========================================================

@router.post(
    "/settings/test",
    response_model=schemas.EndpointTestResponse,
)
def test_storage_endpoint(
    request: schemas.EndpointTestRequest,
):
    """
    Tests a storage endpoint without saving it.
    """

    result = crud.test_storage_endpoint(
        endpoint=request.storage_endpoint,
        api_key=request.storage_api_key,
    )

    return schemas.EndpointTestResponse(
        success=result["success"],
        message=result["message"],
        status_code=result["status_code"],
    )