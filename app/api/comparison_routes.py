"""
Comparison API Routes
Endpoint for comparing two applications by company name.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.services.comparison import build_comparison, CompanyNotFoundException


router = APIRouter(prefix="/api/v1", tags=["Comparison"])


@router.post(
    "/compare",
    status_code=status.HTTP_200_OK,
    response_model=ComparisonResponse,
    summary="Compare two applications by company name",
    description="""
    Compare two applications side-by-side with unified attributes and highlights.
    
    Returns:
    - Unified list of all attributes (labels, integrations, tags) across both apps
    - Each app has 'has' flags indicating which attributes it possesses
    - Exactly 3 competitive highlights per application (AI-generated)
    
    Error codes:
    - 400: Invalid request (same company names or empty values)
    - 404: One or both companies not found in database
    - 502: OpenAI service failure (highlights generation failed)
    """,
)
async def compare_applications(
    request: ComparisonRequest,
    db: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """
    Compare two applications and return unified comparison data.
    
    Args:
        request: Company names to compare
        db: Database session
        
    Returns:
        ComparisonResponse with both application comparison objects
        
    Raises:
        HTTPException: 400 for invalid input, 404 for missing companies, 502 for service errors
    """
    # Validate company names are different
    if request.company_a.lower() == request.company_b.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company names must be different"
        )
    
    try:
        # Call builder to get both comparison objects
        app_a, app_b = await build_comparison(
            db=db,
            company_name_1=request.company_a,
            company_name_2=request.company_b
        )
        
        # Return structured response
        return ComparisonResponse(
            company_a=app_a,
            company_b=app_b
        )
        
    except CompanyNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        # Check if it's an OpenAI/service error
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ["openai", "api", "timeout", "connection"]):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service error: {str(e)}"
            )
        # Re-raise as 500 for unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during comparison: {str(e)}"
        )
