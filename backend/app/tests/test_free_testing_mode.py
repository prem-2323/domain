import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.registration_service import RegistrationService, DEFAULT_DB_PATH
from app.core.rate_limiter import rate_limiter


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path):
    db_file = tmp_path / "test_free_testing.db"
    RegistrationService.set_db_path(db_file)
    rate_limiter.reset()
    yield
    RegistrationService.set_db_path(DEFAULT_DB_PATH)
    rate_limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


def test_health_reports_free_testing_mode(client: TestClient):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["free_testing_mode"] is True
    assert ".com" in data["supported_extensions"]
    assert ".gy" in data["supported_extensions"]
    assert ".in" in data["supported_extensions"]


def test_domain_search_multi_tld_and_free_pricing(client: TestClient):
    res = client.get("/api/domains/search?name=mastertest")
    assert res.status_code == 200
    data = res.json()

    assert data["is_valid"] is True
    assert data["exact_match"] is not None
    assert data["exact_match"]["price"]["registration_price"] == 0.0
    assert data["exact_match"]["price"]["renewal_price"] == 0.0
    assert "FREE TESTING MODE" in data["disclaimer"]
    assert "FREE TESTING MODE" in data["exact_match"]["price"]["pricing_note"]

    # Verify suggestions include multiple extensions
    found_exts = {s["extension"] for s in data["suggestions"]}
    assert any(ext in found_exts for ext in [".com", ".in", ".org", ".net", ".gy"])


def test_domain_search_explicit_tld(client: TestClient):
    res = client.get("/api/domains/search?name=myshop.com")
    assert res.status_code == 200
    data = res.json()
    assert data["exact_match"]["domain"] == "myshop.com"
    assert data["exact_match"]["extension"] == ".com"
    assert data["exact_match"]["price"]["registration_price"] == 0.0


def test_registration_request_multi_tld_free_pricing(client: TestClient):
    for domain in ["myportfolio.com", "developer.in", "startup.org", "network.net", "identity.gy"]:
        payload = {
            "customer_name": "Test User",
            "customer_email": "tester@example.com",
            "domain": domain,
        }
        res = client.post("/api/registrations/requests", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["domain"] == domain
        assert data["estimated_annual_price"] == 0.0
        assert data["pricing_status"] == "free_testing"
        assert "FREE TESTING MODE" in data["disclaimer"]


def test_extensions_endpoint_catalog(client: TestClient):
    res = client.get("/api/domains/extensions")
    assert res.status_code == 200
    data = res.json()
    assert ".com" in data["extensions"]
    assert ".gy" in data["extensions"]
    assert ".in" in data["extensions"]
    assert len(data["catalog"]) >= 5
