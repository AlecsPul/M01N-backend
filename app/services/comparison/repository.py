"""
Comparison Repository
Database operations for application comparison features.
"""
from typing import Optional, Dict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func


async def get_app_by_name(db: AsyncSession, company_name: str) -> Optional[Dict]:
    """
    Resolve company name to application ID.
    Case-insensitive exact match. If multiple matches, prefer exact case.
    
    Args:
        db: Database session
        company_name: Company name to search
        
    Returns:
        Dict with app_id and name, or None if not found
    """
    query = text("""
        SELECT id, name
        FROM application
        WHERE LOWER(name) = LOWER(:company_name)
        ORDER BY 
            CASE WHEN name = :company_name THEN 0 ELSE 1 END
        LIMIT 1
    """)
    
    result = await db.execute(query, {"company_name": company_name})
    row = result.fetchone()
    
    if row:
        return {
            "app_id": row[0],
            "name": row[1]
        }
    return None


async def get_features_text(db: AsyncSession, app_id: UUID) -> Optional[str]:
    """
    Fetch features_text for an application.
    
    Args:
        db: Database session
        app_id: Application UUID
        
    Returns:
        features_text string or None
    """
    query = text("""
        SELECT features_text
        FROM application_features
        WHERE app_id = :app_id
    """)
    
    result = await db.execute(query, {"app_id": app_id})
    row = result.fetchone()
    
    if row and row[0]:
        return row[0]
    return None


async def get_fallback_data(db: AsyncSession, app_id: UUID) -> Dict:
    """
    Get fallback data when features_text is unavailable.
    Fetches labels, integration_keys, and tags.
    
    Args:
        db: Database session
        app_id: Application UUID
        
    Returns:
        Dict with labels, integration_keys, tags lists
    """
    labels_query = text("""
        SELECT al.label
        FROM application_labels al
        JOIN application_search aps ON aps.id = al.app_search_id
        WHERE aps.app_id = :app_id
    """)
    
    keys_query = text("""
        SELECT aik.integration_key
        FROM application_integration_keys aik
        JOIN application_search aps ON aps.id = aik.app_search_id
        WHERE aps.app_id = :app_id
    """)
    
    tags_query = text("""
        SELECT tag
        FROM apps_tags
        WHERE app_id = :app_id
    """)
    
    labels_result = await db.execute(labels_query, {"app_id": app_id})
    labels = [row[0] for row in labels_result.fetchall()]
    
    keys_result = await db.execute(keys_query, {"app_id": app_id})
    integration_keys = [row[0] for row in keys_result.fetchall()]
    
    tags_result = await db.execute(tags_query, {"app_id": app_id})
    tags = [row[0] for row in tags_result.fetchall()]
    
    return {
        "labels": labels,
        "integration_keys": integration_keys,
        "tags": tags
    }
