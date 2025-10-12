from fastapi import APIRouter, File, UploadFile, HTTPException
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from starlette.responses import JSONResponse
from app.database.database_connection import get_db_session
from app.models.all_models import ReconciliationSession
from app.configs.configs import Configs
from app.utils.get_current_session import get_current_session

r = Configs.REDIS

router = APIRouter(
    prefix="/api/file",
    tags=["file"],
    responses={404: {"description": "Failed to upload file"}}
)

@router.post("/create_session")
async def create_session():
    recon_sess = ReconciliationSession()

    try:
        with get_db_session() as db:
            try:
                db.add(recon_sess)
                db.commit()
                db.refresh(recon_sess)
            except IntegrityError:
                db.rollback()
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=404, detail=str(e))

        r.set("current_session_id", recon_sess.id)
        return {"session_id": recon_sess.id}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))



@router.post("/uploadfile")
async def upload_file(file: UploadFile = File(...)):
    try:
        curr_session = get_current_session()

        if file.filename == "":
            raise HTTPException(status_code=400, detail="No file provided")
        if not file.filename.endswith(("xls", "xlsx", "csv")):
            raise HTTPException(status_code=400, detail="Unsupported file type")

        uploads_dir = Path("uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)

        session_dir =  uploads_dir / curr_session
        session_dir.mkdir(parents=True, exist_ok=True)
        filepath = session_dir / file.filename

        with open(filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # return clean_up_uploads()
        return JSONResponse(content="file upload successful", status_code=200)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"upload file endpoint failed: {str(e)}")



