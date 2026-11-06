import pytest
from pydantic import ValidationError
from app.core.config import Settings, DEV_DEFAULT_SECRET_KEY, DEV_DEFAULT_ADMIN_PASSWORD


def test_development_defaults_usable():
    """Development environment must remain usable with secure defaults without requiring manual .env setup."""
    cfg = Settings(APP_ENV="development")
    assert cfg.APP_ENV == "development"
    assert cfg.DEBUG is True
    assert cfg.ADMIN_USERNAME == "admin"
    assert cfg.SECRET_KEY == DEV_DEFAULT_SECRET_KEY
    assert cfg.ADMIN_PASSWORD == DEV_DEFAULT_ADMIN_PASSWORD


def test_production_rejects_debug_true():
    """In production, DEBUG=True must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            DEBUG=True,
            ADMIN_USERNAME="secure_admin_ops",
            SECRET_KEY="98301c25c9a5ffbc00f89722b91c389cf7cf4e119c3650a4a7c4414c70c76313",
            ADMIN_PASSWORD="q40T_S5k9IxL3TLsbFSeyX3iTPh8j95QwW-C5XsQvw8",
        )
    assert "DEBUG must be set to False" in str(exc_info.value)


def test_production_rejects_default_admin_username():
    """In production, default ADMIN_USERNAME ('admin') must be rejected."""
    invalid_usernames = ["admin", "ADMIN", "  admin  ", "administrator", "root", "superuser"]
    for user in invalid_usernames:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                APP_ENV="production",
                DEBUG=False,
                ADMIN_USERNAME=user,
                SECRET_KEY="98301c25c9a5ffbc00f89722b91c389cf7cf4e119c3650a4a7c4414c70c76313",
                ADMIN_PASSWORD="q40T_S5k9IxL3TLsbFSeyX3iTPh8j95QwW-C5XsQvw8",
            )
        assert "default ADMIN_USERNAME ('admin') is prohibited" in str(exc_info.value)


def test_production_rejects_missing_secret_key():
    """In production, missing or empty SECRET_KEY must be rejected."""
    for empty_val in [None, "", "   "]:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                APP_ENV="production",
                DEBUG=False,
                ADMIN_USERNAME="secure_admin_ops",
                SECRET_KEY=empty_val,
                ADMIN_PASSWORD="q40T_S5k9IxL3TLsbFSeyX3iTPh8j95QwW-C5XsQvw8",
            )
        assert "SECRET_KEY is required" in str(exc_info.value)


def test_production_rejects_known_default_secret_key():
    """In production, known default or weak SECRET_KEY values must be rejected."""
    weak_secrets = [
        DEV_DEFAULT_SECRET_KEY,
        "mastertools-domains-secret-admin-session-key-2026",
        "secret",
        "changeme",
        "your_secret_key",
        "your_secret_key_here",
    ]
    for weak_sec in weak_secrets:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                APP_ENV="production",
                DEBUG=False,
                ADMIN_USERNAME="secure_admin_ops",
                SECRET_KEY=weak_sec,
                ADMIN_PASSWORD="q40T_S5k9IxL3TLsbFSeyX3iTPh8j95QwW-C5XsQvw8",
            )
        assert "cannot be a known default" in str(exc_info.value)


def test_production_rejects_short_secret_key():
    """In production, SECRET_KEY with fewer than 32 characters must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            DEBUG=False,
            ADMIN_USERNAME="secure_admin_ops",
            SECRET_KEY="short-secret-key-12345678",
            ADMIN_PASSWORD="q40T_S5k9IxL3TLsbFSeyX3iTPh8j95QwW-C5XsQvw8",
        )
    assert "at least 32 characters" in str(exc_info.value)


def test_production_rejects_missing_admin_password():
    """In production, missing or empty ADMIN_PASSWORD must be rejected."""
    for empty_val in [None, "", "   "]:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                APP_ENV="production",
                DEBUG=False,
                ADMIN_USERNAME="secure_admin_ops",
                SECRET_KEY="98301c25c9a5ffbc00f89722b91c389cf7cf4e119c3650a4a7c4414c70c76313",
                ADMIN_PASSWORD=empty_val,
            )
        assert "ADMIN_PASSWORD is required" in str(exc_info.value)


