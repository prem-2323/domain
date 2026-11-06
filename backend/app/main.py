from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.domains import router as domains_router
from app.api.registrations import (
    router as registrations_router,
    admin_router as admin_registrations_router,
)

app = FastAPI(
    title="MasterTools Domains API",
    description="Domain search and management platform",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount domain search and extension routes
app.include_router(domains_router)

# Mount .GY registration request routes
app.include_router(registrations_router)
app.include_router(admin_registrations_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to MasterTools Domains API",
        "status": "running"
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "mastertools-domains"
    }
