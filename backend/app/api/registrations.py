import secrets
from typing import Optional, Union
from fastapi import APIRouter, HTTPException, Query, Request, Response, Depends, Header, status

from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.core.security import get_current_admin, verify_password, AdminSessionManager
from app.models.registration import (
    CreateRegistrationRequest,
    UpdateRegistrationRequest,
    CustomerRequestCreatedResponse,
    PublicRegistrationRequestResponse,
    CustomerVerifiedRequestResponse,
    AdminRegistrationRequestResponse,
    AdminRegistrationRequestListResponse,
    AdminLoginRequest,
    AdminLoginResponse,
    RegistrationRequestStatus,
)
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/api/registrations", tags=["registrations"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


# ============================================================================
# 1. PUBLIC CUSTOMER ENDPOINTS (Rate limited, strictly sanitized)
# ============================================================================

@router.post(
    "/requests",
    response_model=CustomerRequestCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a domain registration request (Free Testing Mode)",
    description="Submits a customer inquiry for a domain across supported extensions. Enforces validation, deduplication, and returns a private tracking token.",
)
async def create_registration_request(
    request: Request,
    payload: CreateRegistrationRequest,
):
    # Enforce rate limiting on request creation (10/min per IP)
    rate_limiter.check_rate_limit(
        request=request,
        action="registration-creation",
        max_requests=settings.RATE_LIMIT_CREATE_PER_MINUTE,
        window_seconds=60,
    )

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
    response_model=Union[PublicRegistrationRequestResponse, CustomerVerifiedRequestResponse],
    summary="Public tracking lookup for a registration request",
    description="Public callers receive ONLY sanitized status information (Zero customer personal details, messages, or admin notes). If a valid customer tracking token is provided via the X-Customer-Tracking-Token header, verified customer submission details are returned.",
)
async def get_registration_request(
    request: Request,
    request_id: str,
    x_customer_tracking_token: Optional[str] = Header(
        default=None,
        alias="X-Customer-Tracking-Token",
        description="Private customer tracking token header for verified lookup",
    ),
):
    # Enforce rate limiting on public status tracking (60/min per IP)
    rate_limiter.check_rate_limit(
        request=request,
        action="status-tracking",
        max_requests=settings.RATE_LIMIT_TRACK_PER_MINUTE,
        window_seconds=60,
    )

    # 1. If tracking token is provided via dedicated header, verify against customer record
    token = x_customer_tracking_token or request.headers.get("x-customer-tracking-token")
    if token and token.strip():
        verified = RegistrationService.get_customer_verified_request(request_id, token.strip())
        if verified:
            return verified

    # 2. Otherwise return strictly sanitized public response
    public_res = RegistrationService.get_public_request(request_id)
    if not public_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "REQUEST_NOT_FOUND",
                "message": f"Registration request '{request_id}' was not found.",
                "request_id": request_id,
            },
        )
    return public_res


# ============================================================================
# 2. PROTECTED ADMIN WORKFLOW ENDPOINTS (Strictly 401 unauthenticated / 403 unauthorized)
# ============================================================================

@router.get(
    "/requests",
    response_model=AdminRegistrationRequestListResponse,
    summary="List all registration requests (Admin protected)",
    description="Lists all registration requests. Requires valid administrator authentication.",
)
async def list_registration_requests(
    status_filter: Optional[RegistrationRequestStatus] = Query(
        default=None, alias="status", description="Filter requests by status"
    ),
    _admin: dict = Depends(get_current_admin),
):
    items = RegistrationService.list_admin_requests(status_filter=status_filter)
    return AdminRegistrationRequestListResponse(total=len(items), requests=items)


