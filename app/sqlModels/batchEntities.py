"""
Batch, BatchFile, and BatchDeleteRequest Database Models.

Defines Batch (reconciliation batch), BatchFile (uploaded files),
and BatchDeleteRequest (maker-checker delete workflow) tables.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database.mysql_configs import Base


class BatchStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class DeleteRequestStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Batch(Base):
    """
    Batch model for grouping reconciliation operations.

    A batch is the key control for each reconciliation session.
    All transactions reconciled under a batch are tagged with its batch_id.
    Only the creator can close a batch, and only when all transactions are reconciled.
    """
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(20), default=BatchStatus.PENDING.value, nullable=False)
    description = Column(String(500), nullable=True)

    # Audit fields
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id], backref="created_batches")
    files = relationship("BatchFile", back_populates="batch", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('ix_batch_status_created', 'status', 'created_at'),
        Index('ix_batch_created_by', 'created_by_id'),
    )

    def __repr__(self):
        return f"<Batch(id={self.id}, batch_id='{self.batch_id}', status='{self.status}')>"


class BatchFile(Base):
    """
    BatchFile model for tracking uploaded files.

    Stores file metadata for audit trail and file management.
    """
    __tablename__ = "batch_files"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(100), ForeignKey("batches.batch_id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    gateway = Column(String(50), nullable=False)
    file_size = Column(BigInteger, nullable=True)
    content_type = Column(String(100), nullable=True)

    # Audit fields
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    batch = relationship("Batch", back_populates="files")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id], backref="uploaded_files")

    # Indexes
    __table_args__ = (
        Index('ix_batch_file_batch_gateway', 'batch_id', 'gateway'),
        Index('ix_batch_file_uploaded_by', 'uploaded_by_id'),
    )

    def __repr__(self):
        return f"<BatchFile(id={self.id}, batch_id='{self.batch_id}', filename='{self.filename}')>"


class BatchDeleteRequest(Base):
    """
    BatchDeleteRequest model for maker-checker batch deletion workflow.

    Users initiate delete requests which must be approved by an admin.
    Approval triggers cascade deletion of the batch, its files, and transactions.
    """
    __tablename__ = "batch_delete_requests"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(100), ForeignKey("batches.batch_id"), nullable=False, index=True)
    status = Column(String(20), default=DeleteRequestStatus.PENDING.value, nullable=False)
    reason = Column(String(500), nullable=True)

    # Requester
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Reviewer
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    batch = relationship("Batch", backref="delete_requests")
    requested_by = relationship("User", foreign_keys=[requested_by_id], backref="batch_delete_requests")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id], backref="reviewed_batch_deletes")

    # Indexes
    __table_args__ = (
        Index('ix_batch_delete_request_status', 'status'),
        Index('ix_batch_delete_request_batch', 'batch_id', 'status'),
        Index('ix_batch_delete_request_requested_by', 'requested_by_id'),
    )

    def __repr__(self):
        return f"<BatchDeleteRequest(id={self.id}, batch_id='{self.batch_id}', status='{self.status}')>"
