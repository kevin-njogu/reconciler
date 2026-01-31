"""
Gateway Configuration API Endpoints.

Provides CRUD operations for managing payment gateway configurations with
maker-checker approval workflow:
- Users (role=user) can submit change requests
- Admins (role=admin) can approve/reject change requests
- Super admins have no access to gateway management
"""
from typing import List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, or_
from starlette.responses import JSONResponse

from app.database.mysql_configs import get_database
from app.sqlModels.gatewayEntities import (
    GatewayConfig,
    GatewayChangeRequest,
    ChangeRequestStatus,
    ChangeRequestType,
    Gateway,
    GatewayFileConfig,
    FileConfigType,
)
from app.pydanticModels.gatewayModels import (
    GatewayCreateRequest,
    GatewayUpdateRequest,
    GatewayResponse,
    GatewayType,
    GatewayChangeRequestCreate,
    GatewayChangeRequestReview,
    GatewayChangeRequestResponse,
    GatewayChangeRequestListResponse,
    GatewayOptionsResponse,
    # Unified gateway models
    UnifiedGatewayCreate,
    UnifiedGatewayUpdate,
    UnifiedGatewayResponse,
    UnifiedGatewayListResponse,
    UnifiedGatewayChangeRequestCreate,
    GatewayFileConfigResponse,
    FileConfigType as PydanticFileConfigType,
)
from app.config.gateways import (
    get_gateways_info,
    seed_default_gateways,
    get_gateway_options,
    get_valid_country_codes,
    get_valid_currency_codes,
    get_valid_date_formats,
)
from app.auth.dependencies import (
    require_active_user,
    require_user_role,
    require_admin_only,
)
from app.sqlModels.authEntities import User


router = APIRouter(prefix='/api/v1/gateway-config', tags=['Gateway Configuration'])


# =============================================================================
# READ ENDPOINTS (Accessible to users and admins)
# =============================================================================

@router.get("/options", response_model=GatewayOptionsResponse)
async def get_options():
    """
    Get dropdown options for gateway configuration forms.

    Returns lists of valid countries, currencies, and date formats.
    This endpoint is public (no authentication required) to support form population.
    """
    return get_gateway_options()


