"""
File Upload Service.

Handles file uploads for reconciliation with gateway subdirectory organization.

Directory structure:
    uploads/{external_gateway}/{gateway_name}.{ext}

Each gateway directory holds at most 2 files: one external + one internal.
Uploading the same type replaces the existing file.
"""
from typing import Optional, List, Tuple, Dict, Any
from io import BytesIO
from datetime import datetime
import uuid

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.customLogging.logger import get_logger, log_operation, log_exception
from app.exceptions.exceptions import FileUploadException
from app.sqlModels.runEntities import UploadedFile
from app.storage import StorageBackend, get_storage, SUPPORTED_EXTENSIONS
from app.upload.template_generator import DEFAULT_TEMPLATE_COLUMNS
from app.config.gateways import get_gateway_from_db
from app.dataProcessing.file_transformer import FileTransformer, TransformationResult, create_transformer_from_config

logger = get_logger(__name__)

# Backwards compatibility alias
TEMPLATE_COLUMNS = DEFAULT_TEMPLATE_COLUMNS

# Maximum files per gateway subdirectory (one external + one internal)
MAX_FILES_PER_GATEWAY = 2


def get_external_gateway_for(gateway_name: str, db: Session) -> str:
    """
    Determine the external gateway name for a given upload gateway.

    External gateways map to themselves. Internal gateways (e.g., workpay_equity)
    map to their corresponding external gateway (e.g., equity).

    Args:
        gateway_name: The upload gateway name (e.g., 'equity' or 'workpay_equity').
        db: Database session for gateway lookups.

    Returns:
        The external gateway name to use as the subdirectory.

    Raises:
        FileUploadException: If gateway is not valid.
    """
    # First, try legacy gateway_configs table
    gateway_config = get_gateway_from_db(db, gateway_name)
    if gateway_config:
        if gateway_config["config_type"] == "external":
            return gateway_name
        # Internal gateway - derive the external gateway name
        if gateway_name.startswith("workpay_"):
            return gateway_name[len("workpay_"):]
        return gateway_name

    # Try unified gateway_file_configs table
    from sqlalchemy import select
    from app.sqlModels.gatewayEntities import GatewayFileConfig, Gateway

    stmt = select(GatewayFileConfig).where(
        GatewayFileConfig.name == gateway_name,
        GatewayFileConfig.is_active == True
    )
    file_config = db.execute(stmt).scalar_one_or_none()

    if file_config:
        if file_config.config_type == "external":
            return gateway_name
        # Internal config - find the associated gateway's external config name
        gateway = db.query(Gateway).filter(Gateway.id == file_config.gateway_id).first()
        if gateway:
            external_config = gateway.get_external_config()
            if external_config:
                return external_config.name
        # Fallback: derive from naming pattern
        if gateway_name.startswith("workpay_"):
            return gateway_name[len("workpay_"):]
        return gateway_name

    raise FileUploadException(f"Gateway not found: {gateway_name}")


def get_gateway_type(gateway_name: str) -> str:
    """Determine if a gateway name is external or internal."""
    if gateway_name.startswith("workpay_"):
        return "internal"
    return "external"


def get_storage_filename(gateway_name: str, extension: str) -> str:
    """
    Generate the storage filename for a gateway upload.

    Files are renamed to: {gateway_name}.{ext}
    Examples: equity.xlsx, workpay_equity.xlsx, mpesa.csv
    """
    return f"{gateway_name}.{extension}"


