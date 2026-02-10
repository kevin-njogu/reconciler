"""
Gateway Configuration Module.

Provides helper functions for querying unified gateway tables.
All gateway data lives in the `gateways` and `gateway_file_configs` tables.
"""
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

logger = logging.getLogger("app.config.gateways")


# ============================================================================
# HELPER FUNCTIONS (query unified gateway tables)
# ============================================================================

def get_all_upload_gateways(db_session: Optional[Session] = None) -> List[str]:
    """
    Get all valid gateway names for file uploads.

    Queries the unified gateway_file_configs table for active config names.
    """
    if not db_session:
        return []

    from app.sqlModels.gatewayEntities import GatewayFileConfig, Gateway

    stmt = (
        select(GatewayFileConfig.name)
        .join(Gateway, GatewayFileConfig.gateway_id == Gateway.id)
        .where(GatewayFileConfig.is_active == True, Gateway.is_active == True)
    )
    return list(db_session.execute(stmt).scalars().all())


def get_charge_keywords(gateway: str, db_session: Optional[Session] = None) -> List[str]:
    """
    Get charge keywords for a gateway from its file config.

    Args:
        gateway: Gateway config name (e.g., 'equity')
        db_session: Database session

    Returns:
        List of charge keywords for the gateway
    """
    if not db_session:
        return []

    gateway_lower = gateway.lower()

    try:
        from app.sqlModels.gatewayEntities import GatewayFileConfig

        stmt = select(GatewayFileConfig.charge_keywords).where(
            GatewayFileConfig.name == gateway_lower,
            GatewayFileConfig.is_active == True
        )
        keywords = db_session.execute(stmt).scalar_one_or_none()

        if keywords:
            logger.debug(f"Found charge keywords for {gateway}: {keywords}")
            return keywords

    except Exception as e:
        logger.warning(f"Error fetching charge keywords for {gateway}: {e}")

    logger.debug(f"No charge keywords found for gateway {gateway}")
    return []


def get_gateway_display_name(gateway: str, db_session: Optional[Session] = None) -> str:
    """
    Get display name for a gateway via its file config → gateway relationship.

    Args:
        gateway: File config name (e.g., 'equity' or 'workpay_equity')
        db_session: Database session

    Returns:
        Display name or capitalized gateway name as fallback
    """
    if not db_session:
        return gateway.capitalize()

    try:
        from app.sqlModels.gatewayEntities import GatewayFileConfig, Gateway

        stmt = (
            select(Gateway.display_name)
            .join(GatewayFileConfig, GatewayFileConfig.gateway_id == Gateway.id)
            .where(GatewayFileConfig.name == gateway.lower())
        )
        display_name = db_session.execute(stmt).scalar_one_or_none()
        if display_name:
            return display_name

    except Exception as e:
        logger.warning(f"Error fetching display name for {gateway}: {e}")

    return gateway.capitalize()


def is_valid_upload_gateway(gateway: str, db_session: Optional[Session] = None) -> bool:
    """Check if gateway is valid for file uploads."""
    return gateway.lower() in get_all_upload_gateways(db_session)


def get_external_gateways(db_session: Optional[Session] = None) -> List[str]:
    """Get list of active external gateway config names."""
    if not db_session:
        return []

    from app.sqlModels.gatewayEntities import GatewayFileConfig, Gateway, FileConfigType

    stmt = (
        select(GatewayFileConfig.name)
        .join(Gateway, GatewayFileConfig.gateway_id == Gateway.id)
        .where(
            GatewayFileConfig.config_type == FileConfigType.EXTERNAL.value,
            GatewayFileConfig.is_active == True,
            Gateway.is_active == True,
        )
    )
    return list(db_session.execute(stmt).scalars().all())


def get_internal_gateways(db_session: Optional[Session] = None) -> List[str]:
    """Get list of active internal gateway config names."""
    if not db_session:
        return []

    from app.sqlModels.gatewayEntities import GatewayFileConfig, Gateway, FileConfigType

    stmt = (
        select(GatewayFileConfig.name)
        .join(Gateway, GatewayFileConfig.gateway_id == Gateway.id)
        .where(
            GatewayFileConfig.config_type == FileConfigType.INTERNAL.value,
            GatewayFileConfig.is_active == True,
            Gateway.is_active == True,
        )
    )
    return list(db_session.execute(stmt).scalars().all())


def is_valid_external_gateway(gateway: str, db_session: Optional[Session] = None) -> bool:
    """Check if gateway is a valid active external gateway."""
    return gateway.lower() in get_external_gateways(db_session)


def is_valid_internal_gateway(gateway: str, db_session: Optional[Session] = None) -> bool:
    """Check if gateway is a valid active internal gateway."""
    return gateway.lower() in get_internal_gateways(db_session)


def get_gateway_from_db(db_session: Optional[Session] = None, gateway_name: str = "") -> Optional[Dict[str, Any]]:
    """
    Get a gateway file config as a dict (for backward compatibility).

    Returns config dict with name, charge_keywords, etc. or None.
    """
    if not db_session or not gateway_name:
        return None

    from app.sqlModels.gatewayEntities import GatewayFileConfig

    config = db_session.query(GatewayFileConfig).filter(
        GatewayFileConfig.name == gateway_name.lower(),
        GatewayFileConfig.is_active == True,
    ).first()

    if not config:
        return None

    return {
        "name": config.name,
        "config_type": config.config_type,
        "charge_keywords": config.charge_keywords or [],
        "expected_filetypes": config.expected_filetypes or [],
        "header_row_config": config.header_row_config or {},
        "date_format": config.date_format,
        "column_mapping": config.column_mapping,
        "end_of_data_signal": config.end_of_data_signal,
    }


def get_gateway_config(gateway: str, db_session: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """Alias for get_gateway_from_db for backward compatibility."""
    return get_gateway_from_db(db_session, gateway)


def get_gateways_info(db_session: Optional[Session] = None) -> Dict[str, Any]:
    """
    Get comprehensive gateway information for API responses.

    Builds from unified gateway tables.
    """
    if not db_session:
        return {
            "external_gateways": [],
            "internal_gateways": [],
            "upload_gateways": {"external": [], "internal": []},
            "charge_keywords": {},
        }

    from app.sqlModels.gatewayEntities import GatewayFileConfig, Gateway, FileConfigType

    # Get external configs
    ext_stmt = (
        select(GatewayFileConfig.name)
        .join(Gateway, GatewayFileConfig.gateway_id == Gateway.id)
        .where(
            GatewayFileConfig.config_type == FileConfigType.EXTERNAL.value,
            GatewayFileConfig.is_active == True,
            Gateway.is_active == True,
        )
    )
    external = list(db_session.execute(ext_stmt).scalars().all())

    # Get internal configs
    int_stmt = (
        select(GatewayFileConfig.name)
        .join(Gateway, GatewayFileConfig.gateway_id == Gateway.id)
        .where(
            GatewayFileConfig.config_type == FileConfigType.INTERNAL.value,
            GatewayFileConfig.is_active == True,
            Gateway.is_active == True,
        )
    )
    internal = list(db_session.execute(int_stmt).scalars().all())

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
    }
