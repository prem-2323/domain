from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Centralized configuration for MasterTools Domains backend.
    Loads from environment variables or .env file.
    API keys and secrets are strictly retained server-side.
    """

    # Environment & Server
    APP_ENV: str = Field(default="development", description="development | staging | production")
    APP_NAME: str = "MasterTools Domains API"
    DEBUG: bool = True
    CORS_ORIGINS: List[str] = ["*"]

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
    NAMECHEAP_API_USER: Optional[str] = Field(default=None, description="Namecheap API username")
    NAMECHEAP_API_KEY: Optional[str] = Field(default=None, description="Namecheap API key")
    NAMECHEAP_USERNAME: Optional[str] = Field(default=None, description="Namecheap account username")
    NAMECHEAP_CLIENT_IP: Optional[str] = Field(default=None, description="Whitelisted client IP address")

    # GoDaddy Credentials (Required only when REGISTRAR_PROVIDER == 'godaddy')
    GODADDY_API_KEY: Optional[str] = Field(default=None, description="GoDaddy API Key")
    GODADDY_API_SECRET: Optional[str] = Field(default=None, description="GoDaddy API Secret")

    # Porkbun Credentials (Optional)
    PORKBUN_API_KEY: Optional[str] = Field(default=None, description="Porkbun API Key")
    PORKBUN_SECRET_API_KEY: Optional[str] = Field(default=None, description="Porkbun Secret API Key")

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
        NEVER returns actual API secrets or keys.
        """
        active = self.REGISTRAR_PROVIDER.lower()
        return {
            "app_name": self.APP_NAME,
            "environment": self.APP_ENV,
            "active_provider": active,
            "sandbox_mode": self.REGISTRAR_USE_SANDBOX,
            "is_provider_ready": self.is_provider_configured(active),
            "supported_providers": ["mock", "godaddy", "namecheap", "porkbun"],
            "configured_providers": [
                p for p in ["mock", "godaddy", "namecheap", "porkbun"]
                if self.is_provider_configured(p)
            ],
        }


settings = Settings()
