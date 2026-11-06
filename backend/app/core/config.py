import json
from typing import List, Optional, Dict, Any, Set
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator

# Known default values used strictly for local development and offline unit tests
DEV_DEFAULT_SECRET_KEY = "mastertools-domains-secret-admin-session-key-2026"
DEV_DEFAULT_ADMIN_PASSWORD = "MasterToolsGy2026!Admin"

# Blacklist of known default or weak secrets prohibited in production
KNOWN_DEFAULT_SECRETS: Set[str] = {
    "mastertools-domains-secret-admin-session-key-2026",
    "secret",
    "secret_key",
    "secretkey",
    "changeme",
    "password",
    "admin",
    "123456",
    "12345678",
    "default",
    "your_secret_key",
    "your_secret_key_here",
    "development_secret",
}

# Blacklist of known default or weak passwords prohibited in production
KNOWN_DEFAULT_PASSWORDS: Set[str] = {
    "mastertoolsgy2026!admin",
    "admin",
    "password",
    "changeme",
    "123456",
    "12345678",
    "administrator",
    "root",
    "your_admin_password",
    "your_password",
    "pass1234",
}


class Settings(BaseSettings):
    """
    Centralized configuration for MasterTools Domains backend.
    Loads from environment variables or .env file.
    API keys and secrets are strictly retained server-side and never exposed.
    """

    # Environment & Server
    APP_ENV: str = Field(default="development", description="development | staging | production")
    APP_NAME: str = "MasterTools Domains API"
    DEBUG: bool = Field(default=True, description="Debug mode flag")
    SECRET_KEY: Optional[str] = Field(
        default=None,
        repr=False,
        description="Secret key for signing admin sessions (required in production)",
    )
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://localhost:8000",
        ],
        description="Allowed frontend CORS origins",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    return json.loads(v_str)
                except Exception:
                    pass
            return [i.strip() for i in v_str.split(",") if i.strip()]
        return v

    # Admin Authentication
    ADMIN_USERNAME: str = Field(
        default="admin",
        description="Admin dashboard username (default 'admin' prohibited in production)",
    )
    ADMIN_PASSWORD: Optional[str] = Field(
        default=None,
        repr=False,
        description="Admin dashboard password (required in production)",
    )
    ADMIN_SESSION_EXPIRE_HOURS: int = Field(
        default=24,
        description="Admin session lifetime in hours",
    )

    # Free Testing Mode Configuration
    FREE_TESTING_MODE: bool = Field(
        default=True,
        description="Enable Free Testing Mode ($0 / Free for all domain extensions and all users)",
    )
    FREE_TESTING_DISCLAIMER: str = (
        "FREE TESTING MODE: No payment is collected by MasterTools Domains. "
        "This does not waive actual registry or accredited registrar fees."
    )
    SUPPORTED_EXTENSIONS: List[str] = Field(
        default=[".gy", ".com", ".in", ".org", ".net", ".co", ".io", ".tech", ".ai", ".me"],
        description="Configured domain extensions supported across the platform",
    )
    DATA_DIR: Optional[str] = Field(
        default=None,
        description="Persistent disk directory path for SQLite database (e.g. Render /var/data)",
    )

    # Security & Rate Limiting Limits
    MAX_REQUEST_BODY_BYTES: int = Field(
        default=64 * 1024,
        description="Maximum request body size in bytes (64 KB)",
    )
    RATE_LIMIT_CREATE_PER_MINUTE: int = Field(
        default=10,
        description="Max registration creation requests per minute per IP",
    )
    RATE_LIMIT_TRACK_PER_MINUTE: int = Field(
        default=60,
        description="Max tracking lookups per minute per IP",
    )

    # Registrar Provider Switcher ('mock' | 'godaddy' | 'namecheap' | 'porkbun')
    REGISTRAR_PROVIDER: str = Field(
        default="mock",
        description="Active domain registrar provider: 'mock' | 'godaddy' | 'namecheap' | 'porkbun'"
    )
    REGISTRAR_USE_SANDBOX: bool = Field(
        default=True,
        description="Whether to use registrar test/sandbox/OTE environments"
    )

    # Namecheap Credentials (Required only when REGISTRAR_PROVIDER == 'namecheap')
    NAMECHEAP_API_USER: Optional[str] = Field(default=None, repr=False, description="Namecheap API username")
    NAMECHEAP_API_KEY: Optional[str] = Field(default=None, repr=False, description="Namecheap API key")
    NAMECHEAP_USERNAME: Optional[str] = Field(default=None, repr=False, description="Namecheap account username")
    NAMECHEAP_CLIENT_IP: Optional[str] = Field(default=None, repr=False, description="Whitelisted client IP address")

    # GoDaddy Credentials (Required only when REGISTRAR_PROVIDER == 'godaddy')
    GODADDY_API_KEY: Optional[str] = Field(default=None, repr=False, description="GoDaddy API Key")
    GODADDY_API_SECRET: Optional[str] = Field(default=None, repr=False, description="GoDaddy API Secret")

    # Porkbun Credentials (Optional)
    PORKBUN_API_KEY: Optional[str] = Field(default=None, repr=False, description="Porkbun API Key")
    PORKBUN_SECRET_API_KEY: Optional[str] = Field(default=None, repr=False, description="Porkbun Secret API Key")

    # Default DNS Settings
    DEFAULT_NAMESERVERS: List[str] = [
        "ns1.mastertools-dns.com",
        "ns2.mastertools-dns.com"
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        env = (self.APP_ENV or "").strip().lower()
        is_production = env == "production"

        if is_production:
            # 1. DEBUG must be False in production
            if self.DEBUG is True:
                raise ValueError("In production environment, DEBUG must be set to False.")

            # 2. Reject default or common administrative usernames
            username = (self.ADMIN_USERNAME or "").strip().lower()
            if not username or username in {"admin", "administrator", "root", "superuser"}:
                raise ValueError(
                    "In production, default ADMIN_USERNAME ('admin') is prohibited. "
                    "A unique, non-default administrative username must be configured."
                )

            # 3. Reject missing, empty, or known default SECRET_KEY
            if not self.SECRET_KEY or not self.SECRET_KEY.strip():
                raise ValueError("In production, SECRET_KEY is required and cannot be empty.")

            secret = self.SECRET_KEY.strip()
            if secret.lower() in KNOWN_DEFAULT_SECRETS:
                raise ValueError(
                    "In production, SECRET_KEY cannot be a known default or insecure value."
                )
            if len(secret) < 32:
                raise ValueError(
                    "In production, SECRET_KEY must have at least 32 characters of cryptographic entropy."
                )

            # 4. Reject missing, empty, or known default ADMIN_PASSWORD
            if not self.ADMIN_PASSWORD or not self.ADMIN_PASSWORD.strip():
                raise ValueError("In production, ADMIN_PASSWORD is required and cannot be empty.")

            password = self.ADMIN_PASSWORD.strip()
            if password.lower() in KNOWN_DEFAULT_PASSWORDS:
                raise ValueError(
                    "In production, ADMIN_PASSWORD cannot be a known default or insecure value."
                )
            if len(password) < 12:
                raise ValueError(
                    "In production, ADMIN_PASSWORD must be a strong password with at least 12 characters."
                )
        else:
            # Keep development / test configuration usable without manual secret setup
            if not self.SECRET_KEY:
                self.SECRET_KEY = DEV_DEFAULT_SECRET_KEY
            if not self.ADMIN_PASSWORD:
                self.ADMIN_PASSWORD = DEV_DEFAULT_ADMIN_PASSWORD

        return self

    def is_provider_configured(self, provider_name: str) -> bool:
        """Checks if required credentials exist for a given provider."""
        provider = provider_name.lower()
        if provider == "mock":
            return True
        if provider == "godaddy":
            return bool(self.GODADDY_API_KEY and self.GODADDY_API_SECRET)
        if provider == "namecheap":
            return bool(
                self.NAMECHEAP_API_USER
                and self.NAMECHEAP_API_KEY
                and self.NAMECHEAP_CLIENT_IP
            )
        if provider == "porkbun":
            return bool(self.PORKBUN_API_KEY and self.PORKBUN_SECRET_API_KEY)
        return False

    def get_safe_summary(self) -> Dict[str, Any]:
        """
        Returns a sanitized configuration status.
        NEVER returns actual API secrets, passwords, or keys.
        """
        active = self.REGISTRAR_PROVIDER.lower()
        return {
            "app_name": self.APP_NAME,
            "environment": self.APP_ENV,
            "debug": self.DEBUG,
            "free_testing_mode": self.FREE_TESTING_MODE,
            "supported_extensions": self.SUPPORTED_EXTENSIONS,
            "active_provider": active,
            "sandbox_mode": self.REGISTRAR_USE_SANDBOX,
            "is_provider_ready": self.is_provider_configured(active),
            "admin_username_configured": bool(self.ADMIN_USERNAME),
            "secret_key_configured": bool(self.SECRET_KEY),
            "admin_password_configured": bool(self.ADMIN_PASSWORD),
            "supported_providers": ["mock", "godaddy", "namecheap", "porkbun"],
            "configured_providers": [
                p for p in ["mock", "godaddy", "namecheap", "porkbun"]
                if self.is_provider_configured(p)
            ],
        }


settings = Settings()
