"""
File Upload Service.

Handles file uploads for reconciliation batches with gateway subdirectory
organization. Each gateway gets a subdirectory within the batch directory,
containing at most 2 files: one external and one internal.

Directory structure (hybrid approach):
    uploads/{batch_id}/{external_gateway}/raw/{original_filename}  # Raw uploads
    uploads/{batch_id}/{external_gateway}/{gateway_name}.csv        # Normalized files
"""
from typing import Optional, List, Tuple, Dict, Any
from io import BytesIO
from dataclasses import dataclass

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.customLogging.logger import get_logger, log_operation, log_exception
from app.exceptions.exceptions import FileUploadException
from app.sqlModels.batchEntities import BatchFile
from app.storage import StorageBackend, get_storage, SUPPORTED_EXTENSIONS
from app.upload.batch_creation import BatchService
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

    Checks both legacy (gateway_configs) and unified (gateway_file_configs) systems.

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
        if gateway_config["type"] == "external":
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


def get_storage_filename(gateway_name: str, extension: str) -> str:
    """
    Generate the storage filename for a gateway upload.

    Files are renamed to: {gateway_name}.{ext}
    Examples: equity.xlsx, workpay_equity.xlsx, mpesa.csv

    Args:
        gateway_name: The upload gateway name.
        extension: File extension (without dot).

    Returns:
        The storage filename.
    """
    return f"{gateway_name}.{extension}"


