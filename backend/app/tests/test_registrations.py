import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.services.registration_service import RegistrationService
from app.models.registration import RegistrationRequestStatus


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path):
    """Sets an isolated temporary SQLite database for each test run."""
    db_file = tmp_path / "test_registrations.db"
    RegistrationService.set_db_path(db_file)
    yield
    # Reset back to default
    from app.services.registration_service import DEFAULT_DB_PATH
    RegistrationService.set_db_path(DEFAULT_DB_PATH)


@pytest.fixture
def client():
    return TestClient(app)


def test_create_registration_request_success(client: TestClient):
    payload = {
        "customer_name": "Tala Adams",
        "customer_email": "tala@domainmaster.gy",
        "domain": "tala.gy",
        "message": "Personal branding and engineering blog",
    }
    response = client.post("/api/registrations/requests", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["request_id"].startswith("REQ-GY-")
    assert data["domain"] == "tala.gy"
    assert data["customer_name"] == "Tala Adams"
    assert data["customer_email"] == "tala@domainmaster.gy"
    assert data["status"] == "pending"
    assert data["status_label"] == "Pending Initial Review"
    assert data["estimated_annual_price"] == 45.0
    assert data["confirmed_price"] is None
    assert "NOT register, hold, or reserve" in data["disclaimer"]


def test_duplicate_pending_request_rejection(client: TestClient):
    payload = {
        "customer_name": "Tala Adams",
        "customer_email": "tala@domainmaster.gy",
        "domain": "tala.gy",
    }
    # First submission succeeds
    res1 = client.post("/api/registrations/requests", json=payload)
    assert res1.status_code == 201
    first_id = res1.json()["request_id"]

    # Second submission for same domain while pending is rejected with 409
    res2 = client.post("/api/registrations/requests", json=payload)
    assert res2.status_code == 409
    error_data = res2.json()["detail"]
    assert error_data["error"] == "REGISTRATION_REQUEST_REJECTED"
    assert first_id in error_data["message"]


def test_reject_invalid_email(client: TestClient):
    payload = {
        "customer_name": "Prem Singh",
        "customer_email": "invalid-email-format",
        "domain": "prem.gy",
    }
    response = client.post("/api/registrations/requests", json=payload)
    assert response.status_code == 400
    assert "Invalid customer email format" in response.json()["detail"]["message"]


def test_reject_non_gy_domain(client: TestClient):
    payload = {
        "customer_name": "Prem Singh",
        "customer_email": "prem@example.gy",
        "domain": "prem.com",
    }
    response = client.post("/api/registrations/requests", json=payload)
    assert response.status_code == 400
    assert "Only .gy domains are supported" in response.json()["detail"]["message"]


def test_reject_invalid_domain_syntax(client: TestClient):
    payload = {
        "customer_name": "Prem Singh",
        "customer_email": "prem@example.gy",
        "domain": "-badname-.gy",
    }
    response = client.post("/api/registrations/requests", json=payload)
    assert response.status_code == 400
    assert "Domain name cannot start or end with a hyphen" in response.json()["detail"]["message"]


def test_get_request_by_id(client: TestClient):
    payload = {
        "customer_name": "Shop Guyana",
        "customer_email": "contact@myshop.gy",
        "domain": "myshop.gy",
    }
    create_res = client.post("/api/registrations/requests", json=payload)
    request_id = create_res.json()["request_id"]

    # Retrieve by ID
    get_res = client.get(f"/api/registrations/requests/{request_id}")
    assert get_res.status_code == 200
    assert get_res.json()["domain"] == "myshop.gy"

    # Non-existent ID returns 404
    missing_res = client.get("/api/registrations/requests/REQ-GY-NOTFOUND")
    assert missing_res.status_code == 404


def test_admin_update_request_status_and_notes(client: TestClient):
    payload = {
        "customer_name": "Cloud Startup",
        "customer_email": "admin@cloud.gy",
        "domain": "cloudstack.gy",
    }
    create_res = client.post("/api/registrations/requests", json=payload)
    request_id = create_res.json()["request_id"]

    # Admin updates to verification_required
    update_payload = {
        "status": "verification_required",
        "admin_notes": "Checking with University of Guyana Registry registrar directory.",
        "confirmed_price": 45.0,
    }
    patch_res = client.patch(f"/api/registrations/requests/{request_id}", json=update_payload)
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["status"] == "verification_required"
    assert updated_data["status_label"] == "Verification Required (.GY Registry)"
    assert updated_data["confirmed_price"] == 45.0
    assert "Checking with University of Guyana Registry" in updated_data["admin_notes"]


def test_list_and_filter_requests(client: TestClient):
    client.post(
        "/api/registrations/requests",
        json={"customer_name": "User 1", "customer_email": "u1@test.gy", "domain": "domain1.gy"},
    )
    client.post(
        "/api/registrations/requests",
        json={"customer_name": "User 2", "customer_email": "u2@test.gy", "domain": "domain2.gy"},
    )

    list_all = client.get("/api/registrations/requests")
    assert list_all.status_code == 200
    assert list_all.json()["total"] == 2

    # Filter by status
    list_filtered = client.get("/api/registrations/requests?status=verified_available")
    assert list_filtered.status_code == 200
    assert list_filtered.json()["total"] == 0
