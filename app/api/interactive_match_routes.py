"""
Interactive Match API Routes
Endpoints for multi-turn interactive matching with guided question flow.
"""
from fastapi import APIRouter, HTTPException, status
from typing import Union
import asyncpg

from app.core.config import settings
from app.schemas.interactive_match import (
    StartRequest,
    ContinueRequest,
    FinalizeRequest,
    NeedsMoreResponse,
    ReadyResponse,
    MatchResult
)
from app.services.interactive_match import (
    start_session,
    continue_session,
    SessionQuestion,
    SessionComplete,
    is_session_complete,
    get_state,
    get_question,
    compose_final_prompt,
    run_final_match_with_names
)

router = APIRouter(prefix="/api/v1/match/interactive", tags=["Interactive Matching"])


@router.post(
    "/start",
    status_code=status.HTTP_200_OK,
    response_model=Union[NeedsMoreResponse, ReadyResponse],
    summary="Start interactive matching session",
    description="""
    Start a new interactive matching session with an initial prompt.
    
    Returns:
    - If prompt is already valid (2+ labels, 1+ tag, 1+ integration): status='ready'
    - If more information needed: status='needs_more' with a targeted question
    
    The session state is returned to the client and must be sent back in subsequent requests.
    No server-side session storage for stateless operation.
    """
)
async def start_interactive_session(request: StartRequest):
    """
    Start interactive matching session.
    
    Args:
        request: StartRequest with initial prompt_text
        
    Returns:
        NeedsMoreResponse or ReadyResponse
        
    Raises:
        HTTPException: 400 for invalid input, 502 for OpenAI failures
    """
    try:
        result = await start_session(request.prompt_text)
        
        if is_session_complete(result):
            state = get_state(result)
            final_prompt = compose_final_prompt(state)
            
            return ReadyResponse(
                session=state,
                final_prompt=final_prompt,
                results=None
            )
        else:
            state = get_state(result)
            question = get_question(result)
            
            return NeedsMoreResponse(
                session=state,
                question=question,
                missing=state.missing
            )
    
    except Exception as e:
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ["openai", "api", "timeout", "connection"]):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service error: {str(e)}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting session: {str(e)}"
        )


@router.post(
    "/continue",
    status_code=status.HTTP_200_OK,
    response_model=Union[NeedsMoreResponse, ReadyResponse],
    summary="Continue interactive matching session",
    description="""
    Continue an existing interactive session with the user's answer.
    
    Returns:
    - If still missing information: status='needs_more' with next question
    - If requirements now satisfied: status='ready' with final prompt and optional results
    
    Send the session state received from the previous response.
    """
)
async def continue_interactive_session(request: ContinueRequest):
    """
    Continue interactive session with user's answer.
    
    Args:
        request: ContinueRequest with session state and answer_text
        
    Returns:
        NeedsMoreResponse or ReadyResponse
        
    Raises:
        HTTPException: 400 for invalid session, 502 for OpenAI failures
    """
    try:
        result = await continue_session(request.session, request.answer_text)
        
        if is_session_complete(result):
            state = get_state(result)
            final_prompt = compose_final_prompt(state)
            
            return ReadyResponse(
                session=state,
                final_prompt=final_prompt,
                results=None
            )
        else:
            state = get_state(result)
            question = get_question(result)
            
            return NeedsMoreResponse(
                session=state,
                question=question,
                missing=state.missing
            )
    
    except Exception as e:
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ["openai", "api", "timeout", "connection"]):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service error: {str(e)}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error continuing session: {str(e)}"
        )


@router.post(
    "/finalize",
    status_code=status.HTTP_200_OK,
    response_model=ReadyResponse,
    summary="Run final matching on completed session",
    description="""
    Execute the matching algorithm on a completed (valid) session.
    
    This endpoint runs the full matching pipeline:
    1. Composes final prompt from all session turns
    2. Generates embeddings
    3. Runs vector similarity + hybrid scoring
    4. Returns top N matches with names and percentages
    
    Session must be valid (is_valid=true).
    """
)
async def finalize_interactive_session(request: FinalizeRequest):
    """
    Run final matching on a valid session.
    
    Args:
        request: FinalizeRequest with valid session and parameters
        
    Returns:
        ReadyResponse with results
        
    Raises:
        HTTPException: 400 for invalid session, 502 for service errors
    """
    if not request.session.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not valid. Cannot run matching."
        )
    
    conn = None
    try:
        conn = await asyncpg.connect(settings.database_url)
        
        result = await run_final_match_with_names(
            conn,
            request.session,
            top_k=request.top_k,
            top_n=request.top_n
        )
        
        matches = [
            MatchResult(
                app_id=match["app_id"],
                name=match["name"],
                similarity_percent=match["similarity_percent"]
            )
            for match in result["results"]
        ]
        
        return ReadyResponse(
            session=request.session,
            final_prompt=result["final_prompt"],
            results=matches
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ["openai", "api", "timeout", "connection"]):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service error: {str(e)}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running match: {str(e)}"
        )
    finally:
        if conn:
            await conn.close()
