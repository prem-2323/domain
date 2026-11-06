import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.api.domains import router as domains_router
from app.api.registrations import (
    router as registrations_router,
    admin_router as admin_operations_router,
)

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="MasterTools Domains API",
    description="Dedicated .GY country-code domain search and registration platform",
    version="0.2.0",
)


# --- Security Middleware: Request Body Size Limiter ---
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app_instance, max_size_bytes: int = settings.MAX_REQUEST_BODY_BYTES):
        super().__init__(app_instance)
        self.max_size_bytes = max_size_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_size_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "PAYLOAD_TOO_LARGE",
                            "message": f"Request body exceeds maximum allowed size of {self.max_size_bytes} bytes.",
                            "detail": {
                                "error": "PAYLOAD_TOO_LARGE",
                                "message": f"Request body exceeds maximum allowed size of {self.max_size_bytes} bytes.",
                            },
                        },
                    )
            except ValueError:
                pass
        return await call_next(request)


app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=settings.MAX_REQUEST_BODY_BYTES)

# --- CORS Hardening: Restricted to Configured Frontend Origins ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# --- Global Exception Handler: Never Expose Internal Details to Clients ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred. Please contact support.",
        },
    )


# --- Route Mounting ---
app.include_router(domains_router)
app.include_router(registrations_router)
app.include_router(admin_operations_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to MasterTools Domains API (.GY ccTLD Registry Platform)",
        "status": "running",
        "environment": settings.APP_ENV,
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "mastertools-domains",
        "extension": ".gy",
        "version": "0.2.0",
    }
