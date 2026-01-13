"""
API Routes with Database Integration
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.schemas.schemas import ItemCreate, ItemUpdate, ItemResponse, MessageResponse

router = APIRouter(prefix="/api/v1", tags=["items"])