@router.patch(
    "/requests/{request_id}",
    response_model=AdminRegistrationRequestResponse,
    summary="Update registration request status and notes (Admin protected)",
    description="Updates request status, confirmed accredited registrar pricing, and internal admin notes. Requires admin authentication.",
)
async def update_registration_request(
    request_id: str,
    payload: UpdateRegistrationRequest,
    _admin: dict = Depends(get_current_admin),
):
    success, updated, error_msg, http_code = RegistrationService.update_request(
        request_id, payload
    )
    if not success or updated is None:
        raise HTTPException(
            status_code=http_code,
            detail={
                "error": "UPDATE_FAILED",
                "message": error_msg or f"Request '{request_id}' not found.",
                "request_id": request_id,
            },
        )
    return updated


# ============================================================================
# 3. ADMIN AUTHENTICATION & MANAGEMENT ENDPOINTS (/api/admin)
# ============================================================================

@admin_router.post(
    "/login",
    response_model=AdminLoginResponse,
    summary="Admin login and session creation",
    description="Authenticates administrator credentials and returns a secure session token and HTTP-only cookie.",
)
async def admin_login(
    payload: AdminLoginRequest,
    response: Response,
):
    # Verify username and password
    valid_user = secrets.compare_digest(payload.username.strip(), settings.ADMIN_USERNAME)
    valid_pass = verify_password(payload.password, settings.ADMIN_PASSWORD)

    if not valid_user or not valid_pass:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AUTHENTICATION_FAILED",
                "message": "Invalid administrator username or password.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    session = AdminSessionManager.create_session(payload.username.strip())

    # Set secure HTTP-only cookie
    response.set_cookie(
        key="admin_session",
        value=session["session_token"],
        httponly=True,
        samesite="lax",
        secure=settings.APP_ENV == "production",
        max_age=settings.ADMIN_SESSION_EXPIRE_HOURS * 3600,
        path="/",
    )

    return AdminLoginResponse(
        session_token=session["session_token"],
        username=session["username"],
        expires_at=session["expires_at"],
        message="Administrator authenticated successfully.",
    )


@admin_router.post(
    "/logout",
    summary="Admin logout and session revocation",
    description="Revokes the current administrator session token and clears the cookie.",
)
async def admin_logout(
    response: Response,
    admin: dict = Depends(get_current_admin),
):
    token = admin.get("session_token")
    if token:
        AdminSessionManager.revoke_session(token)

    response.delete_cookie(key="admin_session", path="/")
    return {"message": "Admin session revoked and logged out successfully."}


@admin_router.get(
    "/me",
    summary="Verify active admin session",
    description="Returns current administrator identity if session is active.",
)
async def admin_me(
    admin: dict = Depends(get_current_admin),
):
    return {
        "authenticated": True,
        "username": admin["username"],
    }


# Admin aliased routes under /api/admin/registrations
@admin_router.get(
    "/registrations/requests",
    response_model=AdminRegistrationRequestListResponse,
    summary="Admin list registration requests",
)
async def admin_list_requests(
    status_filter: Optional[RegistrationRequestStatus] = Query(default=None, alias="status"),
    admin: dict = Depends(get_current_admin),
):
    return await list_registration_requests(status_filter=status_filter, _admin=admin)


@admin_router.get(
    "/registrations/requests/{request_id}",
    response_model=AdminRegistrationRequestResponse,
    summary="Admin get full registration request details",
)
async def admin_get_request(
    request_id: str,
    _admin: dict = Depends(get_current_admin),
):
    item = RegistrationService.get_admin_request(request_id)
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


@admin_router.patch(
    "/registrations/requests/{request_id}",
    response_model=AdminRegistrationRequestResponse,
    summary="Admin patch registration request",
)
async def admin_patch_request(
    request_id: str,
    payload: UpdateRegistrationRequest,
    admin: dict = Depends(get_current_admin),
):
    return await update_registration_request(request_id, payload, _admin=admin)


@admin_router.put(
    "/registrations/requests/{request_id}",
    response_model=AdminRegistrationRequestResponse,
    summary="Admin put registration request",
)
async def admin_put_request(
    request_id: str,
    payload: UpdateRegistrationRequest,
    admin: dict = Depends(get_current_admin),
):
    return await update_registration_request(request_id, payload, _admin=admin)
