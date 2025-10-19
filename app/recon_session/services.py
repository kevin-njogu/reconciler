from fastapi import APIRouter, HTTPException
from app.recon_session.entities import ReconciliationSession
from app.database.redis_configs import set_current_redis_session_id
from app.fileupload.services import create_uploads_directory


def create_session(db_session):
    try:
        new_session = ReconciliationSession()
        db_session.add(new_session)
        db_session.commit()
        db_session.refresh(new_session)
        set_current_redis_session_id(new_session.id)
        create_uploads_directory(new_session.id, "uploads")
        return new_session
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Failed to create a new session: {str(e)}')
