from fastapi import APIRouter, status, HTTPException
from fastapi.params import Depends
from starlette.responses import JSONResponse
from app.reconciliation.upload_service import UploadService
from app.reports.get_reports import Reports
from app.utils.get_current_session import get_current_session

router = APIRouter(
    prefix="/api",
)

@router.post("/reconcile/{gateway}", status_code=status.HTTP_201_CREATED)
async def reconcile(gateway: str):
    try:
        if not gateway:
            raise HTTPException(status_code=400, detail="Gateway is required")
        upload = UploadService()
        upload.upload_func(gateway)
        return JSONResponse(content="Reconciliation completed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/download/{gateway}")
async def download(gateway:str, session_id: str = Depends(get_current_session)):
    try:
        if not gateway:
            raise HTTPException(status_code=400, detail="Gateway is required")
        report = Reports()
        return report.download_report(session_id, gateway)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



