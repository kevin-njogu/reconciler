"""
Settings Controller.

API endpoints for managing system-wide configuration settings:
- Date formats for file parsing
- Countries and currencies
- Reconciliation keywords (charges, reversals)
- System settings
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from starlette.responses import JSONResponse

from app.database.mysql_configs import get_database
from app.auth.dependencies import require_active_user, require_user_role
from app.sqlModels.authEntities import User
from app.sqlModels.settingsEntities import (
    DateFormat,
    Country,
    Currency,
    ReconciliationKeyword,
    SystemSetting,
    KeywordType,
)
from app.pydanticModels.settingsModels import (
    DateFormatCreate,
    DateFormatUpdate,
    DateFormatResponse,
    CountryCreate,
    CountryUpdate,
    CountryResponse,
    CurrencyCreate,
    CurrencyUpdate,
    CurrencyResponse,
    KeywordCreate,
    KeywordUpdate,
    KeywordResponse,
    KeywordBulkCreate,
    SystemSettingCreate,
    SystemSettingUpdate,
    SystemSettingResponse,
    AllSettingsResponse,
)

logger = logging.getLogger("app.settings")

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])


# =============================================================================
# GET ALL SETTINGS (combined view)
# =============================================================================

@router.get("", response_model=AllSettingsResponse)
async def get_all_settings(
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """
    Get all system settings in a single response.

    Returns date formats, countries with currencies, keywords grouped by type,
    and system settings.
    """
    # Date formats
    date_formats = db.query(DateFormat).filter(DateFormat.is_active == True).all()

    # Countries with currencies
    countries = db.query(Country).filter(Country.is_active == True).all()

    # Keywords grouped by type
    keywords = db.query(ReconciliationKeyword).filter(
        ReconciliationKeyword.is_active == True
    ).all()

    keywords_grouped = {
        "charge": [],
        "reversal": [],
    }
    for kw in keywords:
        if kw.keyword_type in keywords_grouped:
            keywords_grouped[kw.keyword_type].append(KeywordResponse.model_validate(kw.to_dict()))

    # System settings
    system_settings = db.query(SystemSetting).all()

    return AllSettingsResponse(
        date_formats=[DateFormatResponse.model_validate(df) for df in date_formats],
        countries=[CountryResponse.model_validate(c) for c in countries],
        keywords=keywords_grouped,
        system_settings=[SystemSettingResponse.model_validate(s) for s in system_settings],
    )


# =============================================================================
# DATE FORMAT ENDPOINTS
# =============================================================================

@router.get("/date-formats", response_model=List[DateFormatResponse])
async def list_date_formats(
    include_inactive: bool = Query(default=False, description="Include inactive formats"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """List all date formats."""
    query = db.query(DateFormat)
    if not include_inactive:
        query = query.filter(DateFormat.is_active == True)
    formats = query.order_by(DateFormat.is_default.desc(), DateFormat.display_name).all()
    return [DateFormatResponse.model_validate(f) for f in formats]


@router.post("/date-formats", response_model=DateFormatResponse, status_code=201)
async def create_date_format(
    data: DateFormatCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Create a new date format. User role only."""
    # Check for duplicate
    existing = db.query(DateFormat).filter(
        DateFormat.format_string == data.format_string
    ).first()
    if existing:
        raise HTTPException(400, f"Date format '{data.format_string}' already exists")

    # If setting as default, unset other defaults
    if data.is_default:
        db.query(DateFormat).filter(DateFormat.is_default == True).update(
            {"is_default": False}
        )

    date_format = DateFormat(
        format_string=data.format_string,
        display_name=data.display_name,
        example=data.example,
        is_default=data.is_default,
        created_by_id=current_user.id,
    )
    db.add(date_format)
    db.commit()
    db.refresh(date_format)

    logger.info(f"Date format created: {data.format_string}", extra={"user_id": current_user.id})
    return DateFormatResponse.model_validate(date_format)


