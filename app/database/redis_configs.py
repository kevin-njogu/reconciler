import os
import redis
from dotenv import load_dotenv
from urllib.parse import urlparse
from app.exceptions.exceptions import NullValueException

load_dotenv()
REDIS_URL = os.getenv("REDIS_LOCAL")
CURRENT_SESSION_KEY = 'current_id'


def redis_client(redis_url:str):
    parsed = urlparse(redis_url)
    if not parsed:
        raise NullValueException("Redis client is null")
    return redis.Redis(
        host=parsed.hostname,
        port=parsed.port or 6379,
        db=int(parsed.path.strip("/")) if parsed.path else 0,
        decode_responses=True
    )


def set_current_redis_session_id(session_id: str) -> None:
    client = redis_client(REDIS_URL)
    if client is None:
        raise NullValueException("Cannot set redis session to none")
    client.set(CURRENT_SESSION_KEY, session_id)
    return None


def get_current_redis_session_id() -> str:
    client = redis_client(REDIS_URL)
    current_session = client.get(CURRENT_SESSION_KEY)
    if not current_session:
        raise NullValueException("Redis session id is null")
    return current_session