@router.get("/", response_model=List[GatewayResponse])
async def list_gateways(
    gateway_type: str = Query(None, description="Filter by type: 'external' or 'internal'"),
    include_inactive: bool = Query(False, description="Include inactive gateways"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    List all gateway configurations.

    Accessible to users and admins.
    """
    # Block super_admin access
    from app.sqlModels.authEntities import UserRole
    if current_user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Super admins do not have access to gateway management"
        )

    conditions = []

    if not include_inactive:
        conditions.append(GatewayConfig.is_active == True)

    if gateway_type:
        if gateway_type.lower() not in ["external", "internal"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid gateway_type. Must be 'external' or 'internal'"
            )
        conditions.append(GatewayConfig.gateway_type == gateway_type.lower())

    stmt = select(GatewayConfig)
    if conditions:
        stmt = stmt.where(*conditions)
    stmt = stmt.order_by(GatewayConfig.gateway_type, GatewayConfig.name)

    gateways = db.execute(stmt).scalars().all()
    return gateways


@router.get("/info")
async def get_gateway_info(
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get comprehensive gateway information for reconciliation.

    Returns gateway names, upload conventions, and charge keywords.
    Accessible to users and admins.
    """
    # Block super_admin access
    from app.sqlModels.authEntities import UserRole
    if current_user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Super admins do not have access to gateway management"
        )

    return JSONResponse(content=get_gateways_info(db), status_code=200)


@router.get("/{gateway_name}", response_model=GatewayResponse)
async def get_gateway(
    gateway_name: str,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get a specific gateway configuration.

    Accessible to users and admins.
    """
    # Block super_admin access
    from app.sqlModels.authEntities import UserRole
    if current_user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Super admins do not have access to gateway management"
        )

    stmt = select(GatewayConfig).where(GatewayConfig.name == gateway_name.lower())
    gateway = db.execute(stmt).scalar_one_or_none()

    if not gateway:
        raise HTTPException(status_code=404, detail=f"Gateway '{gateway_name}' not found")

    return gateway


@router.get("/upload-names/{gateway_name}")
async def get_upload_names(
    gateway_name: str,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get the upload gateway names for a specific external gateway.

    Accessible to users and admins.
    """
    # Block super_admin access
    from app.sqlModels.authEntities import UserRole
    if current_user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Super admins do not have access to gateway management"
        )

    # Verify gateway exists and is external
    stmt = select(GatewayConfig).where(
        GatewayConfig.name == gateway_name.lower(),
        GatewayConfig.is_active == True
    )
    gateway = db.execute(stmt).scalar_one_or_none()

    if not gateway:
        raise HTTPException(status_code=404, detail=f"Gateway '{gateway_name}' not found")

    if gateway.gateway_type != "external":
        raise HTTPException(
            status_code=400,
            detail=f"Gateway '{gateway_name}' is not an external gateway"
        )

    # Get matching internal gateways (those ending with _{external_gateway})
    # The database stores full internal gateway names like 'workpay_equity', 'workpay_mpesa'
    gateway_lower = gateway_name.lower()
    stmt = select(GatewayConfig).where(
        GatewayConfig.gateway_type == "internal",
        GatewayConfig.is_active == True
    )
    internals = db.execute(stmt).scalars().all()

    # Filter internal gateways that match this external gateway
    internal_gateways = [
        internal.name for internal in internals
        if internal.name.endswith(f"_{gateway_lower}")
    ]

    return JSONResponse(
        content={
            "gateway": gateway_lower,
            "external_upload_name": gateway_lower,
            "internal_upload_names": internal_gateways,
            "usage": {
                "external_file": f"Upload with gateway_name={gateway_lower}",
                "internal_file": f"Upload with gateway_name={internal_gateways[0] if internal_gateways else 'No matching internal gateway found'}",
            }
        },
        status_code=200
    )


# =============================================================================
# CHANGE REQUEST ENDPOINTS (Users submit requests)
# =============================================================================

@router.post("/change-request", response_model=GatewayChangeRequestResponse, status_code=201)
async def create_change_request(
    request: GatewayChangeRequestCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """
    Submit a gateway change request for approval.

    Only users with 'user' role can submit change requests.
    Change requests must be approved by an admin before taking effect.

    Request types:
    - create: Create a new gateway
    - update: Update an existing gateway
    - delete: Deactivate a gateway
    - activate: Reactivate a deactivated gateway
    """
    gateway_name = request.gateway_name.lower()

    # Check for existing pending request for the same gateway
    stmt = select(GatewayChangeRequest).where(
        GatewayChangeRequest.gateway_name == gateway_name,
        GatewayChangeRequest.status == ChangeRequestStatus.PENDING.value
    )
    existing_pending = db.execute(stmt).scalar_one_or_none()

    if existing_pending:
        raise HTTPException(
            status_code=400,
            detail=f"A pending change request already exists for gateway '{gateway_name}'. Please wait for it to be reviewed."
        )

    # Validate based on request type
    if request.request_type == ChangeRequestType.CREATE:
        # Check if gateway already exists
        stmt = select(GatewayConfig).where(GatewayConfig.name == gateway_name)
        existing = db.execute(stmt).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Gateway '{gateway_name}' already exists. Use 'update' request type instead."
            )

        # Validate required fields for creation
        required_fields = ["gateway_type", "display_name", "country", "currency"]
        for field in required_fields:
            if field not in request.proposed_changes:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field '{field}' in proposed_changes for create request"
                )

        # Validate gateway_type
        gateway_type = request.proposed_changes.get("gateway_type")
        if gateway_type not in ["external", "internal"]:
            raise HTTPException(
                status_code=400,
                detail="gateway_type must be 'external' or 'internal'"
            )

        # Validate country code
        country = request.proposed_changes.get("country", "").upper()
        if country not in get_valid_country_codes():
            raise HTTPException(
                status_code=400,
                detail=f"Invalid country code. Must be one of: {', '.join(get_valid_country_codes())}"
            )

        # Validate currency code
        currency = request.proposed_changes.get("currency", "").upper()
        if currency not in get_valid_currency_codes():
            raise HTTPException(
                status_code=400,
                detail=f"Invalid currency code. Must be one of: {', '.join(get_valid_currency_codes())}"
            )

        # Validate date_format if provided
        date_format = request.proposed_changes.get("date_format")
        if date_format and date_format not in get_valid_date_formats():
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format. Must be one of: {', '.join(get_valid_date_formats())}"
            )

        # Check for duplicate display_name
        display_name = request.proposed_changes.get("display_name", "").strip()
        if display_name:
            stmt = select(GatewayConfig).where(
                GatewayConfig.display_name == display_name
            )
            existing_display = db.execute(stmt).scalar_one_or_none()
            if existing_display:
                raise HTTPException(
                    status_code=400,
                    detail=f"A gateway with display name '{display_name}' already exists"
                )

    elif request.request_type in [ChangeRequestType.UPDATE, ChangeRequestType.DELETE, ChangeRequestType.ACTIVATE, ChangeRequestType.PERMANENT_DELETE]:
        # Check if gateway exists
        stmt = select(GatewayConfig).where(GatewayConfig.name == gateway_name)
        gateway = db.execute(stmt).scalar_one_or_none()

        if not gateway:
            raise HTTPException(
                status_code=404,
                detail=f"Gateway '{gateway_name}' not found"
            )

        if request.request_type == ChangeRequestType.DELETE and not gateway.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Gateway '{gateway_name}' is already inactive"
            )

        if request.request_type == ChangeRequestType.ACTIVATE and gateway.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Gateway '{gateway_name}' is already active"
            )

        if request.request_type == ChangeRequestType.PERMANENT_DELETE and gateway.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Gateway '{gateway_name}' must be deactivated before permanent deletion"
            )

        # For UPDATE requests, check for duplicate display_name (excluding current gateway)
        if request.request_type == ChangeRequestType.UPDATE:
            display_name = request.proposed_changes.get("display_name", "").strip()
            if display_name:
                stmt = select(GatewayConfig).where(
                    GatewayConfig.display_name == display_name,
                    GatewayConfig.id != gateway.id
                )
                existing_display = db.execute(stmt).scalar_one_or_none()
                if existing_display:
                    raise HTTPException(
                        status_code=400,
                        detail=f"A gateway with display name '{display_name}' already exists"
                    )

    # Create the change request
    change_request = GatewayChangeRequest(
        request_type=request.request_type.value,
        status=ChangeRequestStatus.PENDING.value,
        gateway_name=gateway_name,
        proposed_changes=request.proposed_changes,
        requested_by_id=current_user.id,
    )

    # Link to existing gateway if applicable
    if request.request_type != ChangeRequestType.CREATE:
        stmt = select(GatewayConfig).where(GatewayConfig.name == gateway_name)
        gateway = db.execute(stmt).scalar_one_or_none()
        if gateway:
            change_request.gateway_id = gateway.id

    db.add(change_request)
    db.commit()
    db.refresh(change_request)

    # Build response with user name
    response = GatewayChangeRequestResponse(
        id=change_request.id,
        request_type=change_request.request_type,
        status=change_request.status,
        gateway_id=change_request.gateway_id,
        gateway_name=change_request.gateway_name,
        proposed_changes=change_request.proposed_changes,
        requested_by_id=change_request.requested_by_id,
        requested_by_name=f"{current_user.first_name} {current_user.last_name}",
        created_at=change_request.created_at,
        reviewed_by_id=change_request.reviewed_by_id,
        reviewed_at=change_request.reviewed_at,
        rejection_reason=change_request.rejection_reason,
    )

    return response


