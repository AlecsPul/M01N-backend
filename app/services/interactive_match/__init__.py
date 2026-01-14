"""
Interactive Match Module
Multi-turn prompt parsing with validation for matching system.
"""
from app.services.interactive_match.parser import parse_user_prompt
from app.schemas.interactive_match import (
    ParsedPromptResult,
    PriorState,
    MissingRequirements,
    SessionState,
    AccumulatedData,
    Turn
)
from app.services.validation_helpers import validate_parsed_data
from app.services.session_manager import create_turn, update_accumulated_data
from app.services.interactive_match.questioning import (
    start_session,
    continue_session,
    SessionQuestion,
    SessionComplete,
    SessionResult,
    is_session_complete,
    get_state,
    get_question
)
from app.services.prompt_composer import compose_final_prompt, format_for_matching_service
from app.services.interactive_matching_service import run_final_match, run_final_match_with_names

__all__ = [
    "parse_user_prompt",
    "ParsedPromptResult",
    "PriorState",
    "MissingRequirements",
    "validate_parsed_data",
    "SessionState",
    "AccumulatedData",
    "Turn",
    "create_turn",
    "update_accumulated_data",
    "start_session",
    "continue_session",
    "SessionQuestion",
    "SessionComplete",
    "SessionResult",
    "is_session_complete",
    "get_state",
    "get_question",
    "compose_final_prompt",
    "format_for_matching_service",
    "run_final_match",
    "run_final_match_with_names"
]
