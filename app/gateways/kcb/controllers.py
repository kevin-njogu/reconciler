from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from app.database.redis_configs import get_current_redis_session_id
from app.database.mysql_configs import Session, get_database

# router = APIRouter(prefix='/api/v1', tags=['Kcb_gateway'])
