"""
Gateway Configuration API Endpoints.

Provides CRUD operations for managing payment gateway configurations with
maker-checker approval workflow:
- Users (role=user) can submit change requests
- Admins (role=admin) can approve/reject change requests
- Super admins have no access to gateway management
"""
import math
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, or_, func as sa_func, update
from starlette.responses import JSONResponse

from app.database.mysql_configs import get_database
from app.sqlModels.gatewayEntities import (
    GatewayChangeRequest,
    ChangeRequestStatus,
    ChangeRequestType,
    Gateway,
    GatewayFileConfig,
    FileConfigType,
)
from app.pydanticModels.gatewayModels import (
    GatewayChangeRequestReview,
    GatewayChangeRequestResponse,
    GatewayChangeRequestListResponse,
    UnifiedGatewayResponse,
    UnifiedGatewayListResponse,
    UnifiedGatewayChangeRequestCreate,
    GatewayFileConfigResponse,
)
from app.config.gateways import get_gateways_info
from app.auth.dependencies import (
    require_active_user,
    require_user_role,
    require_admin_only,
)
from app.sqlModels.authEntities import User, UserRole


router = APIRouter(prefix='/api/v1/gateway-config', tags=['Gateway Configuration'])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _gateway_to_response(gateway: Gateway) -> UnifiedGatewayResponse:
    """Convert a Gateway model to UnifiedGatewayResponse."""
    external_config = gateway.get_external_config()
    internal_config = gateway.get_internal_config()

    def _config_to_response(config: GatewayFileConfig) -> GatewayFileConfigResponse:
        return GatewayFileConfigResponse(
            id=config.id,
            gateway_id=config.gateway_id,
            config_type=config.config_type,
            name=config.name,
            expected_filetypes=config.expected_filetypes or [],
            header_row_config=config.header_row_config or {},
            end_of_data_signal=config.end_of_data_signal,
            date_format=config.date_format,
            charge_keywords=config.charge_keywords or [],
            column_mapping=config.column_mapping,
            is_active=config.is_active,
        )

    return UnifiedGatewayResponse(
        id=gateway.id,
        display_name=gateway.display_name,
        description=gateway.description,
        country=gateway.country,
        currency_code=gateway.currency_code,
        is_active=gateway.is_active,
        external_config=_config_to_response(external_config) if external_config else None,
        internal_config=_config_to_response(internal_config) if internal_config else None,
        created_at=gateway.created_at,
        updated_at=gateway.updated_at,
    )


def _build_change_request_response(
    req: GatewayChangeRequest,
    db: Session,
) -> GatewayChangeRequestResponse:
    """Build a GatewayChangeRequestResponse from a change request."""
    stmt = select(User).where(User.id == req.requested_by_id)
    requested_by = db.execute(stmt).scalar_one_or_none()

    reviewed_by = None
    if req.reviewed_by_id:
        stmt = select(User).where(User.id == req.reviewed_by_id)
        reviewed_by = db.execute(stmt).scalar_one_or_none()

    return GatewayChangeRequestResponse(
        id=req.id,
        request_type=req.request_type,
        status=req.status,
        unified_gateway_id=req.unified_gateway_id,
        gateway_display_name=req.gateway_display_name,
        proposed_changes=req.proposed_changes,
        requested_by_id=req.requested_by_id,
        requested_by_name=f"{requested_by.first_name} {requested_by.last_name}" if requested_by else None,
        created_at=req.created_at,
        reviewed_by_id=req.reviewed_by_id,
        reviewed_by_name=f"{reviewed_by.first_name} {reviewed_by.last_name}" if reviewed_by else None,
        reviewed_at=req.reviewed_at,
        rejection_reason=req.rejection_reason,
    )


def _check_super_admin(current_user: User):
    """Block super_admin access to gateway management."""
    if current_user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Super admins do not have access to gateway management"
        )


# =============================================================================
# READ ENDPOINTS
# =============================================================================

