from pathlib import Path
import pytest
from pydantic import ValidationError
from app.core.config import Settings, DEV_DEFAULT_SECRET_KEY, DEV_DEFAULT_ADMIN_PASSWORD

# Clearly fake test-only constants for CI/test suites (never used in production)
FAKE_PROD_SECRET_KEY = "test_fake_production_secret_key_0123456789abcdef_not_real"
FAKE_PROD_ADMIN_PASSWORD = "test_fake_production_password_strictly_for_tests_12345"
FAKE_PROD_ADMIN_USERNAME = "test_unique_admin_operator"


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
            ADMIN_USERNAME=FAKE_PROD_ADMIN_USERNAME,
            SECRET_KEY=FAKE_PROD_SECRET_KEY,
            ADMIN_PASSWORD=FAKE_PROD_ADMIN_PASSWORD,
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
                SECRET_KEY=FAKE_PROD_SECRET_KEY,
                ADMIN_PASSWORD=FAKE_PROD_ADMIN_PASSWORD,
            )
        assert "default ADMIN_USERNAME ('admin') is prohibited" in str(exc_info.value)


def test_production_rejects_missing_secret_key():
    """In production, missing or empty SECRET_KEY must be rejected."""
    for empty_val in [None, "", "   "]:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                APP_ENV="production",
                DEBUG=False,
                ADMIN_USERNAME=FAKE_PROD_ADMIN_USERNAME,
                SECRET_KEY=empty_val,
                ADMIN_PASSWORD=FAKE_PROD_ADMIN_PASSWORD,
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
                ADMIN_USERNAME=FAKE_PROD_ADMIN_USERNAME,
                SECRET_KEY=weak_sec,
                ADMIN_PASSWORD=FAKE_PROD_ADMIN_PASSWORD,
            )
        assert "cannot be a known default" in str(exc_info.value)


def test_production_rejects_short_secret_key():
    """In production, SECRET_KEY with fewer than 32 characters must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            DEBUG=False,
            ADMIN_USERNAME=FAKE_PROD_ADMIN_USERNAME,
            SECRET_KEY="short-secret-key-12345678",
            ADMIN_PASSWORD=FAKE_PROD_ADMIN_PASSWORD,
        )
    assert "at least 32 characters" in str(exc_info.value)


def test_production_rejects_missing_admin_password():
    """In production, missing or empty ADMIN_PASSWORD must be rejected."""
    for empty_val in [None, "", "   "]:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                APP_ENV="production",
                DEBUG=False,
                ADMIN_USERNAME=FAKE_PROD_ADMIN_USERNAME,
                SECRET_KEY=FAKE_PROD_SECRET_KEY,
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
                ADMIN_USERNAME=FAKE_PROD_ADMIN_USERNAME,
                SECRET_KEY=FAKE_PROD_SECRET_KEY,
                ADMIN_PASSWORD=weak_pwd,
            )
        assert "cannot be a known default" in str(exc_info.value)


def test_production_rejects_short_admin_password():
    """In production, ADMIN_PASSWORD with fewer than 12 characters must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            DEBUG=False,
            ADMIN_USERNAME=FAKE_PROD_ADMIN_USERNAME,
            SECRET_KEY=FAKE_PROD_SECRET_KEY,
            ADMIN_PASSWORD="shortpass1",
        )
    assert "at least 12 characters" in str(exc_info.value)


def test_production_valid_configuration_success():
    """A valid production configuration with strong entropy and custom username succeeds."""
    cfg = Settings(
        APP_ENV="production",
        DEBUG=False,
        ADMIN_USERNAME=FAKE_PROD_ADMIN_USERNAME,
        SECRET_KEY=FAKE_PROD_SECRET_KEY,
        ADMIN_PASSWORD=FAKE_PROD_ADMIN_PASSWORD,
        CORS_ORIGINS=["https://domains.mastertools.gy"],
    )

    assert cfg.APP_ENV == "production"
    assert cfg.DEBUG is False
    assert cfg.ADMIN_USERNAME == FAKE_PROD_ADMIN_USERNAME
    assert cfg.SECRET_KEY == FAKE_PROD_SECRET_KEY
    assert cfg.ADMIN_PASSWORD == FAKE_PROD_ADMIN_PASSWORD
    assert cfg.CORS_ORIGINS == ["https://domains.mastertools.gy"]


def test_secrets_never_logged_or_exposed_in_repr_or_summary():
    """Verifies that secrets are masked with repr=False and safe summary never leaks secret values."""
    cfg = Settings(
        APP_ENV="production",
        DEBUG=False,
        ADMIN_USERNAME=FAKE_PROD_ADMIN_USERNAME,
        SECRET_KEY=FAKE_PROD_SECRET_KEY,
        ADMIN_PASSWORD=FAKE_PROD_ADMIN_PASSWORD,
    )

    # 1. repr check: neither secret should be visible in repr() or str()
    repr_str = repr(cfg)
    assert FAKE_PROD_SECRET_KEY not in repr_str
    assert FAKE_PROD_ADMIN_PASSWORD not in repr_str

    # 2. get_safe_summary check: must only return boolean flags
    summary = cfg.get_safe_summary()
    assert summary["secret_key_configured"] is True
    assert summary["admin_password_configured"] is True
    assert FAKE_PROD_SECRET_KEY not in str(summary)
    assert FAKE_PROD_ADMIN_PASSWORD not in str(summary)


def test_cors_origins_flexibility():
    """Supports both JSON list and comma-separated string formats for CORS_ORIGINS."""
    cfg1 = Settings(CORS_ORIGINS=["https://frontend.gy", "http://localhost:5173"])
    assert cfg1.CORS_ORIGINS == ["https://frontend.gy", "http://localhost:5173"]

    cfg2 = Settings(CORS_ORIGINS="https://frontend.gy, http://localhost:5173")
    assert cfg2.CORS_ORIGINS == ["https://frontend.gy", "http://localhost:5173"]


def test_env_example_contains_no_real_or_default_secrets():
    """
    Verifies that backend/.env.example does not contain hardcoded development defaults,
    real credentials, or populated secrets, and enforces empty placeholders.
    """
    example_path = Path(__file__).resolve().parents[2] / ".env.example"
    assert example_path.exists(), f"Could not find .env.example at {example_path}"

    content = example_path.read_text(encoding="utf-8")

    assigned_vars = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            assigned_vars[k.strip()] = v.strip()

    # 1. SECRET_KEY must be an empty placeholder
    assert assigned_vars.get("SECRET_KEY") == "", "SECRET_KEY in .env.example must be an empty placeholder"

    # 2. ADMIN_PASSWORD must be an empty placeholder
    assert assigned_vars.get("ADMIN_PASSWORD") == "", "ADMIN_PASSWORD in .env.example must be an empty placeholder"

    # 3. ADMIN_USERNAME must not default to 'admin'
    assert assigned_vars.get("ADMIN_USERNAME") != "admin", "ADMIN_USERNAME in .env.example must not default to 'admin'"

    # 4. Known development defaults must not appear in .env.example
    assert DEV_DEFAULT_SECRET_KEY not in content, "DEV_DEFAULT_SECRET_KEY must not appear in .env.example"
    assert DEV_DEFAULT_ADMIN_PASSWORD not in content, "DEV_DEFAULT_ADMIN_PASSWORD must not appear in .env.example"
