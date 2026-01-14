"""
Session State Management
State management utilities for multi-turn interactive matching sessions.
"""
from typing import List
from app.schemas.interactive_match import (
    SessionState,
    AccumulatedData,
    Turn,
    ParsedPromptResult
)


def merge_lists(existing: List[str], new_items: List[str], max_items: int = 10) -> List[str]:
    """
    Merge two lists, removing duplicates and capping at max_items.
    
    Args:
        existing: Current list
        new_items: New items to add
        max_items: Maximum items to keep
        
    Returns:
        Merged and deduplicated list
    """
    seen = set()
    result = []
    
    for item in existing + new_items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
            if len(result) >= max_items:
                break
    
    return result


def update_accumulated_data(
    current: AccumulatedData,
    parsed: ParsedPromptResult
) -> AccumulatedData:
    """
    Update accumulated data with new parsed results.
    
    Args:
        current: Current accumulated data
        parsed: New parsed data to merge
        
    Returns:
        Updated accumulated data
    """
    return AccumulatedData(
        labels=merge_lists(current.labels, parsed.labels, max_items=10),
        tags=merge_lists(current.tags, parsed.tags, max_items=10),
        integrations=merge_lists(current.integrations, parsed.integrations, max_items=10)
    )


def create_turn(user_text: str, parsed: ParsedPromptResult) -> Turn:
    """
    Create a new turn record.
    
    Args:
        user_text: Original user input
        parsed: Parsed result
        
    Returns:
        Turn object
    """
    return Turn(
        user_text=user_text,
        english_text=parsed.combined_prompt_english,
        parsed=parsed
    )
