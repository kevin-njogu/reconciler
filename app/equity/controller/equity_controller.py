from fastapi import APIRouter, status, HTTPException
from app.equity.service.upload_data import upload_service_impl

router = APIRouter(
    prefix="/api",
    tags=["apis"],
)

@router.post("/reconcile/equity", status_code=status.HTTP_201_CREATED)
async def reconcile_equity():
    try:
        response = upload_service_impl()
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"reconcile_equity endpoint failed: {str(e)}")