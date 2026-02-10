"""
Reconciliation Controller.

Provides endpoints for running reconciliation between external (bank)
and internal (workpay) transaction files.
"""
import logging

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.database.mysql_configs import get_database
from app.reconciler.Reconciler import Reconciler, get_available_gateways
from app.exceptions.exceptions import ReconciliationException, DbOperationException
from app.config.gateways import (
    get_external_gateways,
    get_gateways_info,
    is_valid_external_gateway,
)
from app.auth.dependencies import require_active_user
from app.sqlModels.authEntities import User

logger = logging.getLogger("app.controller.reconcile")

router = APIRouter(prefix='/api/v1', tags=['Reconciliation Endpoints'])


@router.get("/")
async def root():
    """Root endpoint for reconciliation API."""
    return JSONResponse(content={"message": "Reconciliation API"}, status_code=200)


@router.get("/gateways")
async def list_gateways(
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    List supported gateways for reconciliation and file uploads.

    Returns:
        - external_gateways: Gateway names for bank statements
        - internal_gateways: Base internal gateway names
        - upload_gateways: All valid gateway names for file uploads
        - charge_keywords: Keywords used to identify charges per gateway
    """
    return JSONResponse(content=get_gateways_info(db), status_code=200)


@router.get("/reconcile/available-gateways")
async def get_ready_gateways(
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get gateways that have files uploaded and are ready for reconciliation.

    Returns gateways with their file status — whether external and internal
    files are present for each gateway.
    """
    try:
        available = get_available_gateways(db_session=db)

        return JSONResponse(
            content={
                "available_gateways": available,
            },
            status_code=200
        )

    except Exception as e:
        logger.error(
            f"Error getting available gateways",
            exc_info=True,
            extra={"error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error checking available gateways: {str(e)}"
        )


@router.post("/reconcile/preview")
async def reconcile_preview(
    gateway: str = Query(..., description="Gateway name to reconcile (e.g., equity, kcb, mpesa)"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Run reconciliation preview (dry run) without saving to database.

    This allows users to review reconciliation insights before committing.
    Results are NOT persisted — call POST /reconcile to save.

    Charge keywords are loaded automatically from the gateway_file_configs table.

    Returns insights including:
    - Total transactions in external file
    - Total transactions in internal file
    - Match rate
    - Unreconciled items count per file
    - Carry-forward stats (previously unreconciled items included)
    """
    try:
        gateway_lower = gateway.lower().strip()

        if not is_valid_external_gateway(gateway_lower, db):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported gateway '{gateway}'. Supported gateways: {get_external_gateways(db)}"
            )

        reconciler = Reconciler(
            gateway=gateway_lower,
            db_session=db,
            user_id=current_user.id,
        )

        result = reconciler.preview()

        logger.info(
            f"Reconciliation preview completed",
            extra={
                "gateway": gateway_lower,
                "user": current_user.username,
                "matched": result.get("insights", {}).get("matched", 0),
                "match_rate": result.get("insights", {}).get("match_rate", 0),
            }
        )

        return JSONResponse(content=result, status_code=200)

    except HTTPException:
        raise
    except ReconciliationException as e:
        logger.warning(
            f"Reconciliation preview validation failed: {str(e)}",
            extra={"gateway": gateway}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error during reconciliation preview",
            exc_info=True,
            extra={"gateway": gateway, "error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error previewing reconciliation for {gateway}: {str(e)}"
        )


@router.post("/reconcile")
async def reconcile(
    gateway: str = Query(..., description="Gateway name to reconcile (e.g., equity, kcb, mpesa)"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Run reconciliation for a gateway.

    This endpoint validates files, performs reconciliation, and saves results to the database.
    A reconciliation run is auto-created with a unique run_id.

    Charge keywords are loaded automatically from the gateway_file_configs table.

    Reconciliation Process:
    1. Validates gateway directory exists with required files
    2. Loads carry-forward data (previously unreconciled transactions, re-evaluates charges)
    3. Loads and preprocesses files (fills nulls, normalizes amounts to positive)
    4. Validates no duplicate reconciliation keys
    5. Generates reconciliation keys: {reference}|{amount}|{gateway}
    6. Matches external debits against internal records (including carry-forward)
    7. Saves new transactions (skips duplicates)
    8. Updates carry-forward matches
    9. Creates reconciliation run record

    Returns:
        Reconciliation result with summary, saved counts, and run_id.
    """
    try:
        gateway_lower = gateway.lower().strip()

        if not is_valid_external_gateway(gateway_lower, db):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported gateway '{gateway}'. Supported gateways: {get_external_gateways(db)}"
            )

        reconciler = Reconciler(
            gateway=gateway_lower,
            db_session=db,
            user_id=current_user.id,
        )

        result = reconciler.run()

        logger.info(
            f"Reconciliation completed successfully",
            extra={
                "run_id": result.get("run_id"),
                "gateway": gateway_lower,
                "user": current_user.username,
                "matched": result.get("summary", {}).get("matched", 0),
            }
        )

        return JSONResponse(content=result, status_code=201)

    except HTTPException:
        raise
    except ReconciliationException as e:
        logger.warning(
            f"Reconciliation validation failed: {str(e)}",
            extra={"gateway": gateway}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except DbOperationException as e:
        logger.error(
            f"Database error during reconciliation",
            exc_info=True,
            extra={"gateway": gateway, "error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error during reconciliation",
            exc_info=True,
            extra={"gateway": gateway, "error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error reconciling {gateway} gateway: {str(e)}"
        )