@router.get("/change-requests/my", response_model=GatewayChangeRequestListResponse)
async def get_my_change_requests(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """
    Get change requests submitted by the current user.

    Only users with 'user' role can view their own requests.
    Returns both legacy and unified gateway change requests.
    """
    conditions = [GatewayChangeRequest.requested_by_id == current_user.id]

    if status:
        if status.lower() not in ["pending", "approved", "rejected"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid status. Must be 'pending', 'approved', or 'rejected'"
            )
        conditions.append(GatewayChangeRequest.status == status.lower())

    stmt = select(GatewayChangeRequest).where(*conditions).order_by(GatewayChangeRequest.created_at.desc())
    requests = db.execute(stmt).scalars().all()

    # Build response with user names
    response_requests = []
    for req in requests:
        # Get requested_by user
        stmt = select(User).where(User.id == req.requested_by_id)
        requested_by = db.execute(stmt).scalar_one_or_none()

        # Get reviewed_by user if applicable
        reviewed_by = None
        if req.reviewed_by_id:
            stmt = select(User).where(User.id == req.reviewed_by_id)
            reviewed_by = db.execute(stmt).scalar_one_or_none()

        # Detect if this is a unified gateway request
        is_unified = req.gateway_display_name is not None

        response_requests.append(GatewayChangeRequestResponse(
            id=req.id,
            request_type=req.request_type,
            status=req.status,
            gateway_id=req.unified_gateway_id if is_unified else req.gateway_id,
            gateway_name=req.gateway_display_name if is_unified else req.gateway_name,
            proposed_changes=req.proposed_changes,
            requested_by_id=req.requested_by_id,
            requested_by_name=f"{requested_by.first_name} {requested_by.last_name}" if requested_by else None,
            created_at=req.created_at,
            reviewed_by_id=req.reviewed_by_id,
            reviewed_by_name=f"{reviewed_by.first_name} {reviewed_by.last_name}" if reviewed_by else None,
            reviewed_at=req.reviewed_at,
            rejection_reason=req.rejection_reason,
        ))

    return GatewayChangeRequestListResponse(
        count=len(response_requests),
        requests=response_requests
    )


# =============================================================================
# APPROVAL ENDPOINTS (Admins review requests)
# =============================================================================

@router.get("/change-requests/pending", response_model=GatewayChangeRequestListResponse)
async def get_pending_change_requests(
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin_only)
):
    """
    Get all pending change requests awaiting approval.

    Only admins (not super_admins) can view and approve change requests.
    Returns both legacy and unified gateway change requests.
    """
    stmt = select(GatewayChangeRequest).where(
        GatewayChangeRequest.status == ChangeRequestStatus.PENDING.value
    ).order_by(GatewayChangeRequest.created_at.asc())

    requests = db.execute(stmt).scalars().all()

    # Build response with user names
    response_requests = []
    for req in requests:
        # Get requested_by user
        stmt = select(User).where(User.id == req.requested_by_id)
        requested_by = db.execute(stmt).scalar_one_or_none()

        # Detect if this is a unified gateway request
        is_unified = req.gateway_display_name is not None

        response_requests.append(GatewayChangeRequestResponse(
            id=req.id,
            request_type=req.request_type,
            status=req.status,
            gateway_id=req.unified_gateway_id if is_unified else req.gateway_id,
            gateway_name=req.gateway_display_name if is_unified else req.gateway_name,
            proposed_changes=req.proposed_changes,
            requested_by_id=req.requested_by_id,
            requested_by_name=f"{requested_by.first_name} {requested_by.last_name}" if requested_by else None,
            created_at=req.created_at,
            reviewed_by_id=req.reviewed_by_id,
            reviewed_at=req.reviewed_at,
            rejection_reason=req.rejection_reason,
        ))

    return GatewayChangeRequestListResponse(
        count=len(response_requests),
        requests=response_requests
    )


