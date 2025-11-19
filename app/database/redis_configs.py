import os
import redis
from dotenv import load_dotenv
from urllib.parse import urlparse
from app.exceptions.exceptions import RedisException

load_dotenv()
# REDIS_URL = os.getenv("REDIS_LOCAL_URL")
# REDIS_URL = os.getenv("REDIS_URL_DOCKER")
CURRENT_SESSION_KEY = 'current_id'


def choose_redis_path():
    try:
        running_in_docker = os.path.exists("/.dockerenv")
        redis_url = (
            os.getenv("REDIS_URL_DOCKER") if running_in_docker
            else os.getenv("REDIS_URL_LOCAL")
        )
        return redis_url
    except Exception:
        raise


def redis_client():
    try:
        redis_path = choose_redis_path()
        parsed = urlparse(redis_path)
        return redis.Redis(
            host=parsed.hostname,
            port=parsed.port or 6379,
            db=int(parsed.path.strip("/")) if parsed.path else 0,
            decode_responses=True
        )
    except Exception:
        raise


def set_current_redis_session_id(session_id: str, data:str = "active") -> str:
    try:
        client = redis_client()
        client.set(session_id, data)
        client.set(CURRENT_SESSION_KEY, session_id)
        return f"{session_id} created successfully"
    except Exception:
        raise


def get_current_redis_session_id() -> dict:
    try:
        client = redis_client()
        current_key = client.get(CURRENT_SESSION_KEY)
        if not current_key:
           return {"message": "no current key set"}
        current_value = client.get(current_key)
        return {"current_session_key": current_key, "value": current_value}
    except Exception:
        raise


def get_all_redis_sessions(pattern: str = "sess:*") -> dict:
    try:
        client = redis_client()
        sessions = {}
        for key in client.scan_iter(match=pattern):
            sessions[key] = client.get(key)
        return sessions
    except Exception:
        raise