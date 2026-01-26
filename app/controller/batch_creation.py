"""
Batch Management Controller.

Handles batch creation, listing, closing, delete requests, and file management.
Batches cannot be edited — only created, closed, or deleted (via maker-checker).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from starlette.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel

from app.database.mysql_configs import get_database
from app.upload.batch_creation import BatchService
from app.sqlModels.batchEntities import Batch, BatchFile, BatchStatus, BatchDeleteRequest
from app.sqlModels.transactionEntities import Transaction
from app.sqlModels.authEntities import User, AuditLog
from app.exceptions.exceptions import FileUploadException
from app.auth.dependencies import require_active_user, require_admin, require_user_role, require_admin_only
from app.customLogging.logger import get_logger, log_exception

logger = get_logger(__name__)

router = APIRouter(prefix='/api/v1/batch', tags=['Batch Management Endpoints'])


class BatchCreateRequest(BaseModel):
    description: Optional[str] = None


class DeleteRequestBody(BaseModel):
    reason: Optional[str] = None


class ReviewDeleteRequestBody(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None


# ============================================================================
# Batch CRUD Endpoints
# ============================================================================

@router.post("", status_code=201)
async def create_batch(
    request_body: Optional[BatchCreateRequest] = None,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user),
):
    """
    Create a new batch for file uploads.

    A user cannot create a new batch if they already have a pending batch.
    Creates a storage directory named after the batch_id.
    """
    try:
        batch_service = BatchService(db)
        batch = batch_service.create_batch(
            created_by_id=current_user.id,
            description=request_body.description if request_body else None,
        )
        return JSONResponse(
            content={
                "batch_id": batch.batch_id,
                "batch_db_id": batch.id,
                "status": batch.status,
                "description": batch.description,
                "created_by": current_user.username,
                "created_at": batch.created_at.isoformat(),
                "message": "Batch created successfully",
            },
            status_code=201,
        )
    except FileUploadException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_exception(logger, "Failed to create batch", e, user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to create batch. Please try again.")


@router.get("/{batch_id}")
async def get_batch(
    batch_id: str,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user),
):
    """
    Get batch details by batch ID.

    Both admin and user roles can view batch details.
    """
    try:
        batch_service = BatchService(db)
        batch = batch_service.get_batch_by_id(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail=f"Batch not found: {batch_id}")

        file_count = db.query(func.count(BatchFile.id)).filter(
            BatchFile.batch_id == batch_id,
        ).scalar()

        transaction_count = db.query(func.count(Transaction.id)).filter(
            Transaction.batch_id == batch_id,
        ).scalar()

        unreconciled_count = db.query(func.count(Transaction.id)).filter(
            Transaction.batch_id == batch_id,
            Transaction.reconciliation_status == "unreconciled",
        ).scalar()

        return JSONResponse(
            content={
                "batch_id": batch.batch_id,
                "batch_db_id": batch.id,
                "status": batch.status,
                "description": batch.description,
                "created_at": batch.created_at.isoformat(),
                "closed_at": batch.closed_at.isoformat() if batch.closed_at else None,
                "created_by": batch.created_by.username if batch.created_by else None,
                "created_by_id": batch.created_by_id,
                "file_count": file_count,
                "transaction_count": transaction_count,
                "unreconciled_count": unreconciled_count,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        log_exception(logger, "Failed to retrieve batch", e, batch_id=batch_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve batch details.")


@router.get("")
async def get_all_batches(
    status: Optional[str] = None,
    search: Optional[str] = Query(None, description="Search batch IDs"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user),
):
    """
    Get all batches with pagination, optionally filtered by status.

    Both admin and user roles can view batches.
    """
    try:
        query = db.query(Batch)

        if status:
            try:
                batch_status = BatchStatus(status.lower())
                query = query.filter(Batch.status == batch_status.value)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Valid values: pending, completed",
                )

        if search:
            query = query.filter(Batch.batch_id.ilike(f"%{search}%"))

        total_count = query.count()

        offset = (page - 1) * page_size
        batches = query.order_by(Batch.created_at.desc()).offset(offset).limit(page_size).all()

        total_pages = (total_count + page_size - 1) // page_size

        return JSONResponse(
            content={
                "batches": [
                    {
                        "batch_id": b.batch_id,
                        "batch_db_id": b.id,
                        "status": b.status,
                        "description": b.description,
                        "created_at": b.created_at.isoformat(),
                        "closed_at": b.closed_at.isoformat() if b.closed_at else None,
                        "created_by": b.created_by.username if b.created_by else None,
                        "created_by_id": b.created_by_id,
                        "file_count": len(b.files) if b.files else 0,
                    }
                    for b in batches
                ],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1,
                },
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        log_exception(logger, "Failed to retrieve batches", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve batches.")


# ============================================================================
# Close Batch Endpoint
# ============================================================================

@router.post("/{batch_id}/close")
async def close_batch(
    batch_id: str,
    request: Request,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user),
):
    """
    Close a batch (mark as completed).

    Only the user who created the batch can close it.
    Cannot close if there are unreconciled transactions.
    """
    try:
        batch_service = BatchService(db)
        batch = batch_service.close_batch(batch_id, current_user.id)

        # Audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="close_batch",
            resource_type="batch",
            resource_id=batch_id,
            details={"batch_id": batch_id, "status": batch.status},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_path=request.url.path,
            request_method="POST",
        )
        db.add(audit_log)
        db.commit()

        return JSONResponse(
            content={
                "batch_id": batch.batch_id,
                "status": batch.status,
                "closed_at": batch.closed_at.isoformat() if batch.closed_at else None,
                "message": "Batch closed successfully",
            }
        )
    except FileUploadException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_exception(logger, "Failed to close batch", e, batch_id=batch_id)
        raise HTTPException(status_code=500, detail="Failed to close batch. Please try again.")


# ============================================================================
# Delete Request Endpoints (Maker-Checker)
# ============================================================================

@router.post("/{batch_id}/delete-request", status_code=201)
async def create_delete_request(
    batch_id: str,
    request_body: Optional[DeleteRequestBody] = None,
    request: Request = None,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role),
):
    """
    Initiate a delete request for a batch (maker operation).

    Only users with 'user' role can initiate delete requests. The request
    must be approved by an admin (checker) before the batch is deleted.
    """
    try:
        batch_service = BatchService(db)
        delete_request = batch_service.create_delete_request(
            batch_id=batch_id,
            requested_by_id=current_user.id,
            reason=request_body.reason if request_body else None,
        )

        return JSONResponse(
            content={
                "id": delete_request.id,
                "batch_id": delete_request.batch_id,
                "status": delete_request.status,
                "reason": delete_request.reason,
                "requested_by": current_user.username,
                "created_at": delete_request.created_at.isoformat(),
                "message": "Delete request submitted. Awaiting admin approval.",
            },
            status_code=201,
        )
    except FileUploadException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_exception(logger, "Failed to create delete request", e, batch_id=batch_id)
        raise HTTPException(status_code=500, detail="Failed to submit delete request.")


@router.get("/delete-requests/list")
async def get_delete_requests(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user),
):
    """
    List batch delete requests.

    Both admin and users can view delete requests.
    """
    try:
        batch_service = BatchService(db)
        requests = batch_service.get_delete_requests(status=status)

        return JSONResponse(
            content={
                "count": len(requests),
                "requests": [
                    {
                        "id": r.id,
                        "batch_id": r.batch_id,
                        "status": r.status,
                        "reason": r.reason,
                        "requested_by": r.requested_by.username if r.requested_by else None,
                        "requested_by_id": r.requested_by_id,
                        "reviewed_by": r.reviewed_by.username if r.reviewed_by else None,
                        "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
                        "rejection_reason": r.rejection_reason,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in requests
                ],
            }
        )
    except Exception as e:
        log_exception(logger, "Failed to retrieve delete requests", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve delete requests.")


@router.post("/delete-requests/{request_id}/review")
async def review_delete_request(
    request_id: int,
    request_body: ReviewDeleteRequestBody,
    request: Request = None,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin_only),
):
    """
    Review (approve or reject) a batch delete request (checker operation).

    Only admins (not super_admins) can review delete requests.
    Approval triggers cascade deletion.
    """
    try:
        batch_service = BatchService(db)
        result = batch_service.review_delete_request(
            request_id=request_id,
            reviewer_id=current_user.id,
            approved=request_body.approved,
            rejection_reason=request_body.rejection_reason,
        )

        # Audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="review_batch_delete_request",
            resource_type="batch_delete_request",
            resource_id=str(request_id),
            details={
                "request_id": request_id,
                "action": result.get("action"),
                "batch_id": result.get("batch_id"),
                "transactions_deleted": result.get("transactions_deleted", 0),
                "files_deleted": result.get("files_deleted", 0),
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_path=request.url.path if request else None,
            request_method="POST",
        )
        db.add(audit_log)
        db.commit()

        return JSONResponse(content=result)
    except FileUploadException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_exception(logger, "Failed to review delete request", e, request_id=request_id)
        raise HTTPException(status_code=500, detail="Failed to review delete request.")


# ============================================================================
# File Management Endpoints
# ============================================================================

@router.get("/{batch_id}/files")
async def get_batch_files(
    batch_id: str,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user),
):
    """
    Get all files in a batch.
    """
    try:
        batch = db.query(Batch).filter(Batch.batch_id == batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail=f"Batch not found: {batch_id}")

        files = db.query(BatchFile).filter(BatchFile.batch_id == batch_id).order_by(
            BatchFile.uploaded_at.desc()
        ).all()

        return JSONResponse(
            content={
                "batch_id": batch_id,
                "batch_status": batch.status,
                "file_count": len(files),
                "files": [
                    {
                        "id": f.id,
                        "filename": f.filename,
                        "original_filename": f.original_filename,
                        "gateway": f.gateway,
                        "file_size": f.file_size,
                        "content_type": f.content_type,
                        "uploaded_at": f.uploaded_at.isoformat(),
                        "uploaded_by": f.uploaded_by.username if f.uploaded_by else None,
                    }
                    for f in files
                ],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        log_exception(logger, "Failed to retrieve batch files", e, batch_id=batch_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve batch files.")