@router.get("/change-requests/all", response_model=GatewayChangeRequestListResponse)
async def get_all_change_requests(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin_only)
):
    """
    Get all change requests (for audit/history).

    Only admins can view all change requests.
    Returns both legacy and unified gateway change requests.
    """
    conditions = []

    if status:
        if status.lower() not in ["pending", "approved", "rejected"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid status. Must be 'pending', 'approved', or 'rejected'"
            )
        conditions.append(GatewayChangeRequest.status == status.lower())

    stmt = select(GatewayChangeRequest)
    if conditions:
        stmt = stmt.where(*conditions)
    stmt = stmt.order_by(GatewayChangeRequest.created_at.desc())

    requests = db.execute(stmt).scalars().all()

    # Build response with user names
    response_requests = []
    for req in requests:
        # Get requested_by user
        stmt = select(User).where(User.id == req.requested_by_id)
        requested_by = db.execute(stmt).scalar_one_or_none()

        # Get reviewed_by user if applicable
        reviewed_by = None
        if req.reviewed_by_id:
            stmt = select(User).where(User.id == req.reviewed_by_id)
            reviewed_by = db.execute(stmt).scalar_one_or_none()

        # Detect if this is a unified gateway request
        is_unified = req.gateway_display_name is not None

        response_requests.append(GatewayChangeRequestResponse(
            id=req.id,
            request_type=req.request_type,
            status=req.status,
            gateway_id=req.unified_gateway_id if is_unified else req.gateway_id,
            gateway_name=req.gateway_display_name if is_unified else req.gateway_name,
            proposed_changes=req.proposed_changes,
            requested_by_id=req.requested_by_id,
            requested_by_name=f"{requested_by.first_name} {requested_by.last_name}" if requested_by else None,
            created_at=req.created_at,
            reviewed_by_id=req.reviewed_by_id,
            reviewed_by_name=f"{reviewed_by.first_name} {reviewed_by.last_name}" if reviewed_by else None,
            reviewed_at=req.reviewed_at,
            rejection_reason=req.rejection_reason,
        ))

    return GatewayChangeRequestListResponse(
        count=len(response_requests),
        requests=response_requests
    )


