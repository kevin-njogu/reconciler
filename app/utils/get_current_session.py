from fastapi import HTTPException

from app.configs.configs import Configs

r = Configs.REDIS


def get_current_session():

    try:
        curr_session = r.get("current_session_id")

        if not curr_session:
            raise HTTPException(status_code=400, detail="No active session found")

        return curr_session
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
