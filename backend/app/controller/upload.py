"""
File Upload Controller.

Handles file uploads for reconciliation with gateway subdirectory organization.

Storage structure:
    uploads/{external_gateway}/{gateway_name}.{ext}

Endpoints:
- POST /file: Upload a file to a gateway subdirectory
- DELETE /file: Delete an uploaded file
- GET /file/download: Download an uploaded file
- GET /files: List files for a gateway
- POST /validate: Validate file columns
- GET /template: Download upload template
- GET /template-info: Get template column info
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, UploadFile, Depends, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from starlette.responses import JSONResponse
from io import BytesIO

from app.customLogging.logger import get_logger, log_operation
from app.database.mysql_configs import get_database
from app.exceptions.exceptions import FileUploadException
from app.upload.upload_files import FileUpload, get_external_gateway_for, get_gateway_type
from app.upload.template_generator import TemplateGenerator, TemplateFormat, DEFAULT_TEMPLATE_COLUMNS
from app.auth.dependencies import require_active_user
from app.sqlModels.authEntities import User
from app.sqlModels.runEntities import UploadedFile
from app.sqlModels.gatewayEntities import GatewayFileConfig
from app.config.gateways import is_valid_upload_gateway, get_all_upload_gateways
from app.middleware.security import MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB

logger = get_logger(__name__)

router = APIRouter(prefix='/api/v1/upload', tags=['File Upload Endpoints'])

TEMPLATE_COLUMNS = DEFAULT_TEMPLATE_COLUMNS


def validate_gateway_for_upload(gateway_name: str, db: Session) -> str:
    """Validate that the gateway name is valid for file uploads."""
    normalized = gateway_name.strip().lower()
    if not is_valid_upload_gateway(normalized, db):
        valid_gateways = get_all_upload_gateways(db)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid gateway '{gateway_name}'. Valid upload gateways: {valid_gateways}"
        )
    return normalized


def get_content_type(filename: str) -> str:
    """Get content type based on file extension."""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    content_types = {
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'xls': 'application/vnd.ms-excel',
        'csv': 'text/csv',
    }
    return content_types.get(ext, 'application/octet-stream')


@router.post("/file", status_code=201)
async def upload_file(
    gateway_name: str = Query(..., description="Gateway name (e.g., 'equity', 'workpay_equity')"),
    skip_validation: bool = Query(default=False, description="Skip column validation (legacy mode only)"),
    transform: bool = Query(default=False, description="Transform raw file using gateway column mapping"),
    file: UploadFile = File(...),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Upload a file to a gateway subdirectory.

    Two modes:
    - **Legacy mode** (transform=false): Expects file with template columns.
      Validates columns and stores as-is.
    - **Transform mode** (transform=true): Accepts raw files from banks/systems.
      Uses gateway column_mapping to transform and stores both raw and normalized files.

    Storage structure:
    - Legacy: {gateway}/{gateway_name}.{ext}
    - Transform raw: {gateway}/{gateway_name}_raw.{ext}
    - Transform normalized: {gateway}/{gateway_name}.csv

    Max 2 files per gateway directory (one external, one internal).
    Uploading the same type replaces the existing file.
    """
    try:
        # Validate gateway
        validated_gateway = validate_gateway_for_upload(gateway_name, db)

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Validate file size before processing
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "File too large",
                    "file_size_mb": round(file_size / 1024 / 1024, 2),
                    "max_size_mb": MAX_FILE_SIZE_MB,
                    "message": f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({MAX_FILE_SIZE_MB}MB)"
                }
            )

        uploader = FileUpload(db)

        if transform:
            return await _handle_transform_upload(
                uploader, file, validated_gateway, content,
                file_size, current_user, db
            )
        else:
            return await _handle_legacy_upload(
                uploader, file, validated_gateway, content,
                file_size, skip_validation, current_user, db
            )

    except HTTPException:
        raise
    except FileUploadException as e:
        logger.warning(f"File upload failed: {str(e)}", extra={"gateway": gateway_name})
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