@router.get("/change-requests/{request_id}", response_model=GatewayChangeRequestResponse)
async def get_change_request(
    request_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get a specific change request by ID.

    Users can only view their own requests.
    Admins can view all requests.
    Handles both legacy and unified gateway change requests.
    """
    from app.sqlModels.authEntities import UserRole

    # Block super_admin access
    if current_user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Super admins do not have access to gateway management"
        )

    stmt = select(GatewayChangeRequest).where(GatewayChangeRequest.id == request_id)
    change_request = db.execute(stmt).scalar_one_or_none()

    if not change_request:
        raise HTTPException(status_code=404, detail="Change request not found")

    # Users can only view their own requests
    if current_user.role == UserRole.USER.value and change_request.requested_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only view your own change requests")

    # Get requested_by user
    stmt = select(User).where(User.id == change_request.requested_by_id)
    requested_by = db.execute(stmt).scalar_one_or_none()

    # Get reviewed_by user if applicable
    reviewed_by = None
    if change_request.reviewed_by_id:
        stmt = select(User).where(User.id == change_request.reviewed_by_id)
        reviewed_by = db.execute(stmt).scalar_one_or_none()

    # Detect if this is a unified gateway request
    is_unified = change_request.gateway_display_name is not None

    return GatewayChangeRequestResponse(
        id=change_request.id,
        request_type=change_request.request_type,
        status=change_request.status,
        gateway_id=change_request.unified_gateway_id if is_unified else change_request.gateway_id,
        gateway_name=change_request.gateway_display_name if is_unified else change_request.gateway_name,
        proposed_changes=change_request.proposed_changes,
        requested_by_id=change_request.requested_by_id,
        requested_by_name=f"{requested_by.first_name} {requested_by.last_name}" if requested_by else None,
        created_at=change_request.created_at,
        reviewed_by_id=change_request.reviewed_by_id,
        reviewed_by_name=f"{reviewed_by.first_name} {reviewed_by.last_name}" if reviewed_by else None,
        reviewed_at=change_request.reviewed_at,
        rejection_reason=change_request.rejection_reason,
    )


@router.post("/change-requests/{request_id}/review", response_model=GatewayChangeRequestResponse)
async def review_change_request(
    request_id: int,
    review: GatewayChangeRequestReview,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin_only)
):
    """
    Approve or reject a change request.

    Only admins (not super_admins) can approve/reject change requests.
    If approved, the gateway change is applied immediately.

    Note: This endpoint handles both legacy and unified gateway change requests.
    It automatically detects the request type based on whether gateway_display_name
    is set (unified) or not (legacy).
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

    # Detect if this is a unified gateway request
    is_unified_request = change_request.gateway_display_name is not None

    # Update the change request
    change_request.reviewed_by_id = current_user.id
    change_request.reviewed_at = datetime.now(ZoneInfo("Africa/Nairobi"))

    if review.approved:
        change_request.status = ChangeRequestStatus.APPROVED.value

        # Apply the change using the appropriate function
        if is_unified_request:
            _apply_unified_gateway_change(change_request, db, current_user.id)
        else:
            _apply_gateway_change(change_request, db)
    else:
        change_request.status = ChangeRequestStatus.REJECTED.value
        change_request.rejection_reason = review.rejection_reason

    db.commit()
    db.refresh(change_request)

    # Get requested_by user
    stmt = select(User).where(User.id == change_request.requested_by_id)
    requested_by = db.execute(stmt).scalar_one_or_none()

    return GatewayChangeRequestResponse(
        id=change_request.id,
        request_type=change_request.request_type,
        status=change_request.status,
        gateway_id=change_request.gateway_id if not is_unified_request else change_request.unified_gateway_id,
        gateway_name=change_request.gateway_name if not is_unified_request else change_request.gateway_display_name,
        proposed_changes=change_request.proposed_changes,
        requested_by_id=change_request.requested_by_id,
        requested_by_name=f"{requested_by.first_name} {requested_by.last_name}" if requested_by else None,
        created_at=change_request.created_at,
        reviewed_by_id=change_request.reviewed_by_id,
        reviewed_by_name=f"{current_user.first_name} {current_user.last_name}",
        reviewed_at=change_request.reviewed_at,
        rejection_reason=change_request.rejection_reason,
    )


def _apply_gateway_change(change_request: GatewayChangeRequest, db: Session):
    """
    Apply an approved gateway change request.

    This is called internally when a change request is approved.
    """
    if change_request.request_type == ChangeRequestType.CREATE.value:
        # Create new gateway
        proposed = change_request.proposed_changes

        # Normalize charge_keywords to lowercase
        charge_keywords = proposed.get("charge_keywords", [])
        if charge_keywords:
            charge_keywords = [kw.lower().strip() for kw in charge_keywords if kw.strip()]

        new_gateway = GatewayConfig(
            name=change_request.gateway_name,
            gateway_type=proposed["gateway_type"],
            display_name=proposed["display_name"],
            country=proposed["country"].upper(),
            currency=proposed["currency"].upper(),
            date_format=proposed.get("date_format", "YYYY-MM-DD"),
            charge_keywords=charge_keywords,
            is_active=True,
        )
        db.add(new_gateway)
        db.flush()

        # Update change request with new gateway ID
        change_request.gateway_id = new_gateway.id

    elif change_request.request_type == ChangeRequestType.UPDATE.value:
        # Update existing gateway
        stmt = select(GatewayConfig).where(GatewayConfig.id == change_request.gateway_id)
        gateway = db.execute(stmt).scalar_one_or_none()

        if gateway:
            proposed = change_request.proposed_changes
            if "display_name" in proposed:
                gateway.display_name = proposed["display_name"]
            if "country" in proposed:
                gateway.country = proposed["country"].upper()
            if "currency" in proposed:
                gateway.currency = proposed["currency"].upper()
            if "date_format" in proposed:
                gateway.date_format = proposed["date_format"]
            if "charge_keywords" in proposed:
                # Normalize to lowercase
                keywords = proposed["charge_keywords"]
                if keywords:
                    keywords = [kw.lower().strip() for kw in keywords if kw.strip()]
                gateway.charge_keywords = keywords
            if "is_active" in proposed:
                gateway.is_active = proposed["is_active"]

    elif change_request.request_type == ChangeRequestType.DELETE.value:
        # Deactivate gateway (soft delete)
        stmt = select(GatewayConfig).where(GatewayConfig.id == change_request.gateway_id)
        gateway = db.execute(stmt).scalar_one_or_none()

        if gateway:
            gateway.is_active = False

    elif change_request.request_type == ChangeRequestType.ACTIVATE.value:
        # Reactivate gateway
        stmt = select(GatewayConfig).where(GatewayConfig.id == change_request.gateway_id)
        gateway = db.execute(stmt).scalar_one_or_none()

        if gateway:
            gateway.is_active = True

    elif change_request.request_type == ChangeRequestType.PERMANENT_DELETE.value:
        # Permanently delete gateway from database
        stmt = select(GatewayConfig).where(GatewayConfig.id == change_request.gateway_id)
        gateway = db.execute(stmt).scalar_one_or_none()

        if gateway:
            # Only allow permanent deletion of inactive gateways
            if gateway.is_active:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot permanently delete an active gateway. Deactivate it first."
                )

            # Clear all gateway_id references in change requests before deletion
            # This preserves the change request history while allowing gateway deletion
            from sqlalchemy import update
            db.execute(
                update(GatewayChangeRequest)
                .where(GatewayChangeRequest.gateway_id == gateway.id)
                .values(gateway_id=None)
            )

            db.delete(gateway)
            # Clear the gateway_id reference on current request as well
            change_request.gateway_id = None


