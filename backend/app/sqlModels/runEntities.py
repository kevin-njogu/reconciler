"""
ReconciliationRun and UploadedFile Database Models.

Defines ReconciliationRun (lightweight reconciliation session) and
UploadedFile (uploaded file tracking) tables.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, BigInteger, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.mysql_configs import Base


class ReconciliationRun(Base):
    """
    Reconciliation run model — a lightweight record of each reconciliation execution.

    Auto-created when reconciliation is saved. Stores summary statistics.
    Replaces the old heavyweight Batch model.
    """
    __tablename__ = "reconciliation_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(100), unique=True, index=True, nullable=False)
    gateway = Column(String(50), nullable=False, index=True)
    status = Column(String(20), default="completed", nullable=False)

    # Summary statistics
    total_external = Column(Integer, default=0, nullable=False)
    total_internal = Column(Integer, default=0, nullable=False)
    matched = Column(Integer, default=0, nullable=False)
    unmatched_external = Column(Integer, default=0, nullable=False)
    unmatched_internal = Column(Integer, default=0, nullable=False)
    carry_forward_matched = Column(Integer, default=0, nullable=False)

    # Audit fields
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id], backref="reconciliation_runs")

    # Indexes
    __table_args__ = (
        Index('ix_run_gateway_created', 'gateway', 'created_at'),
        Index('ix_run_created_by', 'created_by_id'),
    )

    def __repr__(self):
        return f"<ReconciliationRun(id={self.id}, run_id='{self.run_id}', gateway='{self.gateway}')>"


class UploadedFile(Base):
    """
    Uploaded file tracking model.

    Stores metadata for files uploaded per gateway. Each gateway can have
    one external file and one internal file at a time.
    """
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    gateway = Column(String(50), nullable=False, index=True)
    gateway_type = Column(String(20), nullable=False)  # "external" or "internal"
    file_size = Column(BigInteger, nullable=True)
    content_type = Column(String(100), nullable=True)
    is_processed = Column(Boolean, default=False, nullable=False)

    # Audit fields
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id], backref="uploaded_files_records")

    # Indexes
    __table_args__ = (
        Index('ix_uploaded_file_gateway_type', 'gateway', 'gateway_type'),
        Index('ix_uploaded_file_uploaded_by', 'uploaded_by_id'),
    )

    def __repr__(self):
        return f"<UploadedFile(id={self.id}, gateway='{self.gateway}', filename='{self.filename}')>"
