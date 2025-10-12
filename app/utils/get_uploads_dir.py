from pathlib import Path

from app.utils.get_current_session import get_current_session
# sess = get_current_session()

def get_uploads_dir(session_id):
    BASE_DIR = Path(__file__).resolve().parent.parent
    UPLOADS_DIR = BASE_DIR / "uploads" / session_id

    print(UPLOADS_DIR)

    return UPLOADS_DIR

# get_uploads_dir(sess)