# =============================================================================
# ADMIN-ONLY UTILITY ENDPOINTS
# =============================================================================

@router.post("/seed-defaults")
async def seed_defaults(
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin_only)
):
    """
    Seed default gateway configurations into the database.

    This creates the default gateways (equity, kcb, mpesa, workpay) if they don't exist.
    Useful for initial setup or resetting to defaults.

    Only admins can seed defaults.
    """
    seeded = seed_default_gateways(db)
    return JSONResponse(
        content={
            "message": f"Seeded {seeded} default gateways",
            "seeded_count": seeded
        },
        status_code=200
    )


# =============================================================================
# UNIFIED GATEWAY CRUD ENDPOINTS (New)
# =============================================================================

def _gateway_to_response(gateway: Gateway) -> UnifiedGatewayResponse:
    """Convert a Gateway model to UnifiedGatewayResponse."""
    external_config = gateway.get_external_config()
    internal_config = gateway.get_internal_config()

    return UnifiedGatewayResponse(
        id=gateway.id,
        display_name=gateway.display_name,
        description=gateway.description,
        country={
            "id": gateway.country.id,
            "code": gateway.country.code,
            "name": gateway.country.name,
        } if gateway.country else None,
        currency={
            "id": gateway.currency.id,
            "code": gateway.currency.code,
            "name": gateway.currency.name,
            "symbol": gateway.currency.symbol,
        } if gateway.currency else None,
        is_active=gateway.is_active,
        external_config=GatewayFileConfigResponse(
            id=external_config.id,
            gateway_id=external_config.gateway_id,
            config_type=external_config.config_type,
            name=external_config.name,
            filename_prefix=external_config.filename_prefix,
            expected_filetypes=external_config.expected_filetypes or [],
            header_row_config=external_config.header_row_config or {},
            end_of_data_signal=external_config.end_of_data_signal,
            date_format={
                "id": external_config.date_format.id,
                "format_string": external_config.date_format.format_string,
                "example": external_config.date_format.example,
            } if external_config.date_format else None,
            charge_keywords=external_config.charge_keywords or [],
            column_mapping=external_config.column_mapping,
            is_active=external_config.is_active,
        ) if external_config else None,
        internal_config=GatewayFileConfigResponse(
            id=internal_config.id,
            gateway_id=internal_config.gateway_id,
            config_type=internal_config.config_type,
            name=internal_config.name,
            filename_prefix=internal_config.filename_prefix,
            expected_filetypes=internal_config.expected_filetypes or [],
            header_row_config=internal_config.header_row_config or {},
            end_of_data_signal=internal_config.end_of_data_signal,
            date_format={
                "id": internal_config.date_format.id,
                "format_string": internal_config.date_format.format_string,
                "example": internal_config.date_format.example,
            } if internal_config.date_format else None,
            charge_keywords=internal_config.charge_keywords or [],
            column_mapping=internal_config.column_mapping,
            is_active=internal_config.is_active,
        ) if internal_config else None,
        created_at=gateway.created_at,
        updated_at=gateway.updated_at,
    )