def test_production_rejects_known_default_admin_password():
    """In production, known default or weak ADMIN_PASSWORD values must be rejected."""
    weak_passwords = [
        DEV_DEFAULT_ADMIN_PASSWORD,
        "MasterToolsGy2026!Admin",
        "admin",
        "password",
        "changeme",
        "12345678",
    ]
    for weak_pwd in weak_passwords:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                APP_ENV="production",
                DEBUG=False,
                ADMIN_USERNAME="secure_admin_ops",
                SECRET_KEY="98301c25c9a5ffbc00f89722b91c389cf7cf4e119c3650a4a7c4414c70c76313",
                ADMIN_PASSWORD=weak_pwd,
            )
        assert "cannot be a known default" in str(exc_info.value)


def test_production_rejects_short_admin_password():
    """In production, ADMIN_PASSWORD with fewer than 12 characters must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            DEBUG=False,
            ADMIN_USERNAME="secure_admin_ops",
            SECRET_KEY="98301c25c9a5ffbc00f89722b91c389cf7cf4e119c3650a4a7c4414c70c76313",
            ADMIN_PASSWORD="shortpass1",
        )
    assert "at least 12 characters" in str(exc_info.value)


def test_production_valid_configuration_success():
    """A valid production configuration with strong entropy and custom username succeeds."""
    prod_secret = "98301c25c9a5ffbc00f89722b91c389cf7cf4e119c3650a4a7c4414c70c76313"
    prod_password = "q40T_S5k9IxL3TLsbFSeyX3iTPh8j95QwW-C5XsQvw8"
    prod_username = "gy_admin_ops_2026"

    cfg = Settings(
        APP_ENV="production",
        DEBUG=False,
        ADMIN_USERNAME=prod_username,
        SECRET_KEY=prod_secret,
        ADMIN_PASSWORD=prod_password,
        CORS_ORIGINS=["https://domains.mastertools.gy"],
    )

    assert cfg.APP_ENV == "production"
    assert cfg.DEBUG is False
    assert cfg.ADMIN_USERNAME == prod_username
    assert cfg.SECRET_KEY == prod_secret
    assert cfg.ADMIN_PASSWORD == prod_password
    assert cfg.CORS_ORIGINS == ["https://domains.mastertools.gy"]


def test_secrets_never_logged_or_exposed_in_repr_or_summary():
    """Verifies that secrets are masked with repr=False and safe summary never leaks secret values."""
    prod_secret = "98301c25c9a5ffbc00f89722b91c389cf7cf4e119c3650a4a7c4414c70c76313"
    prod_password = "q40T_S5k9IxL3TLsbFSeyX3iTPh8j95QwW-C5XsQvw8"

    cfg = Settings(
        APP_ENV="production",
        DEBUG=False,
        ADMIN_USERNAME="gy_admin_ops_2026",
        SECRET_KEY=prod_secret,
        ADMIN_PASSWORD=prod_password,
    )

    # 1. repr check: neither secret should be visible in repr() or str()
    repr_str = repr(cfg)
    assert prod_secret not in repr_str
    assert prod_password not in repr_str

    # 2. get_safe_summary check: must only return boolean flags
    summary = cfg.get_safe_summary()
    assert summary["secret_key_configured"] is True
    assert summary["admin_password_configured"] is True
    assert prod_secret not in str(summary)
    assert prod_password not in str(summary)


def test_cors_origins_flexibility():
    """Supports both JSON list and comma-separated string formats for CORS_ORIGINS."""
    cfg1 = Settings(CORS_ORIGINS=["https://frontend.gy", "http://localhost:5173"])
    assert cfg1.CORS_ORIGINS == ["https://frontend.gy", "http://localhost:5173"]

    cfg2 = Settings(CORS_ORIGINS="https://frontend.gy, http://localhost:5173")
    assert cfg2.CORS_ORIGINS == ["https://frontend.gy", "http://localhost:5173"]