class FileUpload:
    """
    Handles file uploads for reconciliation batches.
    Uses a pluggable storage backend (local or GCS) with gateway subdirectories.
    """

    def __init__(
        self,
        db: Session,
        storage: Optional[StorageBackend] = None
    ):
        """
        Initialize FileUpload.

        Args:
            db: Database session for batch management.
            storage: Storage backend. Defaults to environment-configured storage.
        """
        self.db = db
        self.batch_service = BatchService(db)
        self.storage = storage or get_storage()

    def validate_gateway_name(self, gateway_name: str) -> str:
        """
        Validate and sanitize gateway name.

        Args:
            gateway_name: The gateway name to validate.

        Returns:
            Sanitized gateway name.
        """
        if not gateway_name or not gateway_name.strip():
            raise FileUploadException("Gateway name is required")

        sanitized = gateway_name.strip().lower()
        if not all(c.isalnum() or c in "-_" for c in sanitized):
            raise FileUploadException("Gateway name can only contain letters, numbers, hyphens, and underscores")

        return sanitized

    def validate_file(self, file: UploadFile) -> None:
        """
        Validate an uploaded file (extension check).

        Args:
            file: The uploaded file to validate.
        """
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

        Args:
            content: File content as bytes.
            filename: Original filename (to determine format).
            required_columns: List of required column names. Defaults to standard template columns.

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

    def check_gateway_file_limit(
        self,
        batch_id: str,
        gateway_name: str,
        external_gateway: str,
    ) -> None:
        """
        Check that adding a file doesn't exceed the max files per gateway.

        Each gateway subdirectory can have at most MAX_FILES_PER_GATEWAY files
        (one external, one internal). If a file with the same base name already
        exists, it will be replaced (not counted as additional).

        Args:
            batch_id: The batch identifier.
            gateway_name: The upload gateway name.
            external_gateway: The external gateway (subdirectory name).

        Raises:
            FileUploadException: If the gateway already has max files and this
                                 would be a new file (not a replacement).
        """
        existing_files = self.storage.list_files(batch_id, gateway=external_gateway)
        storage_filename_base = gateway_name

        # Check if this upload would replace an existing file
        for f in existing_files:
            name_without_ext = f.rsplit('.', 1)[0] if '.' in f else f
            if name_without_ext == storage_filename_base:
                return  # Replacement - allowed

        # New file - check limit
        if len(existing_files) >= MAX_FILES_PER_GATEWAY:
            raise FileUploadException(
                f"Gateway '{external_gateway}' already has {MAX_FILES_PER_GATEWAY} files "
                f"(maximum reached). Delete an existing file first."
            )

    async def save_file(
        self,
        file: UploadFile,
        gateway_name: str,
        batch_id: str,
        content: Optional[bytes] = None,
    ) -> Tuple[str, str, str]:
        """
        Save an uploaded file to storage in the gateway subdirectory.

        The file is renamed to {gateway_name}.{ext} and stored in
        {batch_id}/{external_gateway}/ directory.

        Args:
            file: The uploaded file.
            gateway_name: Validated gateway name.
            batch_id: The batch ID.
            content: Optional pre-read file content.

        Returns:
            Tuple of (storage_filename, external_gateway, storage_path).

        Raises:
            FileUploadException: On validation or storage errors.
        """
        try:
            self.validate_file(file)

            external_gateway = get_external_gateway_for(gateway_name, self.db)
            extension = self._get_file_extension(file.filename)
            storage_filename = get_storage_filename(gateway_name, extension)

            # Check file limit
            self.check_gateway_file_limit(batch_id, gateway_name, external_gateway)

            # Delete existing file with same base name but different extension
            existing_files = self.storage.list_files(batch_id, gateway=external_gateway)
            for existing in existing_files:
                name_without_ext = existing.rsplit('.', 1)[0] if '.' in existing else existing
                if name_without_ext == gateway_name and existing != storage_filename:
                    self.storage.delete_file(batch_id, existing, gateway=external_gateway)
                    logger.info(
                        f"Replaced existing file {existing} with {storage_filename}",
                        extra={"batch_id": batch_id, "gateway": external_gateway}
                    )

            # Read content if not already read
            if content is None:
                content = await file.read()

            # Save to gateway subdirectory
            storage_path = self.storage.save_file(
                batch_id, storage_filename, content, gateway=external_gateway
            )

            log_operation(
                logger, "save_file", success=True,
                batch_id=batch_id, gateway=external_gateway,
                file_name=storage_filename,
            )

            return storage_filename, external_gateway, storage_path

        except FileUploadException:
            raise
        except Exception as e:
            log_exception(logger, "Unexpected error saving file", e, batch_id=batch_id)
            raise FileUploadException(f"Unexpected error saving file: {str(e)}")

    def delete_file(self, batch_id: str, filename: str, gateway: str) -> bool:
        """
        Delete a file from storage and its database record.

        Args:
            batch_id: The batch identifier.
            filename: The stored filename to delete.
            gateway: The gateway subdirectory.

        Returns:
            True if file was deleted.

        Raises:
            FileUploadException: If file not found or deletion fails.
        """
        # Delete from storage
        deleted = self.storage.delete_file(batch_id, filename, gateway=gateway)
        if not deleted:
            raise FileUploadException(f"File not found in storage: {gateway}/{filename}")

        # Delete the database record
        file_record = self.db.query(BatchFile).filter(
            BatchFile.batch_id == batch_id,
            BatchFile.filename == filename,
            BatchFile.gateway == gateway,
        ).first()

        if file_record:
            self.db.delete(file_record)
            self.db.commit()

        log_operation(
            logger, "delete_file", success=True,
            batch_id=batch_id, gateway=gateway, file_name=filename,
        )
        return True

    def get_file_content(self, batch_id: str, filename: str, gateway: str) -> bytes:
        """
        Read file content for download.

        Args:
            batch_id: The batch identifier.
            filename: The stored filename.
            gateway: The gateway subdirectory.

        Returns:
            File content as bytes.
        """
        return self.storage.read_file_bytes(batch_id, filename, gateway=gateway)

    def list_gateway_files(self, batch_id: str, gateway: str) -> List[str]:
        """
        List files in a gateway subdirectory.

        Args:
            batch_id: The batch identifier.
            gateway: The gateway name.

        Returns:
            List of filenames.
        """
        return self.storage.list_files(batch_id, gateway=gateway)

    async def save_raw_file(
        self,
        file: UploadFile,
        gateway_name: str,
        batch_id: str,
        external_gateway: str,
        content: bytes,
    ) -> str:
        """
        Save a raw file to the raw/ subdirectory.

        Args:
            file: The uploaded file.
            gateway_name: Validated gateway name.
            batch_id: The batch ID.
            external_gateway: The external gateway (subdirectory name).
            content: Pre-read file content.

        Returns:
            Storage path for the raw file.
        """
        try:
            extension = self._get_file_extension(file.filename)
            raw_filename = f"{gateway_name}_raw.{extension}"
            raw_path = f"{external_gateway}/raw"

            # Ensure raw directory exists
            self.storage.ensure_gateway_directory(batch_id, raw_path)

            # Save raw file
            storage_path = self.storage.save_file(
                batch_id, raw_filename, content, gateway=raw_path
            )

            log_operation(
                logger, "save_raw_file", success=True,
                batch_id=batch_id, gateway=raw_path,
                file_name=raw_filename,
            )

            return storage_path

        except Exception as e:
            log_exception(logger, "Error saving raw file", e, batch_id=batch_id)
            raise FileUploadException(f"Failed to save raw file: {str(e)}")

    async def transform_and_save(
        self,
        file: UploadFile,
        gateway_name: str,
        batch_id: str,
        content: bytes,
        gateway_config: Dict[str, Any],
    ) -> Tuple[str, str, str, TransformationResult]:
        """
        Transform a raw file and save both raw and normalized versions.

        This implements the hybrid approach:
        1. Save raw file to {batch_id}/{gateway}/raw/
        2. Transform using gateway configuration
        3. Save normalized CSV to {batch_id}/{gateway}/

        Args:
            file: The uploaded file.
            gateway_name: Validated gateway name.
            batch_id: The batch ID.
            content: Pre-read file content.
            gateway_config: Gateway file configuration dict.

        Returns:
            Tuple of (normalized_filename, external_gateway, storage_path, transformation_result).

        Raises:
            FileUploadException: On validation or transformation errors.
        """
        try:
            self.validate_file(file)

            external_gateway = get_external_gateway_for(gateway_name, self.db)

            # Check file limit
            self.check_gateway_file_limit(batch_id, gateway_name, external_gateway)

            # Save raw file first
            await self.save_raw_file(file, gateway_name, batch_id, external_gateway, content)

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
            existing_files = self.storage.list_files(batch_id, gateway=external_gateway)
            for existing in existing_files:
                name_without_ext = existing.rsplit('.', 1)[0] if '.' in existing else existing
                if name_without_ext == gateway_name:
                    self.storage.delete_file(batch_id, existing, gateway=external_gateway)
                    logger.info(
                        f"Replaced existing file {existing} with {normalized_filename}",
                        extra={"batch_id": batch_id, "gateway": external_gateway}
                    )

            # Save normalized CSV
            storage_path = self.storage.save_file(
                batch_id, normalized_filename, result.normalized_data, gateway=external_gateway
            )

            log_operation(
                logger, "transform_and_save", success=True,
                batch_id=batch_id, gateway=external_gateway,
                file_name=normalized_filename,
                rows=result.row_count,
            )

            return normalized_filename, external_gateway, storage_path, result

        except FileUploadException:
            raise
        except Exception as e:
            log_exception(logger, "Error in transform_and_save", e, batch_id=batch_id)
            raise FileUploadException(f"Transformation error: {str(e)}")
