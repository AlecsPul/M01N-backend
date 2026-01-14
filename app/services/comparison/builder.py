"""
Comparison Builder
Build application comparison objects with attributes and highlights.
"""
from typing import List, Tuple, Dict, Set
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.schemas.comparison import ApplicationComparison, AttributeItem, Highlight
from app.services.comparison.repository import get_app_by_name
from app.services.comparison.highlights import get_highlights_for_company


class CompanyNotFoundException(Exception):
    """Raised when a company name is not found in database"""
    pass


async def get_app_search_id(db: AsyncSession, app_id: UUID) -> UUID:
    """
    Get app_search_id for an app_id.
    
    Args:
        db: Database session
        app_id: Application UUID
        
    Returns:
        app_search_id UUID
    """
    query = text("""
        SELECT id
        FROM application_search
        WHERE app_id = :app_id
        LIMIT 1
    """)
    
    result = await db.execute(query, {"app_id": app_id})
    row = result.fetchone()
    
    if row:
        return row[0]
    return None


async def fetch_all_attributes(
    db: AsyncSession,
    app_id_1: UUID,
    app_id_2: UUID,
    app_search_id_1: UUID,
    app_search_id_2: UUID
) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """
    Fetch all attributes for both apps in batch queries.
    
    Returns:
        Tuple of (app1_attributes, app2_attributes)
        Each dict has keys: 'labels', 'integrations', 'tags'
    """
    labels_query = text("""
        SELECT app_search_id, label
        FROM application_labels
        WHERE app_search_id IN (:id1, :id2)
    """)
    
    keys_query = text("""
        SELECT app_search_id, integration_key
        FROM application_integration_keys
        WHERE app_search_id IN (:id1, :id2)
    """)
    
    tags_query = text("""
        SELECT app_id, tag
        FROM apps_tags
        WHERE app_id IN (:id1, :id2)
    """)
    
    app1_attrs = {"labels": set(), "integrations": set(), "tags": set()}
    app2_attrs = {"labels": set(), "integrations": set(), "tags": set()}
    
    labels_result = await db.execute(labels_query, {"id1": app_search_id_1, "id2": app_search_id_2})
    for search_id, label in labels_result.fetchall():
        if search_id == app_search_id_1:
            app1_attrs["labels"].add(label)
        else:
            app2_attrs["labels"].add(label)
    
    keys_result = await db.execute(keys_query, {"id1": app_search_id_1, "id2": app_search_id_2})
    for search_id, key in keys_result.fetchall():
        if search_id == app_search_id_1:
            app1_attrs["integrations"].add(key)
        else:
            app2_attrs["integrations"].add(key)
    
    tags_result = await db.execute(tags_query, {"id1": app_id_1, "id2": app_id_2})
    for app_id, tag in tags_result.fetchall():
        if app_id == app_id_1:
            app1_attrs["tags"].add(tag)
        else:
            app2_attrs["tags"].add(tag)
    
    return app1_attrs, app2_attrs


def build_unified_attributes(
    app1_attrs: Dict[str, Set[str]],
    app2_attrs: Dict[str, Set[str]]
) -> Dict[str, Set[str]]:
    """
    Build union of all attributes from both apps.
    
    Returns:
        Dict with keys: 'labels', 'integrations', 'tags'
        Values are sets of all unique attribute values
    """
    return {
        "labels": app1_attrs["labels"] | app2_attrs["labels"],
        "integrations": app1_attrs["integrations"] | app2_attrs["integrations"],
        "tags": app1_attrs["tags"] | app2_attrs["tags"]
    }


def create_attribute_list(
    app_attrs: Dict[str, Set[str]],
    all_attrs: Dict[str, Set[str]]
) -> List[AttributeItem]:
    """
    Create sorted attribute list with has flags.
    
    Args:
        app_attrs: Attributes this app has
        all_attrs: All attributes across both apps
        
    Returns:
        Sorted list of AttributeItem objects
    """
    attributes = []
    
    for integration in sorted(all_attrs["integrations"]):
        attributes.append(AttributeItem(
            type="integration",
            value=integration,
            has=integration in app_attrs["integrations"]
        ))
    
    for label in sorted(all_attrs["labels"]):
        attributes.append(AttributeItem(
            type="label",
            value=label,
            has=label in app_attrs["labels"]
        ))
    
    for tag in sorted(all_attrs["tags"]):
        attributes.append(AttributeItem(
            type="tag",
            value=tag,
            has=tag in app_attrs["tags"]
        ))
    
    return attributes


async def build_comparison(
    db: AsyncSession,
    company_name_1: str,
    company_name_2: str
) -> Tuple[ApplicationComparison, ApplicationComparison]:
    """
    Build comparison objects for two companies.
    
    Args:
        db: Database session
        company_name_1: First company name
        company_name_2: Second company name
        
    Returns:
        Tuple of (app1_comparison, app2_comparison)
        
    Raises:
        CompanyNotFoundException: If either company is not found
    """
    app1_data = await get_app_by_name(db, company_name_1)
    if not app1_data:
        raise CompanyNotFoundException(f"Company '{company_name_1}' not found")
    
    app2_data = await get_app_by_name(db, company_name_2)
    if not app2_data:
        raise CompanyNotFoundException(f"Company '{company_name_2}' not found")
    
    app1_id = app1_data["app_id"]
    app2_id = app2_data["app_id"]
    
    app1_search_id = await get_app_search_id(db, app1_id)
    app2_search_id = await get_app_search_id(db, app2_id)
    
    if not app1_search_id or not app2_search_id:
        raise CompanyNotFoundException("Application search data not found")
    
    app1_attrs, app2_attrs = await fetch_all_attributes(
        db, app1_id, app2_id, app1_search_id, app2_search_id
    )
    
    all_attrs = build_unified_attributes(app1_attrs, app2_attrs)
    
    app1_attribute_list = create_attribute_list(app1_attrs, all_attrs)
    app2_attribute_list = create_attribute_list(app2_attrs, all_attrs)
    
    app1_highlights_raw = await get_highlights_for_company(db, company_name_1)
    app2_highlights_raw = await get_highlights_for_company(db, company_name_2)
    
    app1_highlights = [Highlight(title=h["title"], detail=h["detail"]) for h in app1_highlights_raw]
    app2_highlights = [Highlight(title=h["title"], detail=h["detail"]) for h in app2_highlights_raw]
    
    app1_comparison = ApplicationComparison(
        name=app1_data["name"],
        attributes=app1_attribute_list,
        highlights=app1_highlights
    )
    
    app2_comparison = ApplicationComparison(
        name=app2_data["name"],
        attributes=app2_attribute_list,
        highlights=app2_highlights
    )
    
    return app1_comparison, app2_comparison
