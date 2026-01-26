"""
Gateway Configuration Module.

This module provides gateway configuration with database persistence.
Gateways can be managed via API or by seeding defaults on startup.

Default gateways are provided as fallback when database is empty.
"""
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select


# ============================================================================
# DROPDOWN OPTIONS FOR GATEWAY CONFIGURATION
# ============================================================================
# These constants define the valid options for gateway configuration fields.
# ============================================================================

SUPPORTED_COUNTRIES: List[Dict[str, str]] = [
    {"code": "KE", "name": "Kenya"},
    {"code": "UG", "name": "Uganda"},
    {"code": "TZ", "name": "Tanzania"},
    {"code": "RW", "name": "Rwanda"},
    {"code": "NG", "name": "Nigeria"},
    {"code": "GH", "name": "Ghana"},
    {"code": "ZA", "name": "South Africa"},
]

SUPPORTED_CURRENCIES: List[Dict[str, str]] = [
    {"code": "KES", "name": "Kenyan Shilling"},
    {"code": "USD", "name": "US Dollar"},
    {"code": "UGX", "name": "Ugandan Shilling"},
    {"code": "TZS", "name": "Tanzanian Shilling"},
    {"code": "RWF", "name": "Rwandan Franc"},
    {"code": "NGN", "name": "Nigerian Naira"},
    {"code": "GHS", "name": "Ghanaian Cedi"},
    {"code": "ZAR", "name": "South African Rand"},
]

SUPPORTED_DATE_FORMATS: List[Dict[str, str]] = [
    {"format": "YYYY-MM-DD", "example": "2024-01-15"},
    {"format": "DD/MM/YYYY", "example": "15/01/2024"},
    {"format": "MM/DD/YYYY", "example": "01/15/2024"},
    {"format": "DD-MM-YYYY", "example": "15-01-2024"},
]


def get_valid_country_codes() -> List[str]:
    """Get list of valid country codes."""
    return [c["code"] for c in SUPPORTED_COUNTRIES]


def get_valid_currency_codes() -> List[str]:
    """Get list of valid currency codes."""
    return [c["code"] for c in SUPPORTED_CURRENCIES]


def get_valid_date_formats() -> List[str]:
    """Get list of valid date formats."""
    return [f["format"] for f in SUPPORTED_DATE_FORMATS]


# ============================================================================
# DEFAULT GATEWAY CONFIGURATION
# ============================================================================
# These defaults are used when the database is empty or as fallback.
# Use the API endpoints to add/update gateways dynamically.
# Note: charge_keywords are stored in lowercase for case-insensitive matching.
# ============================================================================

DEFAULT_GATEWAYS: Dict[str, Dict[str, Any]] = {
    # External Gateways (Bank Statements)
    "equity": {
        "type": "external",
        "display_name": "Equity Bank",
        "country": "KE",
        "currency": "KES",
        "date_format": "YYYY-MM-DD",
        "charge_keywords": ["charge", "fee", "commission", "levy"],
    },
    "kcb": {
        "type": "external",
        "display_name": "KCB Bank",
        "country": "KE",
        "currency": "KES",
        "date_format": "YYYY-MM-DD",
        "charge_keywords": ["charge", "fee", "commission"],
    },
    "mpesa": {
        "type": "external",
        "display_name": "M-Pesa",
        "country": "KE",
        "currency": "KES",
        "date_format": "YYYY-MM-DD",
        "charge_keywords": ["charge", "fee", "transaction cost"],
    },

    # Internal Gateways (Workpay per external gateway)
    "workpay_equity": {
        "type": "internal",
        "display_name": "Workpay (Equity)",
        "country": "KE",
        "currency": "KES",
        "date_format": "YYYY-MM-DD",
        "charge_keywords": [],
    },
    "workpay_kcb": {
        "type": "internal",
        "display_name": "Workpay (KCB)",
        "country": "KE",
        "currency": "KES",
        "date_format": "YYYY-MM-DD",
        "charge_keywords": [],
    },
    "workpay_mpesa": {
        "type": "internal",
        "display_name": "Workpay (M-Pesa)",
        "country": "KE",
        "currency": "KES",
        "date_format": "YYYY-MM-DD",
        "charge_keywords": [],
    },
}


# ============================================================================
# DATABASE GATEWAY FUNCTIONS
# ============================================================================

def get_gateways_from_db(db_session: Session) -> Dict[str, Dict[str, Any]]:
    """
    Load active gateway configurations from database.

    Args:
        db_session: Database session.

    Returns:
        Dictionary of gateway configurations.
    """
    from app.sqlModels.gatewayEntities import GatewayConfig

    stmt = select(GatewayConfig).where(GatewayConfig.is_active == True)
    configs = db_session.execute(stmt).scalars().all()

    gateways = {}
    for config in configs:
        gateways[config.name] = config.to_dict()

    return gateways


