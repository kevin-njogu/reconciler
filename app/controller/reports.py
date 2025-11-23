from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database.mysql_configs import get_database
from app.database.redis_configs import get_current_redis_session_id
from app.reports.download_report import download_gateway_report

router = APIRouter(prefix='/api/v1', tags=['Report Endpoints'])

db_session = Depends(get_database)


@router.post("/download/{gateway}")
async def download_report(
    gateway: str,
    db: Session = db_session,
    session_id: Optional[str] = Query(default=None)
):
    """
    Download a report for a specific payment gateway.

    Args:
        gateway (str): Name of the gateway (e.g., "equity", "kcb", "mpesa").
        db (Session, optional): Database session. Defaults to injected db_session.
        session_id (str, optional): Specific session ID. If not provided, uses the current session in Redis.

    Returns:
        StreamingResponse: The generated report file as a streaming response.

    Raises:
        HTTPException: If report generation fails or gateway/session is invalid.
    """
    try:
        # Determine session to use
        session = session_id or get_current_redis_session_id().get("current_session_key")
        if not session:
            raise HTTPException(status_code=400, detail="No session ID provided and no current session found.")

        # Generate and return the report
        response = download_gateway_report(db, gateway, session)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading report for '{gateway}': {e}")
