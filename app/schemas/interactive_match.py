"""
Interactive Match Schemas
Pydantic models for interactive matching system.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# Core parsing schemas
class MissingRequirements(BaseModel):
    """Missing requirements for a valid prompt"""
    labels_needed: int = Field(0, ge=0, description="Number of additional labels needed")
    tags_needed: int = Field(0, ge=0, description="Number of additional tags needed")
    integrations_needed: int = Field(0, ge=0, description="Number of additional integrations needed")


class ParsedPromptResult(BaseModel):
    """Result from parsing a user prompt"""
    combined_prompt_english: str = Field(..., description="User prompt translated/normalized to English")
    labels: List[str] = Field(default_factory=list, description="Labels from closed catalog")
    tags: List[str] = Field(default_factory=list, description="Free-form tags (1-10)")
    integrations: List[str] = Field(default_factory=list, description="Integration names (0-10)")
    is_valid: bool = Field(..., description="Whether prompt meets minimum requirements")
    missing: MissingRequirements = Field(default_factory=MissingRequirements, description="What is missing if invalid")


class PriorState(BaseModel):
    """Optional prior state from previous parsing iterations"""
    labels: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    integrations: List[str] = Field(default_factory=list)
    combined_prompt_english: str = Field("", description="Previously accumulated English prompt")


# State management schemas
class Turn(BaseModel):
    """Single turn in the conversation"""
    user_text: str = Field(..., description="Original user input")
    english_text: str = Field(..., description="Translated/normalized English text")
    parsed: ParsedPromptResult = Field(..., description="Parsed data from this turn")


class AccumulatedData(BaseModel):
    """Accumulated extracted data across all turns"""
    labels: List[str] = Field(default_factory=list, description="All accumulated labels")
    tags: List[str] = Field(default_factory=list, description="All accumulated tags")
    integrations: List[str] = Field(default_factory=list, description="All accumulated integrations")


class SessionState(BaseModel):
    """Complete state for an interactive matching session"""
    turns: List[Turn] = Field(default_factory=list, description="Conversation history")
    accumulated: AccumulatedData = Field(default_factory=AccumulatedData, description="Merged data")
    missing: MissingRequirements = Field(default_factory=MissingRequirements, description="What's still needed")
    is_valid: bool = Field(False, description="Whether requirements are satisfied")


# API request/response schemas
class StartRequest(BaseModel):
    """Request to start an interactive matching session"""
    prompt_text: str = Field(
        ...,
        description="Initial user requirement description",
        min_length=10,
        max_length=2000
    )


class ContinueRequest(BaseModel):
    """Request to continue an interactive session with an answer"""
    session: SessionState = Field(..., description="Current session state")
    answer_text: str = Field(
        ...,
        description="User's answer to the previous question",
        min_length=1,
        max_length=1000
    )


class FinalizeRequest(BaseModel):
    """Request to run final matching on a valid session"""
    session: SessionState = Field(..., description="Valid session state")
    top_k: int = Field(
        default=30,
        description="Number of candidates to consider",
        ge=10,
        le=100
    )
    top_n: int = Field(
        default=10,
        description="Number of results to return",
        ge=1,
        le=50
    )


class MatchResult(BaseModel):
    """Single match result"""
    app_id: str = Field(..., description="Application UUID")
    name: str = Field(..., description="Application name")
    similarity_percent: float = Field(..., description="Match percentage")


class NeedsMoreResponse(BaseModel):
    """Response when session needs more information"""
    status: Literal["needs_more"] = Field("needs_more", description="Status indicator")
    session: SessionState = Field(..., description="Updated session state")
    question: str = Field(..., description="Next question to ask user")
    missing: MissingRequirements = Field(..., description="What information is still needed")


class ReadyResponse(BaseModel):
    """Response when session is ready for matching"""
    status: Literal["ready"] = Field("ready", description="Status indicator")
    session: SessionState = Field(..., description="Final session state")
    final_prompt: str = Field(..., description="Composed final prompt")
    results: Optional[List[MatchResult]] = Field(None, description="Match results if computed")


class BuyerStructure(BaseModel):
    """Buyer requirements structure"""
    buyer_text: str
    labels_must: List[str]
    labels_nice: List[str]
    tag_must: List[str]
    tag_nice: List[str]
    integration_required: List[str]
    integration_nice: List[str]
    constraints: dict
    notes: str
