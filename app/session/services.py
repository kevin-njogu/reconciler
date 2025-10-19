from fastapi import APIRouter, HTTPException
from app.session.entities import Session
from app.database.redis import set_current_redis_session_id
from app.fileupload.services import create_uploads_directory


def create_session(db_session=None):
    try:
        new_session = Session()
        db_session.add(new_session)
        db_session.commit()
        db_session.refresh(new_session)
        set_current_redis_session_id(new_session.id)
        create_uploads_directory(new_session.id, "uploads")
        return new_session
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Failed to create a new session: {str(e)}')
