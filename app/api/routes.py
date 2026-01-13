"""
API Routes
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["items"])

@router.get("/items/")
def get_items():
    """Get all items"""
    return {"items": []}

@router.get("/items/{item_id}")
def get_item(item_id: int):
    """Get specific item"""
    return {"item_id": item_id, "name": "Item"}

@router.post("/items/")
def create_item(name: str):
    """Create new item"""
    return {"name": name, "id": 1}
