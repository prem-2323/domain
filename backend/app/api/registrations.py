from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.models.registration import (
    CreateRegistrationRequest,
    UpdateRegistrationRequest,
    RegistrationRequestResponse,
    RegistrationRequestListResponse,
    RegistrationRequestStatus,
)
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/api/registrations", tags=["registrations"])
admin_router = APIRouter(prefix="/api/admin/registrations", tags=["admin-registrations"])


@router.post(
    "/requests",
    response_model=RegistrationRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a manual .GY domain registration request",
    description="Submits a customer request for a .gy domain. Does not perform automated purchase or claim immediate allocation.",
)
async def create_registration_request(payload: CreateRegistrationRequest):
    success, result, error_msg, http_code = RegistrationService.create_request(payload)
    if not success or result is None:
        raise HTTPException(
            status_code=http_code,
            detail={
                "error": "REGISTRATION_REQUEST_REJECTED",
                "message": error_msg or "Failed to create registration request.",
                "domain": payload.domain,
            },
        )
    return result


@router.get(
    "/requests/{request_id}",
    response_model=RegistrationRequestResponse,
    summary="Get registration request status by Request ID",
    description="Fetches current review and coordination status for a customer's .gy domain registration request.",
)
async def get_registration_request(request_id: str):
    item = RegistrationService.get_request(request_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "REQUEST_NOT_FOUND",
                "message": f"Registration request '{request_id}' was not found.",
                "request_id": request_id,
            },
        )
    return item


@router.get(
    "/requests",
    response_model=RegistrationRequestListResponse,
    summary="List all registration requests (Admin / Overview)",
    description="Lists all submitted .gy registration requests, optionally filtered by status.",
)
async def list_registration_requests(
    status_filter: Optional[RegistrationRequestStatus] = Query(
        default=None, alias="status", description="Filter requests by status"
    ),
):
    items = RegistrationService.list_requests(status_filter=status_filter)
    return RegistrationRequestListResponse(total=len(items), requests=items)


@router.patch(
    "/requests/{request_id}",
    response_model=RegistrationRequestResponse,
    summary="Update registration request status and notes (Admin)",
    description="Updates request status, confirmed accredited registrar pricing, and internal admin notes.",
)
async def update_registration_request(
    request_id: str, payload: UpdateRegistrationRequest
):
    success, updated, error_msg = RegistrationService.update_request(
        request_id, payload
    )
    if not success or updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "UPDATE_FAILED",
                "message": error_msg or f"Request '{request_id}' not found.",
                "request_id": request_id,
            },
        )
    return updated


# Also mount update on admin_router for explicit admin endpoints
@admin_router.get(
    "/requests",
    response_model=RegistrationRequestListResponse,
    summary="List all registration requests for Admin",
)
async def admin_list_registration_requests(
    status_filter: Optional[RegistrationRequestStatus] = Query(
        default=None, alias="status"
    ),
):
    items = RegistrationService.list_requests(status_filter=status_filter)
    return RegistrationRequestListResponse(total=len(items), requests=items)


@admin_router.patch(
    "/requests/{request_id}",
    response_model=RegistrationRequestResponse,
    summary="Admin status and notes update",
)
async def admin_patch_request(request_id: str, payload: UpdateRegistrationRequest):
    return await update_registration_request(request_id, payload)


@admin_router.put(
    "/requests/{request_id}",
    response_model=RegistrationRequestResponse,
    summary="Admin status and notes full update",
)
async def admin_put_request(request_id: str, payload: UpdateRegistrationRequest):
    return await update_registration_request(request_id, payload)
