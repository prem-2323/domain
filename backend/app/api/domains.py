from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status
from app.models.domain import DomainSearchResponse
from app.services.search_service import SearchService
from app.services.catalog_service import CatalogService
from app.core.config import settings

router = APIRouter(prefix="/api/domains", tags=["domains"])


@router.get(
    "/search",
    response_model=DomainSearchResponse,
    summary="Search domain availability and pricing across extensions",
    description="Validates a domain name and returns availability and pricing across supported extensions.",
)
async def search_domains(
    name: str = Query(
        ...,
        description="Domain name to search (e.g. tala or tala.dev)",
        min_length=1,
    ),
    provider: Optional[str] = Query(
        default=None,
        description="Optional registrar provider override (e.g. 'mock' | 'godaddy' | 'namecheap')",
    ),
):
    success, result, error_msg = await SearchService.search(name, provider_name=provider)
    if not success or result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_DOMAIN_NAME",
                "message": error_msg or "Invalid domain name provided.",
                "query": name,
            },
        )
    return result


@router.get("/extensions", summary="Get supported domain extensions")
def get_extensions():
    return {
        "extensions": CatalogService.get_supported_extensions(),
        "catalog": CatalogService.get_catalog_details(),
    }


@router.get("/provider", summary="Get active registrar provider metadata")
def get_provider_status():
    """
    Returns sanitized active registrar provider status and available integrations.
    Never exposes API secrets or credentials.
    """
    return settings.get_safe_summary()
