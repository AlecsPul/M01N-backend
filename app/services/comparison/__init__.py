from app.services.comparison.highlights import get_highlights_for_company, generate_highlights
from app.services.comparison.repository import get_app_by_name, get_features_text
from app.services.comparison.builder import build_comparison, CompanyNotFoundException

__all__ = [
    "get_highlights_for_company",
    "generate_highlights",
    "get_app_by_name",
    "get_features_text",
    "build_comparison",
    "CompanyNotFoundException"
]
