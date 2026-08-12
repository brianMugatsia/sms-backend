from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter()


@router.get("/settings", response_model=schemas.EndpointSettings)
def get_settings(
    device_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    settings = crud.get_settings(db, device_id)
    return schemas.EndpointSettings(
        device_id=settings.device_id,
        storage_endpoint=settings.storage_endpoint,
        storage_api_key=settings.storage_api_key,
    )


@router.put("/settings", response_model=schemas.EndpointSettings)
def update_settings(
    settings: schemas.EndpointSettings,
    db: Session = Depends(get_db),
):
    if not settings.device_id or settings.device_id.strip() == "":
        raise HTTPException(status_code=400, detail="device_id is required")

    updated = crud.update_settings(
        db=db,
        device_id=settings.device_id,
        settings=settings,
    )

    return schemas.EndpointSettings(
        device_id=updated.device_id,
        storage_endpoint=updated.storage_endpoint,
        storage_api_key=updated.storage_api_key,
    )


@router.post("/settings/test", response_model=schemas.EndpointTestResponse)
async def test_storage_endpoint(
    request: schemas.EndpointTestRequest,
):
    """
    Stateless endpoint testing using httpx.
    """
    result = await crud.test_storage_endpoint_async(
        endpoint=request.storage_endpoint,
        api_key=request.storage_api_key,
    )

    return schemas.EndpointTestResponse(
        success=result["success"],
        message=result["message"],
        status_code=result.get("status_code"),
    )