async def _handle_legacy_upload(
    uploader: FileUpload,
    file: UploadFile,
    gateway_name: str,
    content: bytes,
    file_size: int,
    skip_validation: bool,
    current_user: User,
    db: Session,
):
    """Handle legacy upload mode (template validation)."""
    # Validate file columns unless skipped
    validation_result = None
    if not skip_validation:
        found_columns, missing_columns = uploader.validate_file_columns(content, file.filename)
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "File is missing required columns",
                    "missing_columns": missing_columns,
                    "found_columns": found_columns,
                    "required_columns": list(TEMPLATE_COLUMNS),
                    "hint": "Download the template and ensure your file has all required columns, or use transform=true to auto-transform raw files."
                }
            )
        validation_result = {"found_columns": found_columns, "missing_columns": missing_columns}

    # Reset file position for upload
    await file.seek(0)

    # Save file to gateway subdirectory
    storage_filename, external_gateway, storage_path = await uploader.save_file(
        file, gateway_name, content=content
    )

    # Determine gateway type
    gw_type = get_gateway_type(gateway_name)

    # Remove any existing DB record for this slot (replacement)
    existing_record = db.query(UploadedFile).filter(
        UploadedFile.gateway == external_gateway,
        UploadedFile.filename.like(f"{gateway_name}.%"),
    ).first()
    if existing_record:
        db.delete(existing_record)
        db.flush()

    # Track file in database
    file_record = UploadedFile(
        filename=storage_filename,
        original_filename=file.filename,
        gateway=external_gateway,
        gateway_type=gw_type,
        file_size=file_size,
        content_type=get_content_type(file.filename),
        uploaded_by_id=current_user.id,
    )
    db.add(file_record)
    db.commit()

    response_content = {
        "message": f"{storage_filename} uploaded successfully",
        "gateway": external_gateway,
        "upload_gateway": gateway_name,
        "filename": storage_filename,
        "original_filename": file.filename,
        "file_size": file_size,
        "uploaded_by": current_user.username,
        "mode": "legacy",
    }

    if validation_result:
        response_content["validation"] = validation_result

    log_operation(
        logger, "upload_file", success=True,
        gateway=external_gateway,
        file_name=storage_filename, user=current_user.username,
    )

    return JSONResponse(content=response_content, status_code=201)


async def _handle_transform_upload(
    uploader: FileUpload,
    file: UploadFile,
    gateway_name: str,
    content: bytes,
    file_size: int,
    current_user: User,
    db: Session,
):
    """Handle transform upload mode (raw file transformation)."""
    # Get gateway file configuration
    stmt = select(GatewayFileConfig).where(GatewayFileConfig.name == gateway_name)
    gateway_config = db.execute(stmt).scalar_one_or_none()

    if not gateway_config:
        raise HTTPException(
            status_code=400,
            detail=f"Gateway configuration not found for '{gateway_name}'. Configure column mapping in Gateway Settings first."
        )

    # Build config dict for transformer
    config_dict = gateway_config.to_dict()

    # Reset file position for upload
    await file.seek(0)

    # Transform and save
    storage_filename, external_gateway, storage_path, transform_result = await uploader.transform_and_save(
        file, gateway_name, content, config_dict
    )

    # Determine gateway type
    gw_type = get_gateway_type(gateway_name)

    # Remove any existing DB record for this slot (replacement)
    existing_record = db.query(UploadedFile).filter(
        UploadedFile.gateway == external_gateway,
        UploadedFile.filename.like(f"{gateway_name}.%"),
    ).first()
    if existing_record:
        db.delete(existing_record)
        db.flush()

    # Track normalized file in database
    file_record = UploadedFile(
        filename=storage_filename,
        original_filename=file.filename,
        gateway=external_gateway,
        gateway_type=gw_type,
        file_size=len(transform_result.normalized_data) if transform_result.normalized_data else 0,
        content_type="text/csv",
        uploaded_by_id=current_user.id,
    )
    db.add(file_record)
    db.commit()

    response_content = {
        "message": f"File transformed and saved as {storage_filename}",
        "gateway": external_gateway,
        "upload_gateway": gateway_name,
        "filename": storage_filename,
        "original_filename": file.filename,
        "original_file_size": file_size,
        "normalized_file_size": len(transform_result.normalized_data) if transform_result.normalized_data else 0,
        "uploaded_by": current_user.username,
        "mode": "transform",
        "transformation": {
            "success": transform_result.success,
            "row_count": transform_result.row_count,
            "column_mapping_used": transform_result.column_mapping_used,
            "unmapped_columns": transform_result.unmapped_columns,
            "warnings": transform_result.warnings,
        }
    }

    log_operation(
        logger, "upload_file_transform", success=True,
        gateway=external_gateway,
        file_name=storage_filename, user=current_user.username,
        rows=transform_result.row_count,
    )

    return JSONResponse(content=response_content, status_code=201)