def get_gateway_from_db(db_session: Session, gateway_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific gateway configuration from database.

    Args:
        db_session: Database session.
        gateway_name: Gateway name to look up.

    Returns:
        Gateway configuration dict or None if not found.
    """
    from app.sqlModels.gatewayEntities import GatewayConfig

    stmt = select(GatewayConfig).where(
        GatewayConfig.name == gateway_name.lower(),
        GatewayConfig.is_active == True
    )
    config = db_session.execute(stmt).scalar_one_or_none()

    if config:
        return config.to_dict()
    return None


def seed_default_gateways(db_session: Session) -> int:
    """
    Seed default gateways into database if they don't exist.

    Also handles migration from legacy 'workpay' gateway to per-external
    internal gateways (workpay_equity, workpay_kcb, workpay_mpesa).

    Args:
        db_session: Database session.

    Returns:
        Number of gateways seeded.
    """
    from app.sqlModels.gatewayEntities import GatewayConfig

    seeded = 0

    # Deactivate legacy 'workpay' gateway if it exists
    stmt = select(GatewayConfig).where(
        GatewayConfig.name == "workpay",
        GatewayConfig.is_active == True
    )
    legacy_workpay = db_session.execute(stmt).scalar_one_or_none()
    if legacy_workpay:
        legacy_workpay.is_active = False

    for name, config in DEFAULT_GATEWAYS.items():
        # Check if gateway already exists
        stmt = select(GatewayConfig).where(GatewayConfig.name == name)
        existing = db_session.execute(stmt).scalar_one_or_none()

        if not existing:
            new_gateway = GatewayConfig(
                name=name,
                gateway_type=config["type"],
                display_name=config["display_name"],
                country=config.get("country", "KE"),
                currency=config.get("currency", "KES"),
                date_format=config.get("date_format", "YYYY-MM-DD"),
                charge_keywords=config.get("charge_keywords", []),
                is_active=True,
            )
            db_session.add(new_gateway)
            seeded += 1

    if seeded > 0 or legacy_workpay:
        db_session.commit()

    return seeded


# ============================================================================
# HELPER FUNCTIONS (Database-aware)
# ============================================================================

def get_all_gateways(db_session: Optional[Session] = None) -> Dict[str, Dict[str, Any]]:
    """
    Get all gateway configurations.

    Args:
        db_session: Optional database session. If provided, loads from DB.
                   If None, returns defaults.

    Returns:
        Dictionary of gateway configurations.
    """
    if db_session:
        gateways = get_gateways_from_db(db_session)
        if gateways:
            return gateways
    return DEFAULT_GATEWAYS.copy()


def get_external_gateways(db_session: Optional[Session] = None) -> List[str]:
    """Get list of external (bank) gateway names."""
    gateways = get_all_gateways(db_session)
    return [name for name, config in gateways.items() if config["type"] == "external"]


def get_internal_gateways(db_session: Optional[Session] = None) -> List[str]:
    """
    Get list of internal gateway names.

    Returns the internal gateway names exactly as stored in the database.
    The database stores combined names like 'workpay_equity', 'workpay_mpesa'.
    """
    gateways = get_all_gateways(db_session)
    return [name for name, config in gateways.items() if config["type"] == "internal"]


def get_all_upload_gateways(db_session: Optional[Session] = None) -> List[str]:
    """
    Get all valid gateway names for file uploads.

    Returns external gateways (equity, mpesa, etc.) and internal gateways
    (workpay_equity, workpay_mpesa, etc.) directly from the database.

    The database is the single source of truth - no gateway name generation.
    """
    return get_external_gateways(db_session) + get_internal_gateways(db_session)


def get_charge_keywords(gateway: str, db_session: Optional[Session] = None) -> List[str]:
    """Get charge keywords for a gateway."""
    gateways = get_all_gateways(db_session)
    gateway_lower = gateway.lower()
    if gateway_lower in gateways:
        return gateways[gateway_lower].get("charge_keywords", [])
    return []


def get_gateway_display_name(gateway: str, db_session: Optional[Session] = None) -> str:
    """Get display name for a gateway."""
    gateways = get_all_gateways(db_session)
    gateway_lower = gateway.lower()
    if gateway_lower in gateways:
        return gateways[gateway_lower].get("display_name", gateway.capitalize())
    return gateway.capitalize()


def is_valid_external_gateway(gateway: str, db_session: Optional[Session] = None) -> bool:
    """Check if gateway is a valid external gateway."""
    return gateway.lower() in get_external_gateways(db_session)


def is_valid_internal_gateway(gateway: str, db_session: Optional[Session] = None) -> bool:
    """Check if gateway is a valid internal gateway."""
    return gateway.lower() in get_internal_gateways(db_session)


def is_valid_upload_gateway(gateway: str, db_session: Optional[Session] = None) -> bool:
    """Check if gateway is valid for file uploads."""
    return gateway.lower() in get_all_upload_gateways(db_session)


def get_gateway_config(gateway: str, db_session: Optional[Session] = None) -> Dict[str, Any]:
    """Get full configuration for a gateway."""
    gateways = get_all_gateways(db_session)
    return gateways.get(gateway.lower(), {})


def get_gateways_info(db_session: Optional[Session] = None) -> Dict[str, Any]:
    """
    Get comprehensive gateway information for API responses.

    Returns a structured dictionary with all gateway information.
    The database is the single source of truth for all gateway names.
    """
    external = get_external_gateways(db_session)
    internal = get_internal_gateways(db_session)

    return {
        "external_gateways": external,
        "internal_gateways": internal,
        "upload_gateways": {
            "external": external,
            "internal": internal,
        },
        "charge_keywords": {
            gw: get_charge_keywords(gw, db_session) for gw in external
        },
        "usage": {
            "external_files": f"Use gateway names: {', '.join(external)}",
            "internal_files": f"Use gateway names: {', '.join(internal)}",
        },
    }


def get_gateway_options() -> Dict[str, Any]:
    """
    Get dropdown options for gateway configuration forms.

    Returns lists of valid countries, currencies, and date formats.
    """
    return {
        "countries": SUPPORTED_COUNTRIES,
        "currencies": SUPPORTED_CURRENCIES,
        "date_formats": SUPPORTED_DATE_FORMATS,
    }