import os
import redis
from dotenv import load_dotenv
from urllib.parse import urlparse
from app.exceptions.exceptions import RedisException

load_dotenv()
# REDIS_URL = os.getenv("REDIS_LOCAL_URL")
REDIS_URL = os.getenv("REDIS_URL_DOCKER")
CURRENT_SESSION_KEY = 'current_id'


def redis_client(redis_url:str):
    try:
        parsed = urlparse(redis_url)
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
        client = redis_client(REDIS_URL)
        client.set(session_id, data)
        client.set(CURRENT_SESSION_KEY, session_id)
        return f"{session_id} created successfully"
    except Exception:
        raise


def get_current_redis_session_id() -> dict:
    try:
        client = redis_client(REDIS_URL)
        current_key = client.get(CURRENT_SESSION_KEY)
        if not current_key:
           raise RedisException("No current key currently set")
        current_value = client.get(current_key)
        return {"current_session_key": current_key, "value": current_value}
    except Exception:
        raise


def get_all_redis_sessions(pattern: str = "sess:*") -> dict:
    try:
        client = redis_client(REDIS_URL)
        sessions = {}
        for key in client.scan_iter(match=pattern):
            sessions[key] = client.get(key)
        return sessions
    except Exception:
        raise