@router.get("/unified/list", response_model=UnifiedGatewayListResponse)
async def list_unified_gateways(
    include_inactive: bool = Query(False, description="Include inactive gateways"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    List all unified gateways with their external and internal configurations.

    Accessible to users and admins.
    """
    from app.sqlModels.authEntities import UserRole
    if current_user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Super admins do not have access to gateway management"
        )

    conditions = []
    if not include_inactive:
        conditions.append(Gateway.is_active == True)

    stmt = select(Gateway).options(
        selectinload(Gateway.file_configs),
        selectinload(Gateway.country),
        selectinload(Gateway.currency),
    )
    if conditions:
        stmt = stmt.where(*conditions)
    stmt = stmt.order_by(Gateway.display_name)

    gateways = db.execute(stmt).scalars().all()

    response_gateways = [_gateway_to_response(gw) for gw in gateways]

    return UnifiedGatewayListResponse(
        gateways=response_gateways,
        total_count=len(response_gateways)
    )


@router.get("/unified/{gateway_id}", response_model=UnifiedGatewayResponse)
async def get_unified_gateway(
    gateway_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get a specific unified gateway by ID.

    Accessible to users and admins.
    """
    from app.sqlModels.authEntities import UserRole
    if current_user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Super admins do not have access to gateway management"
        )

    stmt = select(Gateway).options(
        selectinload(Gateway.file_configs),
        selectinload(Gateway.country),
        selectinload(Gateway.currency),
    ).where(Gateway.id == gateway_id)
    gateway = db.execute(stmt).scalar_one_or_none()

    if not gateway:
        raise HTTPException(status_code=404, detail=f"Gateway with ID {gateway_id} not found")

    return _gateway_to_response(gateway)


@router.post("/unified/change-request", status_code=201)
async def create_unified_change_request(
    request: UnifiedGatewayChangeRequestCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """
    Submit a unified gateway change request for approval.

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
            raise HTTPException(
                status_code=400,
                detail="external_config.name is required"
            )
        if ext_config.get("name", "").startswith("workpay_"):
            raise HTTPException(
                status_code=400,
                detail="External config name cannot start with 'workpay_'"
            )

        # Validate internal config
        int_config = proposed.get("internal_config", {})
        if not int_config.get("name"):
            raise HTTPException(
                status_code=400,
                detail="internal_config.name is required"
            )
        if not int_config.get("name", "").startswith("workpay_"):
            raise HTTPException(
                status_code=400,
                detail="Internal config name must start with 'workpay_'"
            )

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
            raise HTTPException(
                status_code=404,
                detail=f"Gateway '{display_name}' not found"
            )

        gateway_id = gateway.id

        if request.request_type == ChangeRequestType.DELETE and not gateway.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Gateway '{display_name}' is already inactive"
            )

        if request.request_type == ChangeRequestType.ACTIVATE and gateway.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Gateway '{display_name}' is already active"
            )

        if request.request_type == ChangeRequestType.PERMANENT_DELETE and gateway.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Gateway '{display_name}' must be deactivated before permanent deletion"
            )

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
        gateway_name=display_name.lower().replace(" ", "_"),  # Legacy field
        proposed_changes=request.proposed_changes,
        requested_by_id=current_user.id,
    )

    db.add(change_request)
    db.commit()
    db.refresh(change_request)

    return {
        "id": change_request.id,
        "request_type": change_request.request_type,
        "status": change_request.status,
        "gateway_id": change_request.unified_gateway_id,
        "display_name": change_request.gateway_display_name,
        "proposed_changes": change_request.proposed_changes,
        "requested_by_id": change_request.requested_by_id,
        "requested_by_name": f"{current_user.first_name} {current_user.last_name}",
        "created_at": change_request.created_at.isoformat() if change_request.created_at else None,
    }


@router.get("/unified/change-requests/pending")
async def get_pending_unified_change_requests(
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin_only)
):
    """
    Get all pending unified gateway change requests awaiting approval.

    Only admins can view and approve change requests.
    """
    stmt = select(GatewayChangeRequest).where(
        GatewayChangeRequest.status == ChangeRequestStatus.PENDING.value,
        GatewayChangeRequest.gateway_display_name.isnot(None)  # Only unified requests
    ).order_by(GatewayChangeRequest.created_at.asc())

    requests = db.execute(stmt).scalars().all()

    response_requests = []
    for req in requests:
        stmt = select(User).where(User.id == req.requested_by_id)
        requested_by = db.execute(stmt).scalar_one_or_none()

        response_requests.append({
            "id": req.id,
            "request_type": req.request_type,
            "status": req.status,
            "gateway_id": req.unified_gateway_id,
            "display_name": req.gateway_display_name,
            "proposed_changes": req.proposed_changes,
            "requested_by_id": req.requested_by_id,
            "requested_by_name": f"{requested_by.first_name} {requested_by.last_name}" if requested_by else None,
            "created_at": req.created_at.isoformat() if req.created_at else None,
        })

    return {
        "count": len(response_requests),
        "requests": response_requests
    }


@router.post("/unified/change-requests/{request_id}/review")
async def review_unified_change_request(
    request_id: int,
    review: GatewayChangeRequestReview,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_admin_only)
):
    """
    Approve or reject a unified gateway change request.

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

    # Update the change request
    change_request.reviewed_by_id = current_user.id
    change_request.reviewed_at = datetime.now(ZoneInfo("Africa/Nairobi"))

    if review.approved:
        change_request.status = ChangeRequestStatus.APPROVED.value
        _apply_unified_gateway_change(change_request, db, current_user.id)
    else:
        change_request.status = ChangeRequestStatus.REJECTED.value
        change_request.rejection_reason = review.rejection_reason

    db.commit()
    db.refresh(change_request)

    # Get requested_by user
    stmt = select(User).where(User.id == change_request.requested_by_id)
    requested_by = db.execute(stmt).scalar_one_or_none()

    return {
        "id": change_request.id,
        "request_type": change_request.request_type,
        "status": change_request.status,
        "gateway_id": change_request.unified_gateway_id,
        "display_name": change_request.gateway_display_name,
        "proposed_changes": change_request.proposed_changes,
        "requested_by_id": change_request.requested_by_id,
        "requested_by_name": f"{requested_by.first_name} {requested_by.last_name}" if requested_by else None,
        "created_at": change_request.created_at.isoformat() if change_request.created_at else None,
        "reviewed_by_id": change_request.reviewed_by_id,
        "reviewed_by_name": f"{current_user.first_name} {current_user.last_name}",
        "reviewed_at": change_request.reviewed_at.isoformat() if change_request.reviewed_at else None,
        "rejection_reason": change_request.rejection_reason,
    }


def _apply_unified_gateway_change(change_request: GatewayChangeRequest, db: Session, user_id: int):
    """
    Apply an approved unified gateway change request.
    """
    proposed = change_request.proposed_changes

    if change_request.request_type == ChangeRequestType.CREATE.value:
        # Create new gateway
        new_gateway = Gateway(
            display_name=change_request.gateway_display_name,
            description=proposed.get("description"),
            country_id=proposed.get("country_id"),
            currency_id=proposed.get("currency_id"),
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
            filename_prefix=ext_config.get("filename_prefix"),
            expected_filetypes=ext_config.get("expected_filetypes", ["xlsx", "xls", "csv"]),
            header_row_config=ext_config.get("header_row_config", {"xlsx": 0, "xls": 0, "csv": 0}),
            end_of_data_signal=ext_config.get("end_of_data_signal"),
            date_format_id=ext_config.get("date_format_id"),
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
            filename_prefix=int_config.get("filename_prefix"),
            expected_filetypes=int_config.get("expected_filetypes", ["xlsx", "xls", "csv"]),
            header_row_config=int_config.get("header_row_config", {"xlsx": 0, "xls": 0, "csv": 0}),
            end_of_data_signal=int_config.get("end_of_data_signal"),
            date_format_id=int_config.get("date_format_id"),
            charge_keywords=None,  # Internal configs don't have charge keywords
            column_mapping=int_config.get("column_mapping"),
            is_active=True,
        )
        db.add(internal)
        db.flush()

        # Update change request with new gateway ID
        change_request.unified_gateway_id = new_gateway.id

    elif change_request.request_type == ChangeRequestType.UPDATE.value:
        # Update existing gateway
        stmt = select(Gateway).options(
            selectinload(Gateway.file_configs)
        ).where(Gateway.id == change_request.unified_gateway_id)
        gateway = db.execute(stmt).scalar_one_or_none()

        if gateway:
            if "display_name" in proposed:
                gateway.display_name = proposed["display_name"]
            if "description" in proposed:
                gateway.description = proposed["description"]
            if "country_id" in proposed:
                gateway.country_id = proposed["country_id"]
            if "currency_id" in proposed:
                gateway.currency_id = proposed["currency_id"]
            if "is_active" in proposed:
                gateway.is_active = proposed["is_active"]

            # Update external config
            if "external_config" in proposed:
                ext_config = gateway.get_external_config()
                if ext_config:
                    ext_updates = proposed["external_config"]
                    if "name" in ext_updates:
                        ext_config.name = ext_updates["name"].lower()
                    if "filename_prefix" in ext_updates:
                        ext_config.filename_prefix = ext_updates["filename_prefix"]
                    if "expected_filetypes" in ext_updates:
                        ext_config.expected_filetypes = ext_updates["expected_filetypes"]
                    if "header_row_config" in ext_updates:
                        ext_config.header_row_config = ext_updates["header_row_config"]
                    if "end_of_data_signal" in ext_updates:
                        ext_config.end_of_data_signal = ext_updates["end_of_data_signal"]
                    if "date_format_id" in ext_updates:
                        ext_config.date_format_id = ext_updates["date_format_id"]
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
                    if "filename_prefix" in int_updates:
                        int_config.filename_prefix = int_updates["filename_prefix"]
                    if "expected_filetypes" in int_updates:
                        int_config.expected_filetypes = int_updates["expected_filetypes"]
                    if "header_row_config" in int_updates:
                        int_config.header_row_config = int_updates["header_row_config"]
                    if "end_of_data_signal" in int_updates:
                        int_config.end_of_data_signal = int_updates["end_of_data_signal"]
                    if "date_format_id" in int_updates:
                        int_config.date_format_id = int_updates["date_format_id"]
                    if "column_mapping" in int_updates:
                        int_config.column_mapping = int_updates["column_mapping"]

    elif change_request.request_type == ChangeRequestType.DELETE.value:
        # Deactivate gateway (soft delete)
        stmt = select(Gateway).options(
            selectinload(Gateway.file_configs)
        ).where(Gateway.id == change_request.unified_gateway_id)
        gateway = db.execute(stmt).scalar_one_or_none()

        if gateway:
            gateway.is_active = False
            # Also deactivate file configs
            for config in gateway.file_configs:
                config.is_active = False

    elif change_request.request_type == ChangeRequestType.ACTIVATE.value:
        # Reactivate gateway
        stmt = select(Gateway).options(
            selectinload(Gateway.file_configs)
        ).where(Gateway.id == change_request.unified_gateway_id)
        gateway = db.execute(stmt).scalar_one_or_none()

        if gateway:
            gateway.is_active = True
            # Also reactivate file configs
            for config in gateway.file_configs:
                config.is_active = True

    elif change_request.request_type == ChangeRequestType.PERMANENT_DELETE.value:
        # Permanently delete gateway
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

            # Clear unified_gateway_id references in change requests
            from sqlalchemy import update
            db.execute(
                update(GatewayChangeRequest)
                .where(GatewayChangeRequest.unified_gateway_id == gateway.id)
                .values(unified_gateway_id=None)
            )

            db.delete(gateway)
            change_request.unified_gateway_id = None
