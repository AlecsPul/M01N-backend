"""
Interactive Match Validation
Validation logic for parsed prompts.
"""
from typing import List, Tuple
from app.schemas.interactive_match import MissingRequirements


MIN_LABELS_REQUIRED = 2
MIN_TAGS_REQUIRED = 1
MIN_INTEGRATIONS_REQUIRED = 1


def validate_parsed_data(
    labels: List[str],
    tags: List[str],
    integrations: List[str]
) -> Tuple[bool, MissingRequirements]:
    """
    Validate if parsed data meets minimum requirements.
    
    Args:
        labels: List of extracted labels
        tags: List of extracted tags
        integrations: List of extracted integrations
        
    Returns:
        Tuple of (is_valid, missing_requirements)
    """
    labels_count = len(labels)
    tags_count = len(tags)
    integrations_count = len(integrations)
    
    labels_needed = max(0, MIN_LABELS_REQUIRED - labels_count)
    tags_needed = max(0, MIN_TAGS_REQUIRED - tags_count)
    integrations_needed = max(0, MIN_INTEGRATIONS_REQUIRED - integrations_count)
    
    is_valid = (
        labels_count >= MIN_LABELS_REQUIRED and
        tags_count >= MIN_TAGS_REQUIRED and
        integrations_count >= MIN_INTEGRATIONS_REQUIRED
    )
    
    missing = MissingRequirements(
        labels_needed=labels_needed,
        tags_needed=tags_needed,
        integrations_needed=integrations_needed
    )
    
    return is_valid, missing


def deduplicate_and_normalize_tags(tags: List[str]) -> List[str]:
    """
    Deduplicate and normalize tags to Title Case.
    
    Args:
        tags: Raw list of tags
        
    Returns:
        Deduplicated, normalized tags
    """
    seen = set()
    result = []
    
    for tag in tags:
        normalized = tag.strip().title()
        if normalized and normalized.lower() not in seen:
            seen.add(normalized.lower())
            result.append(normalized)
    
    return result[:10]


def deduplicate_list(items: List[str]) -> List[str]:
    """
    Deduplicate list while preserving order.
    
    Args:
        items: List with potential duplicates
        
    Returns:
        Deduplicated list
    """
    seen = set()
    result = []
    
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    
    return result
