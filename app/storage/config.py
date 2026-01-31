from enum import Enum
from functools import lru_cache

from app.config.settings import settings
from app.storage.base import StorageBackend
from app.storage.local_storage import LocalStorage
from app.storage.gcs_storage import GcsStorage


class StorageType(Enum):
    LOCAL = "local"
    GCS = "gcs"


@lru_cache(maxsize=1)
def get_storage() -> StorageBackend:
    """
    Factory function to get the appropriate storage backend based on environment.

    Uses STORAGE_BACKEND environment variable:
    - "local": Uses LocalStorage with LOCAL_UPLOADS_PATH
    - "gcs": Uses GcsStorage with GCS_BUCKET

    Returns:
        StorageBackend instance configured for the current environment.
    """
    if settings.STORAGE_BACKEND == StorageType.GCS.value:
        return GcsStorage(bucket=settings.GCS_BUCKET)
    return LocalStorage(base_path=settings.LOCAL_UPLOADS_PATH)


def get_local_storage(base_path: str = None) -> LocalStorage:
    """
    Get a LocalStorage instance with optional custom base path.

    Args:
        base_path: Custom base path for uploads. Defaults to LOCAL_UPLOADS_PATH.

    Returns:
        LocalStorage instance.
    """
    return LocalStorage(base_path=base_path or settings.LOCAL_UPLOADS_PATH)


def get_gcs_storage(bucket: str = None) -> GcsStorage:
    """
    Get a GcsStorage instance with optional custom bucket.

    Args:
        bucket: Custom GCS bucket name. Defaults to GCS_BUCKET.

    Returns:
        GcsStorage instance.
    """
    return GcsStorage(bucket=bucket or settings.GCS_BUCKET)
