"""
Reconciliation Controller.

Provides endpoints for running reconciliation between external (bank)
and internal (workpay) transaction files.
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.database.mysql_configs import get_database
from app.reconciler.Reconciler import Reconciler, get_available_gateways
from app.exceptions.exceptions import ReconciliationException, DbOperationException
from app.config.gateways import (
    get_external_gateways,
    get_charge_keywords,
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


@router.get("/reconcile/available-gateways/{batch_id}")
async def get_batch_available_gateways(
    batch_id: str = Path(..., description="Batch ID to check for available gateways"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get gateways that have files uploaded for a specific batch.

    This endpoint checks which gateways have files uploaded and returns
    their status for reconciliation readiness.

    Args:
        batch_id: The batch identifier to check.

    Returns:
        Dictionary with batch_id and list of available gateways with their file status.
        Each gateway includes:
        - gateway: Base gateway name (e.g., "equity")
        - display_name: User-friendly gateway name
        - has_external: Whether external file exists
        - has_internal: Whether internal file exists
        - external_file: External filename if present
        - internal_file: Internal filename if present
        - ready_for_reconciliation: Whether both files are present
    """
    try:
        available = get_available_gateways(batch_id, db_session=db)

        return JSONResponse(
            content={
                "batch_id": batch_id,
                "available_gateways": available,
            },
            status_code=200
        )

    except Exception as e:
        logger.error(
            f"Error getting available gateways for batch {batch_id}",
            exc_info=True,
            extra={"batch_id": batch_id, "error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error checking available gateways: {str(e)}"
        )


@router.post("/reconcile/preview")
async def reconcile_preview(
    batch_id: str = Query(..., description="Batch ID containing the files to reconcile"),
    gateway: str = Query(..., description="Gateway name to reconcile (e.g., equity, kcb, mpesa)"),
    charge_keywords: Optional[List[str]] = Query(default=None, description="Keywords to identify charge transactions"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Run reconciliation preview (dry run) without saving to database.

    This allows users to review reconciliation insights before committing.
    Results are NOT persisted - call POST /reconcile to save.

    Returns insights including:
    - Total transactions in external file
    - Total transactions in internal file
    - Match rate
    - Unreconciled items count per file

    Args:
        batch_id: The batch containing uploaded files.
        gateway: Gateway name (equity, kcb, mpesa).
        charge_keywords: Optional keywords to identify charge transactions.

    Returns:
        Reconciliation preview with insights (not saved).
    """
    try:
        gateway_lower = gateway.lower().strip()

        # Validate gateway exists in configuration
        if not is_valid_external_gateway(gateway_lower, db):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported gateway '{gateway}'. Supported gateways: {get_external_gateways(db)}"
            )

        # Get charge keywords from config if not provided
        keywords = charge_keywords or get_charge_keywords(gateway_lower, db)

        # Create reconciler and run preview (dry run)
        reconciler = Reconciler(
            batch_id=batch_id,
            gateway=gateway_lower,
            db_session=db,
            charge_keywords=keywords,
        )

        # Run preview without saving
        result = reconciler.preview()

        logger.info(
            f"Reconciliation preview completed",
            extra={
                "batch_id": batch_id,
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
            extra={"batch_id": batch_id, "gateway": gateway}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error during reconciliation preview",
            exc_info=True,
            extra={"batch_id": batch_id, "gateway": gateway, "error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error previewing reconciliation for {gateway}: {str(e)}"
        )


@router.post("/reconcile")
async def reconcile(
    batch_id: str = Query(..., description="Batch ID containing the files to reconcile"),
    gateway: str = Query(..., description="Gateway name to reconcile (e.g., equity, kcb, mpesa)"),
    charge_keywords: Optional[List[str]] = Query(default=None, description="Keywords to identify charge transactions"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Run reconciliation for a batch and gateway.

    This endpoint validates files, performs reconciliation, and saves results to the database.
    It's a single-step operation that replaces the old preview/save workflow.

    Reconciliation Process:
    1. Validates batch exists and is in pending status
    2. Validates gateway directory exists with required files
    3. Checks for existing reconciliation (prevents duplicates)
    4. Loads and preprocesses files (fills nulls, normalizes data)
    5. Generates reconciliation keys: {reference}|{amount}|{gateway}
    6. Matches external debits against internal records
    7. Saves all transactions to database with reconciliation status

    Args:
        batch_id: The batch containing uploaded files.
        gateway: Gateway name (equity, kcb, mpesa).
        charge_keywords: Optional keywords to identify charge transactions.

    Returns:
        Reconciliation result with summary and saved counts.

    Raises:
        HTTPException 400: If validation fails (batch, gateway, files).
        HTTPException 409: If reconciliation already exists.
        HTTPException 500: If processing error occurs.
    """
    try:
        gateway_lower = gateway.lower().strip()

        # Validate gateway exists in configuration
        if not is_valid_external_gateway(gateway_lower, db):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported gateway '{gateway}'. Supported gateways: {get_external_gateways(db)}"
            )

        # Get charge keywords from config if not provided
        keywords = charge_keywords or get_charge_keywords(gateway_lower, db)

        # Create reconciler and run full process
        reconciler = Reconciler(
            batch_id=batch_id,
            gateway=gateway_lower,
            db_session=db,
            charge_keywords=keywords,
        )

        # Run validates, reconciles, and saves
        result = reconciler.run()

        logger.info(
            f"Reconciliation completed successfully",
            extra={
                "batch_id": batch_id,
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
            extra={"batch_id": batch_id, "gateway": gateway}
        )
        # Check if it's a "already exists" error
        if "already exists" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except DbOperationException as e:
        logger.error(
            f"Database error during reconciliation",
            exc_info=True,
            extra={"batch_id": batch_id, "gateway": gateway, "error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error during reconciliation",
            exc_info=True,
            extra={"batch_id": batch_id, "gateway": gateway, "error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error reconciling {gateway} gateway: {str(e)}"
        )


# Backwards compatibility endpoint - deprecated
@router.post("/reconcile/save")
async def reconcile_and_save(
    batch_id: str = Query(..., description="Batch ID containing the files to reconcile"),
    external_gateway: str = Query(..., description="External gateway name (equity, kcb, mpesa)"),
    internal_gateway: Optional[str] = Query(default=None, description="Internal gateway name (deprecated, ignored)"),
    charge_keywords: Optional[List[str]] = Query(default=None, description="Keywords to identify charge transactions"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Reconcile transactions and save results to database.

    DEPRECATED: Use POST /reconcile instead. This endpoint is maintained
    for backwards compatibility.

    Args:
        batch_id: The batch containing uploaded files.
        external_gateway: External gateway name (equity, kcb, mpesa).
        internal_gateway: Deprecated - ignored.
        charge_keywords: Optional keywords to identify charge transactions.

    Returns:
        Dictionary with save counts and summary.
    """
    # Forward to new endpoint
    return await reconcile(
        batch_id=batch_id,
        gateway=external_gateway,
        charge_keywords=charge_keywords,
        db=db,
        current_user=current_user
    )