@router.get("/", response_model=UnifiedGatewayListResponse)
async def list_gateways(
    include_inactive: bool = Query(False, description="Include inactive gateways"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """List all gateways with their external and internal configurations."""
    _check_super_admin(current_user)

    conditions = []
    if not include_inactive:
        conditions.append(Gateway.is_active == True)

    stmt = select(Gateway).options(selectinload(Gateway.file_configs))
    if conditions:
        stmt = stmt.where(*conditions)
    stmt = stmt.order_by(Gateway.display_name)

    gateways = db.execute(stmt).scalars().all()
    response_gateways = [_gateway_to_response(gw) for gw in gateways]

    return UnifiedGatewayListResponse(
        gateways=response_gateways,
        total_count=len(response_gateways)
    )


@router.get("/info")
async def get_gateway_info(
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """Get comprehensive gateway information for reconciliation."""
    _check_super_admin(current_user)
    return JSONResponse(content=get_gateways_info(db), status_code=200)


@router.get("/{gateway_id}", response_model=UnifiedGatewayResponse)
async def get_gateway(
    gateway_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """Get a specific gateway by ID."""
    _check_super_admin(current_user)

    stmt = select(Gateway).options(
        selectinload(Gateway.file_configs)
    ).where(Gateway.id == gateway_id)
    gateway = db.execute(stmt).scalar_one_or_none()

    if not gateway:
        raise HTTPException(status_code=404, detail=f"Gateway with ID {gateway_id} not found")

    return _gateway_to_response(gateway)


# =============================================================================
# CHANGE REQUEST ENDPOINTS (Users submit requests)
# =============================================================================

@router.post("/change-request", response_model=GatewayChangeRequestResponse, status_code=201)
async def create_change_request(
    request: UnifiedGatewayChangeRequestCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """
    Submit a gateway change request for approval.

    Only users with 'user' role can submit change requests.
    Change requests must be approved by an admin before taking effect.
    """
    display_name = request.display_name.strip()

    # Check for existing pending request for the same gateway display name
    stmt = select(GatewayChangeRequest).where(
        GatewayChangeRequest.gateway_display_name == display_name,
        GatewayChangeRequest.status == ChangeRequestStatus.PENDING.value
    )
    existing_pending = db.execute(stmt).scalar_one_or_none()

    if existing_pending:
        raise HTTPException(
            status_code=400,
            detail=f"A pending change request already exists for gateway '{display_name}'. Please wait for it to be reviewed."
        )

    gateway_id = None

    # Validate based on request type
    if request.request_type == ChangeRequestType.CREATE:
        # Check if gateway already exists
        stmt = select(Gateway).where(Gateway.display_name == display_name)
        existing = db.execute(stmt).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Gateway '{display_name}' already exists. Use 'update' request type instead."
            )

        # Validate required fields for creation
        proposed = request.proposed_changes
        if "external_config" not in proposed or "internal_config" not in proposed:
            raise HTTPException(
                status_code=400,
                detail="Both external_config and internal_config are required for create request"
            )

        # Validate external config
        ext_config = proposed.get("external_config", {})
        if not ext_config.get("name"):
            raise HTTPException(status_code=400, detail="external_config.name is required")
        if ext_config.get("name", "").startswith("workpay_"):
            raise HTTPException(status_code=400, detail="External config name cannot start with 'workpay_'")

        # Validate internal config
        int_config = proposed.get("internal_config", {})
        if not int_config.get("name"):
            raise HTTPException(status_code=400, detail="internal_config.name is required")
        if not int_config.get("name", "").startswith("workpay_"):
            raise HTTPException(status_code=400, detail="Internal config name must start with 'workpay_'")

        # Check for duplicate config names
        ext_name = ext_config.get("name", "").lower()
        int_name = int_config.get("name", "").lower()

        stmt = select(GatewayFileConfig).where(
            or_(
                GatewayFileConfig.name == ext_name,
                GatewayFileConfig.name == int_name
            )
        )
        existing_configs = db.execute(stmt).scalars().all()
        if existing_configs:
            existing_names = [c.name for c in existing_configs]
            raise HTTPException(
                status_code=400,
                detail=f"Config name(s) already exist: {', '.join(existing_names)}"
            )

    elif request.request_type in [ChangeRequestType.UPDATE, ChangeRequestType.DELETE, ChangeRequestType.ACTIVATE, ChangeRequestType.PERMANENT_DELETE]:
        # Check if gateway exists
        stmt = select(Gateway).where(Gateway.display_name == display_name)
        gateway = db.execute(stmt).scalar_one_or_none()

        if not gateway:
            raise HTTPException(status_code=404, detail=f"Gateway '{display_name}' not found")

        gateway_id = gateway.id

        if request.request_type == ChangeRequestType.DELETE and not gateway.is_active:
            raise HTTPException(status_code=400, detail=f"Gateway '{display_name}' is already inactive")

        if request.request_type == ChangeRequestType.ACTIVATE and gateway.is_active:
            raise HTTPException(status_code=400, detail=f"Gateway '{display_name}' is already active")

        if request.request_type == ChangeRequestType.PERMANENT_DELETE and gateway.is_active:
            raise HTTPException(status_code=400, detail=f"Gateway '{display_name}' must be deactivated before permanent deletion")

        # For UPDATE requests, check for duplicate display_name (excluding current gateway)
        if request.request_type == ChangeRequestType.UPDATE:
            new_display_name = request.proposed_changes.get("display_name", "").strip()
            if new_display_name and new_display_name != display_name:
                stmt = select(Gateway).where(
                    Gateway.display_name == new_display_name,
                    Gateway.id != gateway.id
                )
                existing_display = db.execute(stmt).scalar_one_or_none()
                if existing_display:
                    raise HTTPException(
                        status_code=400,
                        detail=f"A gateway with display name '{new_display_name}' already exists"
                    )

    # Create the change request
    change_request = GatewayChangeRequest(
        request_type=request.request_type.value,
        status=ChangeRequestStatus.PENDING.value,
        unified_gateway_id=gateway_id,
        gateway_display_name=display_name,
        proposed_changes=request.proposed_changes,
        requested_by_id=current_user.id,
    )

    db.add(change_request)
    db.commit()
    db.refresh(change_request)

    return _build_change_request_response(change_request, db)


@router.get("/change-requests/my", response_model=GatewayChangeRequestListResponse)
async def get_my_change_requests(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Get change requests submitted by the current user."""
    conditions = [GatewayChangeRequest.requested_by_id == current_user.id]

    if status:
        if status.lower() not in ["pending", "approved", "rejected"]:
            raise HTTPException(status_code=400, detail="Invalid status. Must be 'pending', 'approved', or 'rejected'")
        conditions.append(GatewayChangeRequest.status == status.lower())

    stmt = select(GatewayChangeRequest).where(*conditions).order_by(GatewayChangeRequest.created_at.desc())
    requests = db.execute(stmt).scalars().all()

    response_requests = [_build_change_request_response(req, db) for req in requests]

    return GatewayChangeRequestListResponse(
        count=len(response_requests),
        requests=response_requests
    )


# =============================================================================
# APPROVAL ENDPOINTS (Admins review requests)
# =============================================================================

@router.get("/change-requests/pending", response_model=GatewayChangeRequestListResponse)
async def get_pending_change_requests(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin_only)
):
    """Get all pending change requests awaiting approval."""
    base_stmt = select(GatewayChangeRequest).where(
        GatewayChangeRequest.status == ChangeRequestStatus.PENDING.value
    )

    total_count = db.execute(
        select(sa_func.count()).select_from(base_stmt.subquery())
    ).scalar() or 0
    total_pages = max(1, math.ceil(total_count / page_size))

    stmt = base_stmt.order_by(
        GatewayChangeRequest.created_at.asc()
    ).offset((page - 1) * page_size).limit(page_size)

    requests = db.execute(stmt).scalars().all()
    response_requests = [_build_change_request_response(req, db) for req in requests]

    return GatewayChangeRequestListResponse(
        count=total_count,
        requests=response_requests,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/change-requests/all", response_model=GatewayChangeRequestListResponse)
async def get_all_change_requests(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin_only)
):
    """Get all change requests (for audit/history)."""
    conditions = []

    if status:
        if status.lower() not in ["pending", "approved", "rejected"]:
            raise HTTPException(status_code=400, detail="Invalid status. Must be 'pending', 'approved', or 'rejected'")
        conditions.append(GatewayChangeRequest.status == status.lower())

    base_stmt = select(GatewayChangeRequest)
    if conditions:
        base_stmt = base_stmt.where(*conditions)

    total_count = db.execute(
        select(sa_func.count()).select_from(base_stmt.subquery())
    ).scalar() or 0
    total_pages = max(1, math.ceil(total_count / page_size))

    stmt = base_stmt.order_by(
        GatewayChangeRequest.created_at.desc()
    ).offset((page - 1) * page_size).limit(page_size)

    requests = db.execute(stmt).scalars().all()
    response_requests = [_build_change_request_response(req, db) for req in requests]

    return GatewayChangeRequestListResponse(
        count=total_count,
        requests=response_requests,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/change-requests/{request_id}", response_model=GatewayChangeRequestResponse)
async def get_change_request(
    request_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """Get a specific change request by ID."""
    _check_super_admin(current_user)

    stmt = select(GatewayChangeRequest).where(GatewayChangeRequest.id == request_id)
    change_request = db.execute(stmt).scalar_one_or_none()

    if not change_request:
        raise HTTPException(status_code=404, detail="Change request not found")

    # Users can only view their own requests
    if current_user.role == UserRole.USER.value and change_request.requested_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only view your own change requests")

    return _build_change_request_response(change_request, db)


@router.post("/change-requests/{request_id}/review", response_model=GatewayChangeRequestResponse)
async def review_change_request(
    request_id: int,
    review: GatewayChangeRequestReview,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin_only)
):
    """
    Approve or reject a change request.

    Only admins can approve/reject change requests.
    If approved, the gateway change is applied immediately.
    """
    stmt = select(GatewayChangeRequest).where(GatewayChangeRequest.id == request_id)
    change_request = db.execute(stmt).scalar_one_or_none()

    if not change_request:
        raise HTTPException(status_code=404, detail="Change request not found")

    if change_request.status != ChangeRequestStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Change request has already been {change_request.status}"
        )

    change_request.reviewed_by_id = current_user.id
    change_request.reviewed_at = datetime.now(ZoneInfo("Africa/Nairobi"))

    if review.approved:
        change_request.status = ChangeRequestStatus.APPROVED.value
        _apply_gateway_change(change_request, db, current_user.id)
    else:
        change_request.status = ChangeRequestStatus.REJECTED.value
        change_request.rejection_reason = review.rejection_reason

    db.commit()
    db.refresh(change_request)

    return _build_change_request_response(change_request, db)


# =============================================================================
# APPLY CHANGE (internal)
# =============================================================================

def _apply_gateway_change(change_request: GatewayChangeRequest, db: Session, user_id: int):
    """Apply an approved gateway change request."""
    proposed = change_request.proposed_changes

    if change_request.request_type == ChangeRequestType.CREATE.value:
        # Create new gateway
        new_gateway = Gateway(
            display_name=change_request.gateway_display_name,
            description=proposed.get("description"),
            country=proposed.get("country"),
            currency_code=proposed.get("currency_code"),
            is_active=True,
            created_by_id=user_id,
        )
        db.add(new_gateway)
        db.flush()

        # Create external config
        ext_config = proposed.get("external_config", {})
        external = GatewayFileConfig(
            gateway_id=new_gateway.id,
            config_type=FileConfigType.EXTERNAL.value,
            name=ext_config.get("name", "").lower(),
            expected_filetypes=ext_config.get("expected_filetypes", ["xlsx", "xls", "csv"]),
            header_row_config=ext_config.get("header_row_config", {"xlsx": 0, "xls": 0, "csv": 0}),
            end_of_data_signal=ext_config.get("end_of_data_signal"),
            date_format=ext_config.get("date_format"),
            charge_keywords=[kw.lower().strip() for kw in ext_config.get("charge_keywords", []) if kw.strip()],
            column_mapping=ext_config.get("column_mapping"),
            is_active=True,
        )
        db.add(external)

        # Create internal config
        int_config = proposed.get("internal_config", {})
        internal = GatewayFileConfig(
            gateway_id=new_gateway.id,
            config_type=FileConfigType.INTERNAL.value,
            name=int_config.get("name", "").lower(),
            expected_filetypes=int_config.get("expected_filetypes", ["xlsx", "xls", "csv"]),
            header_row_config=int_config.get("header_row_config", {"xlsx": 0, "xls": 0, "csv": 0}),
            end_of_data_signal=int_config.get("end_of_data_signal"),
            date_format=int_config.get("date_format"),
            charge_keywords=[kw.lower().strip() for kw in int_config.get("charge_keywords", []) if kw.strip()] or None,
            column_mapping=int_config.get("column_mapping"),
            is_active=True,
        )
        db.add(internal)
        db.flush()

        change_request.unified_gateway_id = new_gateway.id

    elif change_request.request_type == ChangeRequestType.UPDATE.value:
        stmt = select(Gateway).options(
            selectinload(Gateway.file_configs)
        ).where(Gateway.id == change_request.unified_gateway_id)
        gateway = db.execute(stmt).scalar_one_or_none()

        if gateway:
            if "display_name" in proposed:
                gateway.display_name = proposed["display_name"]
            if "description" in proposed:
                gateway.description = proposed["description"]
            if "country" in proposed:
                gateway.country = proposed["country"]
            if "currency_code" in proposed:
                gateway.currency_code = proposed["currency_code"]
            if "is_active" in proposed:
                gateway.is_active = proposed["is_active"]

            # Update external config
            if "external_config" in proposed:
                ext_config = gateway.get_external_config()
                if ext_config:
                    ext_updates = proposed["external_config"]
                    if "name" in ext_updates:
                        ext_config.name = ext_updates["name"].lower()
                    if "expected_filetypes" in ext_updates:
                        ext_config.expected_filetypes = ext_updates["expected_filetypes"]
                    if "header_row_config" in ext_updates:
                        ext_config.header_row_config = ext_updates["header_row_config"]
                    if "end_of_data_signal" in ext_updates:
                        ext_config.end_of_data_signal = ext_updates["end_of_data_signal"]
                    if "date_format" in ext_updates:
                        ext_config.date_format = ext_updates["date_format"]
                    if "charge_keywords" in ext_updates:
                        ext_config.charge_keywords = [
                            kw.lower().strip() for kw in ext_updates["charge_keywords"] if kw.strip()
                        ]
                    if "column_mapping" in ext_updates:
                        ext_config.column_mapping = ext_updates["column_mapping"]

            # Update internal config
            if "internal_config" in proposed:
                int_config = gateway.get_internal_config()
                if int_config:
                    int_updates = proposed["internal_config"]
                    if "name" in int_updates:
                        int_config.name = int_updates["name"].lower()
                    if "expected_filetypes" in int_updates:
                        int_config.expected_filetypes = int_updates["expected_filetypes"]
                    if "header_row_config" in int_updates:
                        int_config.header_row_config = int_updates["header_row_config"]
                    if "end_of_data_signal" in int_updates:
                        int_config.end_of_data_signal = int_updates["end_of_data_signal"]
                    if "date_format" in int_updates:
                        int_config.date_format = int_updates["date_format"]
                    if "charge_keywords" in int_updates:
                        int_config.charge_keywords = [
                            kw.lower().strip() for kw in int_updates["charge_keywords"] if kw.strip()
                        ]
                    if "column_mapping" in int_updates:
                        int_config.column_mapping = int_updates["column_mapping"]

    elif change_request.request_type == ChangeRequestType.DELETE.value:
        stmt = select(Gateway).options(
            selectinload(Gateway.file_configs)
        ).where(Gateway.id == change_request.unified_gateway_id)
        gateway = db.execute(stmt).scalar_one_or_none()

        if gateway:
            gateway.is_active = False
            for config in gateway.file_configs:
                config.is_active = False

    elif change_request.request_type == ChangeRequestType.ACTIVATE.value:
        stmt = select(Gateway).options(
            selectinload(Gateway.file_configs)
        ).where(Gateway.id == change_request.unified_gateway_id)
        gateway = db.execute(stmt).scalar_one_or_none()

        if gateway:
            gateway.is_active = True
            for config in gateway.file_configs:
                config.is_active = True

    elif change_request.request_type == ChangeRequestType.PERMANENT_DELETE.value:
        stmt = select(Gateway).options(
            selectinload(Gateway.file_configs)
        ).where(Gateway.id == change_request.unified_gateway_id)
        gateway = db.execute(stmt).scalar_one_or_none()

        if gateway:
            if gateway.is_active:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot permanently delete an active gateway. Deactivate it first."
                )

            db.execute(
                update(GatewayChangeRequest)
                .where(GatewayChangeRequest.unified_gateway_id == gateway.id)
                .values(unified_gateway_id=None)
            )

            db.delete(gateway)
            change_request.unified_gateway_id = None