class FileUpload:
    """
    Handles file uploads for reconciliation.
    Uses a pluggable storage backend (local or GCS) with gateway subdirectories.
    """

    def __init__(
        self,
        db: Session,
        storage: Optional[StorageBackend] = None
    ):
        self.db = db
        self.storage = storage or get_storage()

    def validate_gateway_name(self, gateway_name: str) -> str:
        """Validate and sanitize gateway name."""
        if not gateway_name or not gateway_name.strip():
            raise FileUploadException("Gateway name is required")

        sanitized = gateway_name.strip().lower()
        if not all(c.isalnum() or c in "-_" for c in sanitized):
            raise FileUploadException("Gateway name can only contain letters, numbers, hyphens, and underscores")

        return sanitized

    def validate_file(self, file: UploadFile) -> None:
        """Validate an uploaded file (extension check)."""
        if not file:
            raise FileUploadException("File must be attached")
        if not file.filename:
            raise FileUploadException("File must have a filename")
        if not self.storage.is_supported_extension(file.filename):
            raise FileUploadException(
                f"Unsupported file format. Allowed: {', '.join(SUPPORTED_EXTENSIONS)}"
            )

    def validate_file_columns(
        self,
        content: bytes,
        filename: str,
        required_columns: Optional[List[str]] = None
    ) -> Tuple[List[str], List[str]]:
        """
        Validate that file contains required columns.

        Returns:
            Tuple of (found_columns, missing_columns).
        """
        try:
            ext = filename.lower().split('.')[-1] if '.' in filename else ''

            if ext == 'csv':
                df = pd.read_csv(BytesIO(content), nrows=0)
            elif ext in ('xlsx', 'xls'):
                df = None
                last_error = None
                for engine in ['openpyxl', 'xlrd']:
                    try:
                        df = pd.read_excel(BytesIO(content), sheet_name=0, nrows=0, engine=engine)
                        break
                    except Exception as e:
                        last_error = e
                        continue
                if df is None:
                    raise FileUploadException(f"Cannot read Excel file: {last_error}")
            else:
                raise FileUploadException(f"Cannot validate file format: {ext}")

            file_columns = [col.strip() for col in df.columns.tolist()]
            file_columns_lower = [col.lower() for col in file_columns]

            columns_to_check = required_columns if required_columns else DEFAULT_TEMPLATE_COLUMNS

            found = []
            missing = []

            for req_col in columns_to_check:
                if req_col.lower() in file_columns_lower:
                    found.append(req_col)
                else:
                    missing.append(req_col)

            return found, missing

        except FileUploadException:
            raise
        except Exception as e:
            raise FileUploadException(f"Failed to read file columns: {str(e)}")

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension without dot from filename."""
        if '.' in filename:
            return filename.rsplit('.', 1)[-1].lower()
        return ''

    def _save_archive_copy(
        self,
        external_gateway: str,
        filename_base: str,
        extension: str,
        content: bytes,
    ) -> None:
        """
        Save an immutable audit copy of a file to the archive subdirectory.

        Archive path: {external_gateway}/archive/{filename_base}_{YYYYMMDD_HHMMSS}_{uuid8}.{ext}

        This is best-effort — failures are logged as warnings and never propagate
        to the caller, so a storage issue never blocks a legitimate upload.
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            archive_filename = f"{filename_base}_{timestamp}_{unique_id}.{extension}"
            self.storage.archive_file(external_gateway, archive_filename, content)
            logger.info(
                f"Archived copy saved: {external_gateway}/archive/{archive_filename}",
                extra={"gateway": external_gateway},
            )
        except Exception as e:
            logger.warning(
                f"Failed to save archive copy for {filename_base}.{extension}: {e}",
                extra={"gateway": external_gateway},
            )

    def check_gateway_file_limit(
        self,
        gateway_name: str,
        external_gateway: str,
    ) -> None:
        """
        Check that adding a file doesn't exceed the max files per gateway.

        Each gateway subdirectory can have at most MAX_FILES_PER_GATEWAY files
        (one external, one internal). If a file with the same base name already
        exists, it will be replaced (not counted as additional).
        """
        existing_files = self.storage.list_files(external_gateway)
        storage_filename_base = gateway_name

        # Filter out raw files (_raw suffix) - they don't count toward the limit
        countable_files = [
            f for f in existing_files
            if not (f.rsplit('.', 1)[0] if '.' in f else f).endswith('_raw')
        ]

        # Check if this upload would replace an existing file
        for f in countable_files:
            name_without_ext = f.rsplit('.', 1)[0] if '.' in f else f
            if name_without_ext == storage_filename_base:
                return  # Replacement - allowed

        # New file - check limit
        if len(countable_files) >= MAX_FILES_PER_GATEWAY:
            raise FileUploadException(
                f"Gateway '{external_gateway}' already has {MAX_FILES_PER_GATEWAY} files "
                f"(maximum reached). Delete an existing file first."
            )

    async def save_file(
        self,
        file: UploadFile,
        gateway_name: str,
        content: Optional[bytes] = None,
    ) -> Tuple[str, str, str]:
        """
        Save an uploaded file to storage in the gateway subdirectory.

        The file is renamed to {gateway_name}.{ext} and stored in
        {external_gateway}/ directory.

        Args:
            file: The uploaded file.
            gateway_name: Validated gateway name.
            content: Optional pre-read file content.

        Returns:
            Tuple of (storage_filename, external_gateway, storage_path).
        """
        try:
            self.validate_file(file)

            external_gateway = get_external_gateway_for(gateway_name, self.db)
            extension = self._get_file_extension(file.filename)
            storage_filename = get_storage_filename(gateway_name, extension)

            # Check file limit
            self.check_gateway_file_limit(gateway_name, external_gateway)

            # Delete existing file with same base name but different extension
            existing_files = self.storage.list_files(external_gateway)
            for existing in existing_files:
                name_without_ext = existing.rsplit('.', 1)[0] if '.' in existing else existing
                if name_without_ext == gateway_name and existing != storage_filename:
                    self.storage.delete_file(external_gateway, existing)
                    logger.info(
                        f"Replaced existing file {existing} with {storage_filename}",
                        extra={"gateway": external_gateway}
                    )

            # Read content if not already read
            if content is None:
                content = await file.read()

            # Save an immutable audit copy before writing the active file
            self._save_archive_copy(external_gateway, gateway_name, extension, content)

            # Ensure gateway directory exists
            self.storage.ensure_gateway_directory(external_gateway)

            # Save to gateway subdirectory
            storage_path = self.storage.save_file(
                external_gateway, storage_filename, content
            )

            log_operation(
                logger, "save_file", success=True,
                gateway=external_gateway,
                file_name=storage_filename,
            )

            return storage_filename, external_gateway, storage_path

        except FileUploadException:
            raise
        except Exception as e:
            log_exception(logger, "Unexpected error saving file", e)
            raise FileUploadException(f"Unexpected error saving file: {str(e)}")

    def delete_file(self, filename: str, gateway: str) -> bool:
        """
        Delete a file from storage and its database record.

        Args:
            filename: The stored filename to delete.
            gateway: The gateway subdirectory.

        Returns:
            True if file was deleted.
        """
        # Delete from storage
        deleted = self.storage.delete_file(gateway, filename)
        if not deleted:
            raise FileUploadException(f"File not found in storage: {gateway}/{filename}")

        # Delete the database record
        file_record = self.db.query(UploadedFile).filter(
            UploadedFile.gateway == gateway,
            UploadedFile.filename == filename,
        ).first()

        if file_record:
            self.db.delete(file_record)
            self.db.commit()

        log_operation(
            logger, "delete_file", success=True,
            gateway=gateway, file_name=filename,
        )
        return True

    def get_file_content(self, filename: str, gateway: str) -> bytes:
        """Read file content for download."""
        return self.storage.read_file_bytes(gateway, filename)

    def list_gateway_files(self, gateway: str) -> List[str]:
        """List files in a gateway subdirectory."""
        return self.storage.list_files(gateway)

    async def save_raw_file(
        self,
        file: UploadFile,
        gateway_name: str,
        external_gateway: str,
        content: bytes,
    ) -> str:
        """
        Save a raw file alongside the normalized file.

        Raw files are stored with a _raw suffix:
            {external_gateway}/{gateway_name}_raw.{ext}

        Args:
            file: The uploaded file.
            gateway_name: Validated gateway name.
            external_gateway: The external gateway (subdirectory name).
            content: Pre-read file content.

        Returns:
            Storage path for the raw file.
        """
        try:
            extension = self._get_file_extension(file.filename)
            raw_filename = f"{gateway_name}_raw.{extension}"

            # Save an immutable audit copy of the raw file
            self._save_archive_copy(external_gateway, f"{gateway_name}_raw", extension, content)

            # Ensure gateway directory exists
            self.storage.ensure_gateway_directory(external_gateway)

            # Save raw file
            storage_path = self.storage.save_file(
                external_gateway, raw_filename, content
            )

            log_operation(
                logger, "save_raw_file", success=True,
                gateway=external_gateway,
                file_name=raw_filename,
            )

            return storage_path

        except Exception as e:
            log_exception(logger, "Error saving raw file", e)
            raise FileUploadException(f"Failed to save raw file: {str(e)}")

    async def transform_and_save(
        self,
        file: UploadFile,
        gateway_name: str,
        content: bytes,
        gateway_config: Dict[str, Any],
    ) -> Tuple[str, str, str, TransformationResult]:
        """
        Transform a raw file and save both raw and normalized versions.

        1. Save raw file to {gateway}/{gateway_name}_raw.{ext}
        2. Transform using gateway configuration
        3. Save normalized CSV to {gateway}/{gateway_name}.csv

        Args:
            file: The uploaded file.
            gateway_name: Validated gateway name.
            content: Pre-read file content.
            gateway_config: Gateway file configuration dict.

        Returns:
            Tuple of (normalized_filename, external_gateway, storage_path, transformation_result).
        """
        try:
            self.validate_file(file)

            external_gateway = get_external_gateway_for(gateway_name, self.db)

            # Check file limit
            self.check_gateway_file_limit(gateway_name, external_gateway)

            # Save raw file first
            await self.save_raw_file(file, gateway_name, external_gateway, content)

            # Create transformer from gateway config
            transformer = create_transformer_from_config(gateway_config)

            # Transform the file
            result = transformer.transform(content, file.filename)

            if not result.success:
                raise FileUploadException(
                    f"File transformation failed: {'; '.join(result.errors)}"
                )

            # Save normalized file as CSV
            normalized_filename = f"{gateway_name}.csv"

            # Delete existing normalized file if any
            existing_files = self.storage.list_files(external_gateway)
            for existing in existing_files:
                name_without_ext = existing.rsplit('.', 1)[0] if '.' in existing else existing
                if name_without_ext == gateway_name:
                    self.storage.delete_file(external_gateway, existing)
                    logger.info(
                        f"Replaced existing file {existing} with {normalized_filename}",
                        extra={"gateway": external_gateway}
                    )

            # Save normalized CSV
            storage_path = self.storage.save_file(
                external_gateway, normalized_filename, result.normalized_data
            )

            log_operation(
                logger, "transform_and_save", success=True,
                gateway=external_gateway,
                file_name=normalized_filename,
                rows=result.row_count,
            )

            return normalized_filename, external_gateway, storage_path, result

        except FileUploadException:
            raise
        except Exception as e:
            log_exception(logger, "Error in transform_and_save", e)
            raise FileUploadException(f"Transformation error: {str(e)}")