@router.delete("/file")
async def delete_file(
    filename: str = Query(..., description="Stored filename to delete"),
    gateway: str = Query(..., description="Gateway subdirectory name"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Delete an uploaded file.

    The file is removed from both storage and the database record.
    """
    try:
        uploader = FileUpload(db)
        uploader.delete_file(filename, gateway)

        log_operation(
            logger, "delete_file", success=True,
            gateway=gateway,
            file_name=filename, user=current_user.username,
        )

        return JSONResponse(content={
            "message": f"File {filename} deleted successfully",
            "gateway": gateway,
            "filename": filename,
        })

    except HTTPException:
        raise
    except FileUploadException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error deleting file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.get("/file/download")
async def download_file(
    filename: str = Query(..., description="Stored filename to download"),
    gateway: str = Query(..., description="Gateway subdirectory name"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Download an uploaded file.

    Returns the file as a streaming response with appropriate content type.
    """
    try:
        uploader = FileUpload(db)
        content = uploader.get_file_content(filename, gateway)

        content_type = get_content_type(filename)

        return StreamingResponse(
            BytesIO(content),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(content)),
            }
        )

    except HTTPException:
        raise
    except FileUploadException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error downloading file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@router.get("/files")
async def list_files(
    gateway: Optional[str] = Query(None, description="Filter by gateway"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    List uploaded files, optionally filtered by gateway.

    Returns file records from the database with their metadata.
    """
    try:
        query = db.query(UploadedFile)
        if gateway:
            query = query.filter(UploadedFile.gateway == gateway.lower().strip())

        files = query.order_by(UploadedFile.uploaded_at.desc()).all()

        return JSONResponse(content={
            "gateway_filter": gateway,
            "file_count": len(files),
            "files": [
                {
                    "id": f.id,
                    "filename": f.filename,
                    "original_filename": f.original_filename,
                    "gateway": f.gateway,
                    "gateway_type": f.gateway_type,
                    "file_size": f.file_size,
                    "content_type": f.content_type,
                    "is_processed": f.is_processed,
                    "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
                    "uploaded_by": f.uploaded_by.username if f.uploaded_by else None,
                }
                for f in files
            ],
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing files: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.post("/validate")
async def validate_file_columns(
    file: UploadFile = File(...),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Validate file columns before upload.

    Checks if the file contains required columns:
    Date, Reference, Details, Debit, Credit

    Column matching is case-insensitive.
    """
    try:
        content = await file.read()
        file_size = len(content)

        # Validate file size before processing
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "File too large",
                    "file_size_mb": round(file_size / 1024 / 1024, 2),
                    "max_size_mb": MAX_FILE_SIZE_MB,
                    "message": f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({MAX_FILE_SIZE_MB}MB)"
                }
            )

        uploader = FileUpload(db)
        uploader.validate_file(file)

        found_columns, missing_columns = uploader.validate_file_columns(content, file.filename)

        return JSONResponse(
            content={
                "valid": len(missing_columns) == 0,
                "filename": file.filename,
                "file_size": len(content),
                "required_columns": list(TEMPLATE_COLUMNS),
                "found_columns": found_columns,
                "missing_columns": missing_columns,
                "message": "All required columns found" if len(missing_columns) == 0
                    else f"Missing columns: {', '.join(missing_columns)}",
            }
        )
    except FileUploadException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during file validation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate file: {str(e)}")


@router.get("/template")
async def download_template(
    format: Optional[str] = Query(default="xlsx", description="Template format: xlsx or csv"),
    current_user: User = Depends(require_active_user)
):
    """
    Download upload template.

    Template columns: Date, Reference, Details, Debit, Credit
    The same template is used for all gateways.
    """
    try:
        generator = TemplateGenerator()
        template_format = TemplateFormat.CSV if format and format.lower() == "csv" else TemplateFormat.XLSX

        template_date = date.today()
        file_content = generator.generate_template(template_date, template_format)

        log_operation(
            logger, "download_template", success=True,
            format=template_format.value, user=current_user.username,
        )

        return StreamingResponse(
            BytesIO(file_content),
            media_type=generator.get_content_type(template_format),
            headers={
                "Content-Disposition": f"attachment; filename={generator.get_template_filename(template_format)}"
            }
        )
    except FileUploadException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate template: {str(e)}")


@router.get("/template-info")
async def get_template_info(
    current_user: User = Depends(require_active_user)
):
    """Get template column information for the download popup."""
    generator = TemplateGenerator()
    return JSONResponse(content=generator.get_column_info())
