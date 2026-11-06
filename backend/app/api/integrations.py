import logging
from typing import Literal, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Depends, status

from app.core.config import settings
from app.core.security import get_current_admin
from app.models.integration import (
    ProposedDnsPlan,
    DnsApplyRequest,
    IntegrationDeploymentStatus,
    IntegrationConfigStatus,
    CloudflareZoneInfo,
    DnsRecordItem,
)
from app.services.integrations.dns_workflow_service import dns_workflow_service
from app.services.integrations.cloudflare_service import cloudflare_service, CloudflareApiError

logger = logging.getLogger("integrations_api")

router = APIRouter()


@router.get(
    "/status",
    response_model=IntegrationConfigStatus,
    summary="Get status of external cloud integrations",
    description="Returns configuration and credential presence for Cloudflare, Vercel, and Render without exposing tokens or secrets.",
)
async def get_integration_status() -> IntegrationConfigStatus:
    summary = settings.get_safe_summary()
    return IntegrationConfigStatus(
        cloudflare=summary["integrations"]["cloudflare"],
        vercel=summary["integrations"]["vercel"],
        render=summary["integrations"]["render"],
    )


@router.get(
    "/plan",
    response_model=ProposedDnsPlan,
    summary="Generate proposed DNS plan and detect conflicts",
    description=(
        "Requires authenticated administrator session. "
        "Inspects Cloudflare zone status, assigned nameservers, and required hosting DNS records for Vercel or Render. "
        "Performs automated conflict detection against existing records and cryptographically signs the server-side plan."
    ),
)
async def get_proposed_plan(
    domain: str = Query(..., description="Target domain name (e.g. till.gy, myapp.com)"),
    target: Literal["vercel", "render"] = Query("vercel", description="Hosting destination"),
    admin: Dict[str, Any] = Depends(get_current_admin),
) -> ProposedDnsPlan:
    try:
        plan = await dns_workflow_service.get_proposed_plan(domain=domain, target_platform=target)
        return plan
    except CloudflareApiError as e:
        raise HTTPException(status_code=e.status_code, detail={"error": "CLOUDFLARE_ERROR", "message": e.message})


@router.post(
    "/apply",
    response_model=IntegrationDeploymentStatus,
    summary="Apply proposed DNS records to Cloudflare",
    description=(
        "Requires authenticated administrator session. "
        "Creates or updates DNS records in Cloudflare with explicit administrator approval. "
        "Enforces plan signature integrity, expiration check, drift detection, and conflict override approval."
    ),
)
async def apply_dns_plan(
    request: DnsApplyRequest,
    admin: Dict[str, Any] = Depends(get_current_admin),
) -> IntegrationDeploymentStatus:
    if not request.approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "APPROVAL_REQUIRED",
                "message": "Explicit administrator approval is required to create or modify Cloudflare DNS records.",
                "domain": request.domain,
            },
        )

    res = await dns_workflow_service.apply_dns_plan(request, admin_username=admin["username"])
    return res


@router.get(
    "/verify",
    response_model=IntegrationDeploymentStatus,
    summary="Verify live DNS propagation and platform deployment",
    description="Requires authenticated administrator session. Performs live authoritative DNS queries and queries Vercel or Render to check verified status.",
)
async def verify_deployment(
    domain: str = Query(..., description="Domain name to verify"),
    target: Literal["vercel", "render"] = Query("vercel", description="Hosting destination"),
    admin: Dict[str, Any] = Depends(get_current_admin),
) -> IntegrationDeploymentStatus:
    res = await dns_workflow_service.verify_deployment(domain=domain, target_platform=target)
    return res


@router.get(
    "/cloudflare/zone",
    response_model=CloudflareZoneInfo,
    summary="Inspect Cloudflare zone details",
    description="Requires authenticated administrator session. Retrieves active status, SSL/TLS mode, and assigned nameservers directly from Cloudflare API.",
)
async def get_cloudflare_zone(
    domain: str = Query(..., description="Domain name belonging to zone"),
    admin: Dict[str, Any] = Depends(get_current_admin),
) -> CloudflareZoneInfo:
    try:
        zone = await cloudflare_service.get_zone_for_domain(domain)
        if not zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "ZONE_NOT_FOUND", "message": f"No Cloudflare zone found for '{domain}'."},
            )
        return zone
    except CloudflareApiError as e:
        raise HTTPException(status_code=e.status_code, detail={"error": "CLOUDFLARE_ERROR", "message": e.message})


@router.get(
    "/cloudflare/dns-records",
    response_model=List[DnsRecordItem],
    summary="List existing Cloudflare DNS records",
    description="Requires authenticated administrator session. Retrieves existing DNS records in Cloudflare for the zone corresponding to the domain.",
)
async def list_cloudflare_dns_records(
    domain: str = Query(..., description="Domain name"),
    admin: Dict[str, Any] = Depends(get_current_admin),
) -> List[DnsRecordItem]:
    try:
        zone = await cloudflare_service.get_zone_for_domain(domain)
        if not zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "ZONE_NOT_FOUND", "message": f"No Cloudflare zone found for '{domain}'."},
            )
        records = await cloudflare_service.list_dns_records(zone.zone_id)
        return records
    except CloudflareApiError as e:
        raise HTTPException(status_code=e.status_code, detail={"error": "CLOUDFLARE_ERROR", "message": e.message})
