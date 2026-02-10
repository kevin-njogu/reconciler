"""Pydantic models for reconciliation runs and uploaded files."""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class ReconciliationRunResponse(BaseModel):
    """Response model for a reconciliation run."""
    id: int
    run_id: str
    gateway: str
    status: str
    total_external: int
    total_internal: int
    matched: int
    unmatched_external: int
    unmatched_internal: int
    carry_forward_matched: int
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RunListResponse(BaseModel):
    """Response for reconciliation run list."""
    count: int
    runs: List[ReconciliationRunResponse]


class UploadedFileResponse(BaseModel):
    """Response model for an uploaded file."""
    id: int
    filename: str
    original_filename: str
    gateway: str
    gateway_type: str
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    is_processed: bool

    class Config:
        from_attributes = True


class UploadedFileListResponse(BaseModel):
    """Response for uploaded file list."""
    count: int
    files: List[UploadedFileResponse]