@router.put("/date-formats/{format_id}", response_model=DateFormatResponse)
async def update_date_format(
    format_id: int,
    data: DateFormatUpdate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Update a date format. User role only."""
    date_format = db.query(DateFormat).filter(DateFormat.id == format_id).first()
    if not date_format:
        raise HTTPException(404, "Date format not found")

    # If setting as default, unset other defaults
    if data.is_default:
        db.query(DateFormat).filter(
            DateFormat.is_default == True,
            DateFormat.id != format_id
        ).update({"is_default": False})

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(date_format, key, value)

    db.commit()
    db.refresh(date_format)

    logger.info(f"Date format updated: {format_id}", extra={"user_id": current_user.id})
    return DateFormatResponse.model_validate(date_format)


@router.delete("/date-formats/{format_id}")
async def delete_date_format(
    format_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Delete (deactivate) a date format. User role only."""
    date_format = db.query(DateFormat).filter(DateFormat.id == format_id).first()
    if not date_format:
        raise HTTPException(404, "Date format not found")

    if date_format.is_default:
        raise HTTPException(400, "Cannot delete the default date format")

    date_format.is_active = False
    db.commit()

    logger.info(f"Date format deleted: {format_id}", extra={"user_id": current_user.id})
    return {"message": "Date format deleted successfully"}


# =============================================================================
# COUNTRY ENDPOINTS
# =============================================================================

@router.get("/countries", response_model=List[CountryResponse])
async def list_countries(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """List all countries with their currencies."""
    query = db.query(Country)
    if not include_inactive:
        query = query.filter(Country.is_active == True)
    countries = query.order_by(Country.name).all()
    return [CountryResponse.model_validate(c) for c in countries]


@router.post("/countries", response_model=CountryResponse, status_code=201)
async def create_country(
    data: CountryCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Create a new country with optional currencies. User role only."""
    # Check for duplicate
    existing = db.query(Country).filter(Country.code == data.code).first()
    if existing:
        raise HTTPException(400, f"Country with code '{data.code}' already exists")

    country = Country(
        code=data.code,
        name=data.name,
        created_by_id=current_user.id,
    )
    db.add(country)
    db.flush()  # Get the ID

    # Add currencies if provided
    if data.currencies:
        for curr_data in data.currencies:
            currency = Currency(
                code=curr_data.code,
                name=curr_data.name,
                symbol=curr_data.symbol,
                country_id=country.id,
                is_default=curr_data.is_default,
            )
            db.add(currency)

    db.commit()
    db.refresh(country)

    logger.info(f"Country created: {data.code}", extra={"user_id": current_user.id})
    return CountryResponse.model_validate(country)


@router.put("/countries/{country_id}", response_model=CountryResponse)
async def update_country(
    country_id: int,
    data: CountryUpdate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Update a country. User role only."""
    country = db.query(Country).filter(Country.id == country_id).first()
    if not country:
        raise HTTPException(404, "Country not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(country, key, value)

    db.commit()
    db.refresh(country)

    logger.info(f"Country updated: {country_id}", extra={"user_id": current_user.id})
    return CountryResponse.model_validate(country)


@router.delete("/countries/{country_id}")
async def delete_country(
    country_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Delete (deactivate) a country. User role only."""
    country = db.query(Country).filter(Country.id == country_id).first()
    if not country:
        raise HTTPException(404, "Country not found")

    country.is_active = False
    db.commit()

    logger.info(f"Country deleted: {country_id}", extra={"user_id": current_user.id})
    return {"message": "Country deleted successfully"}


# =============================================================================
# CURRENCY ENDPOINTS
# =============================================================================

@router.post("/countries/{country_id}/currencies", response_model=CurrencyResponse, status_code=201)
async def add_currency_to_country(
    country_id: int,
    data: CurrencyCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Add a currency to a country. User role only."""
    country = db.query(Country).filter(Country.id == country_id).first()
    if not country:
        raise HTTPException(404, "Country not found")

    # Check for duplicate currency in this country
    existing = db.query(Currency).filter(
        Currency.country_id == country_id,
        Currency.code == data.code
    ).first()
    if existing:
        raise HTTPException(400, f"Currency '{data.code}' already exists for this country")

    # If setting as default, unset other defaults for this country
    if data.is_default:
        db.query(Currency).filter(
            Currency.country_id == country_id,
            Currency.is_default == True
        ).update({"is_default": False})

    currency = Currency(
        code=data.code,
        name=data.name,
        symbol=data.symbol,
        country_id=country_id,
        is_default=data.is_default,
    )
    db.add(currency)
    db.commit()
    db.refresh(currency)

    logger.info(f"Currency added: {data.code} to country {country_id}", extra={"user_id": current_user.id})
    return CurrencyResponse.model_validate(currency)


@router.put("/currencies/{currency_id}", response_model=CurrencyResponse)
async def update_currency(
    currency_id: int,
    data: CurrencyUpdate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Update a currency. User role only."""
    currency = db.query(Currency).filter(Currency.id == currency_id).first()
    if not currency:
        raise HTTPException(404, "Currency not found")

    # If setting as default, unset other defaults for this country
    if data.is_default:
        db.query(Currency).filter(
            Currency.country_id == currency.country_id,
            Currency.is_default == True,
            Currency.id != currency_id
        ).update({"is_default": False})

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(currency, key, value)

    db.commit()
    db.refresh(currency)

    logger.info(f"Currency updated: {currency_id}", extra={"user_id": current_user.id})
    return CurrencyResponse.model_validate(currency)


@router.delete("/currencies/{currency_id}")
async def delete_currency(
    currency_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Delete a currency. User role only."""
    currency = db.query(Currency).filter(Currency.id == currency_id).first()
    if not currency:
        raise HTTPException(404, "Currency not found")

    db.delete(currency)
    db.commit()

    logger.info(f"Currency deleted: {currency_id}", extra={"user_id": current_user.id})
    return {"message": "Currency deleted successfully"}


# =============================================================================
# RECONCILIATION KEYWORD ENDPOINTS
# =============================================================================

@router.get("/keywords", response_model=List[KeywordResponse])
async def list_keywords(
    keyword_type: Optional[str] = Query(None, description="Filter by type: charge, reversal"),
    gateway_id: Optional[int] = Query(None, description="Filter by gateway"),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """List reconciliation keywords with optional filtering."""
    query = db.query(ReconciliationKeyword)

    if not include_inactive:
        query = query.filter(ReconciliationKeyword.is_active == True)
    if keyword_type:
        query = query.filter(ReconciliationKeyword.keyword_type == keyword_type)
    if gateway_id is not None:
        query = query.filter(ReconciliationKeyword.gateway_id == gateway_id)

    keywords = query.order_by(
        ReconciliationKeyword.keyword_type,
        ReconciliationKeyword.keyword
    ).all()

    return [KeywordResponse.model_validate(kw.to_dict()) for kw in keywords]


@router.get("/keywords/grouped")
async def list_keywords_grouped(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """List keywords grouped by type."""
    query = db.query(ReconciliationKeyword)
    if not include_inactive:
        query = query.filter(ReconciliationKeyword.is_active == True)

    keywords = query.order_by(ReconciliationKeyword.keyword).all()

    grouped = {
        "charge": [],
        "reversal": [],
    }
    for kw in keywords:
        if kw.keyword_type in grouped:
            grouped[kw.keyword_type].append(KeywordResponse.model_validate(kw.to_dict()))

    return JSONResponse(content=grouped)


@router.post("/keywords", response_model=KeywordResponse, status_code=201)
async def create_keyword(
    data: KeywordCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Create a new reconciliation keyword. User role only."""
    # Check for duplicate
    existing = db.query(ReconciliationKeyword).filter(
        ReconciliationKeyword.keyword == data.keyword,
        ReconciliationKeyword.keyword_type == data.keyword_type.value,
        ReconciliationKeyword.gateway_id == data.gateway_id,
    ).first()
    if existing:
        raise HTTPException(400, f"Keyword '{data.keyword}' already exists for this type")

    keyword = ReconciliationKeyword(
        keyword=data.keyword,
        keyword_type=data.keyword_type.value,
        description=data.description,
        is_case_sensitive=data.is_case_sensitive,
        gateway_id=data.gateway_id,
        created_by_id=current_user.id,
    )
    db.add(keyword)
    db.commit()
    db.refresh(keyword)

    logger.info(f"Keyword created: {data.keyword} ({data.keyword_type})", extra={"user_id": current_user.id})
    return KeywordResponse.model_validate(keyword.to_dict())


@router.post("/keywords/bulk", status_code=201)
async def create_keywords_bulk(
    data: KeywordBulkCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Bulk create keywords of the same type. User role only."""
    created = []
    skipped = []

    for kw in data.keywords:
        kw_clean = kw.strip()
        if not kw_clean:
            continue

        # Check for duplicate
        existing = db.query(ReconciliationKeyword).filter(
            ReconciliationKeyword.keyword == kw_clean,
            ReconciliationKeyword.keyword_type == data.keyword_type.value,
            ReconciliationKeyword.gateway_id == data.gateway_id,
        ).first()

        if existing:
            skipped.append(kw_clean)
            continue

        keyword = ReconciliationKeyword(
            keyword=kw_clean,
            keyword_type=data.keyword_type.value,
            gateway_id=data.gateway_id,
            created_by_id=current_user.id,
        )
        db.add(keyword)
        created.append(kw_clean)

    db.commit()

    logger.info(
        f"Bulk keywords created: {len(created)} added, {len(skipped)} skipped",
        extra={"user_id": current_user.id, "type": data.keyword_type.value}
    )

    return JSONResponse(content={
        "message": f"Created {len(created)} keywords",
        "created": created,
        "skipped": skipped,
    }, status_code=201)


@router.put("/keywords/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: int,
    data: KeywordUpdate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Update a keyword. User role only."""
    keyword = db.query(ReconciliationKeyword).filter(
        ReconciliationKeyword.id == keyword_id
    ).first()
    if not keyword:
        raise HTTPException(404, "Keyword not found")

    update_data = data.model_dump(exclude_unset=True)
    if "keyword_type" in update_data and update_data["keyword_type"]:
        update_data["keyword_type"] = update_data["keyword_type"].value

    for key, value in update_data.items():
        setattr(keyword, key, value)

    db.commit()
    db.refresh(keyword)

    logger.info(f"Keyword updated: {keyword_id}", extra={"user_id": current_user.id})
    return KeywordResponse.model_validate(keyword.to_dict())


@router.delete("/keywords/{keyword_id}")
async def delete_keyword(
    keyword_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Delete a keyword. User role only."""
    keyword = db.query(ReconciliationKeyword).filter(
        ReconciliationKeyword.id == keyword_id
    ).first()
    if not keyword:
        raise HTTPException(404, "Keyword not found")

    db.delete(keyword)
    db.commit()

    logger.info(f"Keyword deleted: {keyword_id}", extra={"user_id": current_user.id})
    return {"message": "Keyword deleted successfully"}


# =============================================================================
# SYSTEM SETTINGS ENDPOINTS
# =============================================================================

@router.get("/system", response_model=List[SystemSettingResponse])
async def list_system_settings(
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """List all system settings."""
    settings = db.query(SystemSetting).order_by(SystemSetting.key).all()
    return [SystemSettingResponse.model_validate(s) for s in settings]


@router.get("/system/{key}", response_model=SystemSettingResponse)
async def get_system_setting(
    key: str,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_active_user)
):
    """Get a specific system setting by key."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(404, f"Setting '{key}' not found")
    return SystemSettingResponse.model_validate(setting)


@router.put("/system/{key}", response_model=SystemSettingResponse)
async def update_system_setting(
    key: str,
    data: SystemSettingUpdate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Update a system setting. User role only."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(404, f"Setting '{key}' not found")

    if not setting.is_editable:
        raise HTTPException(400, f"Setting '{key}' is not editable")

    setting.value = data.value
    setting.updated_by_id = current_user.id
    db.commit()
    db.refresh(setting)

    logger.info(f"System setting updated: {key}", extra={"user_id": current_user.id})
    return SystemSettingResponse.model_validate(setting)


@router.post("/system", response_model=SystemSettingResponse, status_code=201)
async def create_system_setting(
    data: SystemSettingCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Create a new system setting. User role only."""
    # Check for duplicate key
    existing = db.query(SystemSetting).filter(SystemSetting.key == data.key).first()
    if existing:
        raise HTTPException(400, f"Setting with key '{data.key}' already exists")

    setting = SystemSetting(
        key=data.key,
        value=data.value,
        value_type=data.value_type,
        description=data.description,
        is_editable=data.is_editable,
        updated_by_id=current_user.id,
    )
    db.add(setting)
    db.commit()
    db.refresh(setting)

    logger.info(f"System setting created: {data.key}", extra={"user_id": current_user.id})
    return SystemSettingResponse.model_validate(setting)


@router.delete("/system/{key}")
async def delete_system_setting(
    key: str,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """Delete a system setting. User role only."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(404, f"Setting '{key}' not found")

    db.delete(setting)
    db.commit()

    logger.info(f"System setting deleted: {key}", extra={"user_id": current_user.id})
    return {"message": f"Setting '{key}' deleted successfully"}


# =============================================================================
# SEED DEFAULT SETTINGS
# =============================================================================

@router.post("/seed-defaults", status_code=201)
async def seed_default_settings(
    db: Session = Depends(get_database),
    current_user: User = Depends(require_user_role)
):
    """
    Seed default settings if they don't exist. User role only.

    Creates default date formats, common countries/currencies,
    and standard reconciliation keywords.
    """
    created = {
        "date_formats": 0,
        "countries": 0,
        "currencies": 0,
        "keywords": 0,
    }

    # Default date formats
    default_formats = [
        ("%Y-%m-%d", "ISO Format (YYYY-MM-DD)", "2024-01-15", True),
        ("%d/%m/%Y", "DD/MM/YYYY", "15/01/2024", False),
        ("%m/%d/%Y", "MM/DD/YYYY (US)", "01/15/2024", False),
        ("%d-%m-%Y", "DD-MM-YYYY", "15-01-2024", False),
        ("%Y/%m/%d", "YYYY/MM/DD", "2024/01/15", False),
    ]

    for fmt, name, example, is_default in default_formats:
        existing = db.query(DateFormat).filter(DateFormat.format_string == fmt).first()
        if not existing:
            df = DateFormat(
                format_string=fmt,
                display_name=name,
                example=example,
                is_default=is_default,
                created_by_id=current_user.id,
            )
            db.add(df)
            created["date_formats"] += 1

    # Default countries and currencies
    default_countries = [
        ("KE", "Kenya", [("KES", "Kenyan Shilling", "KSh", True)]),
        ("UG", "Uganda", [("UGX", "Ugandan Shilling", "USh", True)]),
        ("TZ", "Tanzania", [("TZS", "Tanzanian Shilling", "TSh", True)]),
        ("NG", "Nigeria", [("NGN", "Nigerian Naira", "₦", True)]),
        ("GH", "Ghana", [("GHS", "Ghanaian Cedi", "GH₵", True)]),
        ("ZA", "South Africa", [("ZAR", "South African Rand", "R", True)]),
        ("US", "United States", [("USD", "US Dollar", "$", True)]),
        ("GB", "United Kingdom", [("GBP", "British Pound", "£", True)]),
    ]

    for code, name, currencies in default_countries:
        existing = db.query(Country).filter(Country.code == code).first()
        if not existing:
            country = Country(code=code, name=name, created_by_id=current_user.id)
            db.add(country)
            db.flush()
            created["countries"] += 1

            for curr_code, curr_name, symbol, is_default in currencies:
                currency = Currency(
                    code=curr_code,
                    name=curr_name,
                    symbol=symbol,
                    country_id=country.id,
                    is_default=is_default,
                )
                db.add(currency)
                created["currencies"] += 1

    # Default reconciliation keywords
    default_keywords = {
        "charge": ["CHARGE", "FEE", "COMMISSION", "LEVY", "LEDGER FEE", "SERVICE CHARGE", "TRANSACTION FEE"],
        "reversal": ["REVERSAL", "REVERSED", "REFUND", "REFUNDED", "CANCELLED", "CANCELED", "RETURNED"],
    }

    for kw_type, keywords in default_keywords.items():
        for kw in keywords:
            existing = db.query(ReconciliationKeyword).filter(
                ReconciliationKeyword.keyword == kw,
                ReconciliationKeyword.keyword_type == kw_type,
            ).first()
            if not existing:
                keyword = ReconciliationKeyword(
                    keyword=kw,
                    keyword_type=kw_type,
                    created_by_id=current_user.id,
                )
                db.add(keyword)
                created["keywords"] += 1

    db.commit()

    logger.info(f"Default settings seeded: {created}", extra={"user_id": current_user.id})

    return JSONResponse(content={
        "message": "Default settings seeded successfully",
        "created": created,
    }, status_code=201)
