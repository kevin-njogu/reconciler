"""
Batch Management Service.

Handles batch lifecycle: creation (with storage directory), closing (with
unreconciled transaction check), delete requests (maker-checker workflow),
and cascade deletion.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.customLogging.logger import get_logger, log_operation, log_exception
from app.exceptions.exceptions import FileUploadException
from app.sqlModels.batchEntities import (
    Batch, BatchFile, BatchStatus,
    BatchDeleteRequest, DeleteRequestStatus,
)
from app.sqlModels.transactionEntities import Transaction
from app.storage.config import get_storage

logger = get_logger(__name__)


class BatchService:
    """Service class for batch management operations."""

    def __init__(self, db: Session):
        self.db = db

    def _generate_batch_id_string(self) -> str:
        """Generate a unique batch ID with timestamp and UUID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        short_uuid = uuid.uuid4().hex[:8]
        return f"{timestamp}_{short_uuid}"

    def user_has_pending_batch(self, user_id: int) -> Optional[Batch]:
        """
        Check if a user already has a pending batch.

        Args:
            user_id: The user's database ID.

        Returns:
            The pending Batch if one exists, None otherwise.
        """
        return self.db.query(Batch).filter(
            Batch.created_by_id == user_id,
            Batch.status == BatchStatus.PENDING.value,
        ).first()

    def create_batch(
        self,
        created_by_id: int,
        description: Optional[str] = None,
    ) -> Batch:
        """
        Create a new batch with storage directory.

        Validates that the user does not already have an open (pending) batch.
        Creates the batch record in the database and provisions a storage
        directory named after the batch_id.

        Args:
            created_by_id: User ID of the creator.
            description: Optional description for the batch.

        Returns:
            The created Batch object.

        Raises:
            FileUploadException: If user already has a pending batch or
                                 directory creation fails.
        """
        # Check if user already has a pending batch
        existing = self.user_has_pending_batch(created_by_id)
        if existing:
            raise FileUploadException(
                f"You already have an open batch: {existing.batch_id}. "
                "Close it before creating a new one."
            )

        batch_id = self._generate_batch_id_string()

        batch = Batch(
            batch_id=batch_id,
            status=BatchStatus.PENDING.value,
            created_by_id=created_by_id,
            description=description,
        )
        self.db.add(batch)
        self.db.flush()  # Get the ID without committing

        # Create storage directory for the batch
        storage = get_storage()
        try:
            storage.ensure_batch_directory(batch_id)
            logger.info(f"Created storage directory for batch {batch_id}")
        except Exception as e:
            self.db.rollback()
            log_exception(logger, "Failed to create batch storage directory", e, batch_id=batch_id)
            raise FileUploadException(f"Failed to create storage for batch: {str(e)}")

        self.db.commit()
        self.db.refresh(batch)

        log_operation(logger, "create_batch", success=True, batch_id=batch_id, user_id=created_by_id)
        return batch

    def close_batch(self, batch_id: str, user_id: int) -> Batch:
        """
        Close a batch (mark as completed).

        Only the creator of the batch can close it. The batch can only be closed
        if all transactions tagged to it are reconciled.

        Args:
            batch_id: The batch identifier.
            user_id: The ID of the user requesting the close.

        Returns:
            The updated Batch object.

        Raises:
            FileUploadException: If batch not found, user is not the creator,
                                 or unreconciled transactions exist.
        """
        batch = self.get_batch_by_id(batch_id)
        if not batch:
            raise FileUploadException(f"Batch not found: {batch_id}")

        if batch.status == BatchStatus.COMPLETED.value:
            raise FileUploadException(f"Batch {batch_id} is already closed.")

        if batch.created_by_id != user_id:
            raise FileUploadException(
                "Only the batch creator can close this batch."
            )

        # Check for unreconciled transactions
        unreconciled_count = self.db.query(Transaction).filter(
            Transaction.batch_id == batch_id,
            Transaction.reconciliation_status == "unreconciled",
        ).count()

        if unreconciled_count > 0:
            raise FileUploadException(
                f"Cannot close batch: {unreconciled_count} unreconciled "
                f"transaction(s) remain. Reconcile all transactions first."
            )

        batch.status = BatchStatus.COMPLETED.value
        batch.closed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(batch)

        log_operation(logger, "close_batch", success=True, batch_id=batch_id, user_id=user_id)
        return batch

    def create_delete_request(
        self,
        batch_id: str,
        requested_by_id: int,
        reason: Optional[str] = None,
    ) -> BatchDeleteRequest:
        """
        Create a delete request for a batch (maker-checker workflow).

        Users initiate the request; an admin must approve it before
        the batch is actually deleted.

        Args:
            batch_id: The batch identifier to request deletion for.
            requested_by_id: User ID initiating the delete request.
            reason: Optional reason for deletion.

        Returns:
            The created BatchDeleteRequest object.

        Raises:
            FileUploadException: If batch not found or a pending request exists.
        """
        batch = self.get_batch_by_id(batch_id)
        if not batch:
            raise FileUploadException(f"Batch not found: {batch_id}")

        # Check if there's already a pending delete request for this batch
        existing_request = self.db.query(BatchDeleteRequest).filter(
            BatchDeleteRequest.batch_id == batch_id,
            BatchDeleteRequest.status == DeleteRequestStatus.PENDING.value,
        ).first()

        if existing_request:
            raise FileUploadException(
                f"A delete request for batch {batch_id} is already pending approval."
            )

        delete_request = BatchDeleteRequest(
            batch_id=batch_id,
            requested_by_id=requested_by_id,
            reason=reason,
        )
        self.db.add(delete_request)
        self.db.commit()
        self.db.refresh(delete_request)

        log_operation(
            logger, "create_delete_request", success=True,
            batch_id=batch_id, user_id=requested_by_id,
        )
        return delete_request

    def review_delete_request(
        self,
        request_id: int,
        reviewer_id: int,
        approved: bool,
        rejection_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Review (approve or reject) a batch delete request.

        If approved, triggers cascade deletion of the batch.

        Args:
            request_id: The delete request ID.
            reviewer_id: Admin user ID performing the review.
            approved: Whether to approve or reject.
            rejection_reason: Reason for rejection (required if rejected).

        Returns:
            Dictionary with review result and deletion stats if approved.

        Raises:
            FileUploadException: If request not found or already reviewed.
        """
        delete_request = self.db.query(BatchDeleteRequest).filter(
            BatchDeleteRequest.id == request_id,
        ).first()

        if not delete_request:
            raise FileUploadException(f"Delete request not found: {request_id}")

        if delete_request.status != DeleteRequestStatus.PENDING.value:
            raise FileUploadException(
                f"Delete request {request_id} has already been {delete_request.status}."
            )

        now = datetime.now(timezone.utc)

        if approved:
            delete_request.status = DeleteRequestStatus.APPROVED.value
            delete_request.reviewed_by_id = reviewer_id
            delete_request.reviewed_at = now
            self.db.commit()

            # Perform cascade deletion
            stats = self._cascade_delete_batch(delete_request.batch_id)
            stats["request_id"] = request_id
            stats["action"] = "approved"

            log_operation(
                logger, "approve_delete_request", success=True,
                request_id=request_id, batch_id=delete_request.batch_id,
                reviewer_id=reviewer_id,
            )
            return stats
        else:
            delete_request.status = DeleteRequestStatus.REJECTED.value
            delete_request.reviewed_by_id = reviewer_id
            delete_request.reviewed_at = now
            delete_request.rejection_reason = rejection_reason
            self.db.commit()

            log_operation(
                logger, "reject_delete_request", success=True,
                request_id=request_id, batch_id=delete_request.batch_id,
                reviewer_id=reviewer_id,
            )
            return {
                "request_id": request_id,
                "action": "rejected",
                "batch_id": delete_request.batch_id,
                "rejection_reason": rejection_reason,
            }

    def get_delete_requests(
        self,
        status: Optional[str] = None,
    ) -> List[BatchDeleteRequest]:
        """
        Get batch delete requests, optionally filtered by status.

        Args:
            status: Optional filter (pending, approved, rejected).

        Returns:
            List of BatchDeleteRequest objects.
        """
        query = self.db.query(BatchDeleteRequest).order_by(
            BatchDeleteRequest.created_at.desc()
        )
        if status:
            query = query.filter(BatchDeleteRequest.status == status)
        return query.all()

    def _cascade_delete_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Perform cascade deletion of a batch and all related data.

        Deletes: transactions, file records, storage files/directory,
        delete requests, batch record.

        Args:
            batch_id: The batch identifier to delete.

        Returns:
            Dictionary containing deletion statistics.
        """
        stats: Dict[str, Any] = {
            "batch_id": batch_id,
            "transactions_deleted": 0,
            "files_deleted": 0,
            "file_records_deleted": 0,
            "delete_requests_deleted": 0,
        }

        # 1. Delete all transactions for this batch
        transactions_count = self.db.query(Transaction).filter(
            Transaction.batch_id == batch_id,
        ).delete(synchronize_session=False)
        stats["transactions_deleted"] = transactions_count

        # 2. Delete all file records for this batch
        file_records_count = self.db.query(BatchFile).filter(
            BatchFile.batch_id == batch_id,
        ).delete(synchronize_session=False)
        stats["file_records_deleted"] = file_records_count

        # 3. Delete storage directory and files
        storage = get_storage()
        try:
            if storage.batch_directory_exists(batch_id):
                files_deleted = storage.delete_batch_directory(batch_id)
                stats["files_deleted"] = files_deleted
        except Exception as e:
            log_exception(logger, "Failed to delete batch storage directory", e, batch_id=batch_id)
            stats["file_deletion_error"] = str(e)

        # 4. Delete all delete requests for this batch (must be before batch deletion)
        delete_requests_count = self.db.query(BatchDeleteRequest).filter(
            BatchDeleteRequest.batch_id == batch_id,
        ).delete(synchronize_session=False)
        stats["delete_requests_deleted"] = delete_requests_count

        # 5. Delete the batch record
        batch = self.get_batch_by_id(batch_id)
        if batch:
            self.db.delete(batch)

        self.db.commit()

        log_operation(
            logger, "cascade_delete_batch", success=True,
            batch_id=batch_id,
            transactions_deleted=transactions_count,
            files_deleted=stats.get("files_deleted", 0),
        )
        return stats

    def get_batch_by_id(self, batch_id: str) -> Optional[Batch]:
        """Get batch by batch_id string."""
        return self.db.query(Batch).filter(Batch.batch_id == batch_id).first()

    def get_all_batches(self) -> List[Batch]:
        """Get all batches ordered by creation date (newest first)."""
        return self.db.query(Batch).order_by(Batch.created_at.desc()).all()

    def add_file_record(
        self,
        batch_id: str,
        filename: str,
        original_filename: str,
        gateway: str,
        file_size: Optional[int] = None,
        content_type: Optional[str] = None,
        uploaded_by_id: Optional[int] = None,
    ) -> BatchFile:
        """
        Add a file record to track uploaded files.

        Args:
            batch_id: The batch ID.
            filename: The stored filename (with gateway prefix).
            original_filename: The original uploaded filename.
            gateway: The gateway name.
            file_size: File size in bytes.
            content_type: MIME content type.
            uploaded_by_id: User ID of the uploader.

        Returns:
            The created BatchFile record.
        """
        file_record = BatchFile(
            batch_id=batch_id,
            filename=filename,
            original_filename=original_filename,
            gateway=gateway,
            file_size=file_size,
            content_type=content_type,
            uploaded_by_id=uploaded_by_id,
        )
        self.db.add(file_record)
        self.db.commit()
        self.db.refresh(file_record)
        return file_record

    def get_batch_files(self, batch_id: str) -> List[BatchFile]:
        """Get all file records for a batch."""
        return self.db.query(BatchFile).filter(
            BatchFile.batch_id == batch_id,
        ).order_by(BatchFile.uploaded_at.desc()).all()
