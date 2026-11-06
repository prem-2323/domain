import concurrent.futures
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.services.registration_service import RegistrationService
from app.services.pricing_service import PricingService


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path):
    """Sets an isolated temporary SQLite database and resets rate limits for each test run."""
    db_file = tmp_path / "test_registrations.db"
    RegistrationService.set_db_path(db_file)
    rate_limiter.reset()
    yield
    from app.services.registration_service import DEFAULT_DB_PATH
    RegistrationService.set_db_path(DEFAULT_DB_PATH)
    rate_limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


def get_admin_headers(client: TestClient) -> dict:
    """Helper to perform admin login and return Authorization headers."""
    res = client.post(
        "/api/admin/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert res.status_code == 200
    token = res.json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. Registration Request Creation & Validation
# ============================================================================

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
    assert "tracking_token" in data
    assert len(data["tracking_token"]) >= 32
    assert data["domain"] == "tala.gy"
    assert data["customer_name"] == "Tala Adams"
    assert data["customer_email"] == "tala@domainmaster.gy"
    assert data["status"] == "pending"
    assert data["status_label"] == "Pending Initial Review"
    assert data["estimated_annual_price"] == 45.0
    assert "NOT register, hold, or reserve" in data["disclaimer"]


def test_request_id_entropy(client: TestClient):
    """Verifies that generated request IDs have at least 128 bits of entropy (32 hex characters)."""
    ids = []
    tokens = []
    for i in range(5):
        payload = {
            "customer_name": f"User {i}",
            "customer_email": f"user{i}@test.gy",
            "domain": f"entropy-domain-{i}.gy",
        }
        res = client.post("/api/registrations/requests", json=payload)
        assert res.status_code == 201
        data = res.json()
        req_id = data["request_id"]
        # Prefix is REQ-GY- (7 chars), followed by at least 32 hex chars (128 bits = 16 bytes = 32 hex chars)
        assert req_id.startswith("REQ-GY-")
        hex_part = req_id.replace("REQ-GY-", "")
        assert len(hex_part) >= 32
        int(hex_part, 16)  # Verify valid hex
        ids.append(req_id)
        tokens.append(data["tracking_token"])

    # All generated IDs and tokens must be unique
    assert len(set(ids)) == 5
    assert len(set(tokens)) == 5


def test_reject_invalid_email(client: TestClient):
    invalid_emails = [
        "plainaddress",
        "missing@domain",
        "@missinguser.com",
        "spaces in@domain.com",
    ]
    for email in invalid_emails:
        payload = {
            "customer_name": "Prem Singh",
            "customer_email": email,
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
    bad_domains = [
        "-badname-.gy",
        "badname-.gy",
        "-badname.gy",
        "bad_domain.gy",
        "bad..gy",
        "a" * 64 + ".gy",
    ]
    for dom in bad_domains:
        payload = {
            "customer_name": "Prem Singh",
            "customer_email": "prem@example.gy",
            "domain": dom,
        }
        response = client.post("/api/registrations/requests", json=payload)
        assert response.status_code == 400


# ============================================================================
# 2. Duplicate Request Protection & Concurrency
# ============================================================================

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

    # Second submission for same domain while active is rejected with 409
    res2 = client.post("/api/registrations/requests", json=payload)
    assert res2.status_code == 409
    error_data = res2.json()["detail"]
    assert error_data["error"] == "REGISTRATION_REQUEST_REJECTED"
    assert first_id in error_data["message"]


def test_duplicate_domain_normalization_rejection(client: TestClient):
    # Normalized matching: uppercase and surrounding whitespace
    res1 = client.post(
        "/api/registrations/requests",
        json={"customer_name": "Tala", "customer_email": "tala@test.gy", "domain": "brand.gy"},
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/api/registrations/requests",
        json={"customer_name": "Tala", "customer_email": "tala@test.gy", "domain": "  BRAND.GY  "},
    )
    assert res2.status_code == 409


def test_concurrent_duplicate_submission_atomic_protection(client: TestClient):
    """Verifies that under concurrent attempts, exactly one succeeds and others return 409."""
    domain = "concurrent-target.gy"
    payload = {
        "customer_name": "Concurrent User",
        "customer_email": "concurrent@test.gy",
        "domain": domain,
    }

    def submit():
        c = TestClient(app)
        return c.post("/api/registrations/requests", json=payload)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(submit) for _ in range(5)]
        results = [f.result() for f in futures]

    statuses = [r.status_code for r in results]
    assert statuses.count(201) == 1
    assert statuses.count(409) == 4


def test_non_active_request_allows_new_request(client: TestClient):
    """When a prior request is rejected or unavailable, a new request for the domain is allowed."""
    payload = {
        "customer_name": "Buyer 1",
        "customer_email": "b1@test.gy",
        "domain": "reopen-domain.gy",
    }
    res1 = client.post("/api/registrations/requests", json=payload)
    assert res1.status_code == 201
    req_id = res1.json()["request_id"]

    # Admin rejects the request
    headers = get_admin_headers(client)
    patch_res = client.patch(
        f"/api/registrations/requests/{req_id}",
        json={"status": "rejected", "admin_notes": "Domain reserved by government policy."},
        headers=headers,
    )
    assert patch_res.status_code == 200

    # A new request for the same domain can now be submitted
    res2 = client.post("/api/registrations/requests", json=payload)
    assert res2.status_code == 201


# ============================================================================
# 3. Customer Privacy & Public Lookup Sanitization
# ============================================================================

def test_public_tracking_privacy_protection(client: TestClient):
    """Ensures public callers NEVER receive customer email, name, message, or admin notes."""
    payload = {
        "customer_name": "Secret Customer",
        "customer_email": "secret@confidential.gy",
        "domain": "private-brand.gy",
        "message": "Do not disclose this strategic product launch.",
    }
    create_res = client.post("/api/registrations/requests", json=payload)
    req_id = create_res.json()["request_id"]

    # Public lookup without tracking token
    public_res = client.get(f"/api/registrations/requests/{req_id}")
    assert public_res.status_code == 200
    pub_data = public_res.json()

    # Verify zero private customer data is leaked
    assert "customer_name" not in pub_data
    assert "customer_email" not in pub_data
    assert "message" not in pub_data
    assert "admin_notes" not in pub_data
    assert "confirmation_reference" not in pub_data

    # Verify public fields are present
    assert pub_data["request_id"] == req_id
    assert pub_data["domain"] == "private-brand.gy"
    assert pub_data["status"] == "pending"
    assert pub_data["pricing_type"] == "estimated"
    assert pub_data["pricing_amount"] == 45.0
    assert "disclaimer" in pub_data


def test_customer_tracking_with_token(client: TestClient):
    """With the valid private customer tracking token in header, submission details are returned without admin notes."""
    payload = {
        "customer_name": "Alice Verified",
        "customer_email": "alice@verified.gy",
        "domain": "alice-brand.gy",
        "message": "Need Cloudflare DNS delegation.",
    }
    create_res = client.post("/api/registrations/requests", json=payload)
    req_id = create_res.json()["request_id"]
    token = create_res.json()["tracking_token"]

    # 1. Lookup with header X-Customer-Tracking-Token
    verified_res = client.get(
        f"/api/registrations/requests/{req_id}",
        headers={"X-Customer-Tracking-Token": token},
    )
    assert verified_res.status_code == 200
    v_data = verified_res.json()

    assert v_data["customer_name"] == "Alice Verified"
    assert v_data["customer_email"] == "alice@verified.gy"
    assert v_data["message"] == "Need Cloudflare DNS delegation."
    # Admin internal notes must still remain private
    assert "admin_notes" not in v_data

    # 2. Token in query parameter is ignored (not accepted in URLs)
    query_res = client.get(f"/api/registrations/requests/{req_id}?token={token}")
    assert query_res.status_code == 200
    q_data = query_res.json()
    assert "customer_name" not in q_data
    assert "customer_email" not in q_data


def test_customer_tracking_with_invalid_token_falls_back_to_public(client: TestClient):
    """An invalid tracking token safely returns the public sanitized view with no data leaked."""
    payload = {
        "customer_name": "Bob Protected",
        "customer_email": "bob@protected.gy",
        "domain": "bob-brand.gy",
    }
    create_res = client.post("/api/registrations/requests", json=payload)
    req_id = create_res.json()["request_id"]

    res = client.get(
        f"/api/registrations/requests/{req_id}",
        headers={"X-Customer-Tracking-Token": "invalid-fake-token"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "customer_name" not in data
    assert "customer_email" not in data


# ============================================================================
# 4. Admin Authentication, Authorization & Session Management
# ============================================================================

def test_unauthenticated_admin_endpoints_return_401(client: TestClient):
    # Unauthenticated GET list
    res_list = client.get("/api/registrations/requests")
    assert res_list.status_code == 401
    assert "detail" in res_list.json()

    # Unauthenticated PATCH
    res_patch = client.patch(
        "/api/registrations/requests/REQ-GY-12345",
        json={"status": "verification_required"},
    )
    assert res_patch.status_code == 401

    # Unauthenticated admin me
    res_me = client.get("/api/admin/me")
    assert res_me.status_code == 401

    # Unauthenticated logout
    res_logout = client.post("/api/admin/logout")
    assert res_logout.status_code == 401


def test_admin_login_invalid_credentials(client: TestClient):
    res = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": "WrongPassword123!"},
    )
    assert res.status_code == 401
    assert "Invalid administrator" in res.json()["detail"]["message"]


def test_admin_login_logout_lifecycle(client: TestClient):
    # 1. Login successfully
    login_res = client.post(
        "/api/admin/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert login_res.status_code == 200
    token = login_res.json()["session_token"]
    assert len(token) >= 32

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Check /api/admin/me
    me_res = client.get("/api/admin/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["authenticated"] is True
    assert me_res.json()["username"] == settings.ADMIN_USERNAME

    # 3. Access protected list
    list_res = client.get("/api/registrations/requests", headers=headers)
    assert list_res.status_code == 200

    # 4. Logout
    logout_res = client.post("/api/admin/logout", headers=headers)
    assert logout_res.status_code == 200

    # 5. Token is now revoked; subsequent request returns 401
    after_res = client.get("/api/registrations/requests", headers=headers)
    assert after_res.status_code == 401


# ============================================================================
# 5. Status Workflow & Integrity Protection
# ============================================================================

def test_admin_update_status_and_notes(client: TestClient):
    create_res = client.post(
        "/api/registrations/requests",
        json={"customer_name": "Tech Corp", "customer_email": "tech@corp.gy", "domain": "techcorp.gy"},
    )
    req_id = create_res.json()["request_id"]

    headers = get_admin_headers(client)

    # Transition to verification_required
    patch_res = client.patch(
        f"/api/registrations/requests/{req_id}",
        json={
            "status": "verification_required",
            "admin_notes": "Contacted University of Guyana Registry registrar.",
            "confirmed_price": 45.0,
        },
        headers=headers,
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["status"] == "verification_required"
    assert data["confirmed_price"] == 45.0
    assert "Contacted University of Guyana" in data["admin_notes"]


def test_registered_status_requires_reference_and_notes(client: TestClient):
    """Setting status to 'registered' mandates both reference (>= 3 chars) and notes (>= 10 chars)."""
    create_res = client.post(
        "/api/registrations/requests",
        json={"customer_name": "Official Corp", "customer_email": "corp@gy.gy", "domain": "official.gy"},
    )
    req_id = create_res.json()["request_id"]
    headers = get_admin_headers(client)

    # 1. Attempt to register without confirmation reference -> rejected with 422
    res_no_ref = client.patch(
        f"/api/registrations/requests/{req_id}",
        json={
            "status": "registered",
            "admin_notes": "Registration recorded in registry.",
        },
        headers=headers,
    )
    assert res_no_ref.status_code == 422
    assert "confirmation reference" in res_no_ref.json()["detail"]["message"].lower()

    # 2. Attempt to register without adequate notes -> rejected with 422
    res_no_notes = client.patch(
        f"/api/registrations/requests/{req_id}",
        json={
            "status": "registered",
            "confirmation_reference": "REG-GY-ACC-9921",
            "admin_notes": "short",
        },
        headers=headers,
    )
    assert res_no_notes.status_code == 422
    assert "confirmation note" in res_no_notes.json()["detail"]["message"].lower()

    # 3. Successful registration with required evidence
    res_valid = client.patch(
        f"/api/registrations/requests/{req_id}",
        json={
            "status": "registered",
            "confirmation_reference": "REG-GY-ACC-9921",
            "admin_notes": "Confirmed recorded with University of Guyana Registry by accredited partner.",
            "confirmed_price": 45.0,
        },
        headers=headers,
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["status"] == "registered"
    assert res_valid.json()["confirmation_reference"] == "REG-GY-ACC-9921"


# ============================================================================
# 6. SQLite Database Persistence
# ============================================================================

def test_sqlite_persistence_across_connection_reopen(client: TestClient, tmp_path: Path):
    db_file = tmp_path / "persistent_test.db"
    RegistrationService.set_db_path(db_file)

    payload = {
        "customer_name": "Persistent User",
        "customer_email": "persist@example.gy",
        "domain": "persist.gy",
    }
    create_res = client.post("/api/registrations/requests", json=payload)
    assert create_res.status_code == 201
    req_id = create_res.json()["request_id"]

    # Simulate process reload / connection reopen
    RegistrationService.set_db_path(db_file)

    headers = get_admin_headers(client)
    get_res = client.get("/api/registrations/requests", headers=headers)
    assert get_res.status_code == 200
    requests = get_res.json()["requests"]
    assert any(r["request_id"] == req_id and r["domain"] == "persist.gy" for r in requests)


# ============================================================================
# 7. Rate Limiting & Request Size Limits
# ============================================================================

def test_rate_limiting_exceeded(client: TestClient):
    """Submitting more requests than RATE_LIMIT_CREATE_PER_MINUTE from the same IP returns HTTP 429."""
    rate_limiter.reset()
    limit = settings.RATE_LIMIT_CREATE_PER_MINUTE

    for i in range(limit):
        res = client.post(
            "/api/registrations/requests",
            json={"customer_name": "Rate User", "customer_email": "rate@test.gy", "domain": f"ratelimit-{i}.gy"},
        )
        assert res.status_code == 201

    # Request number limit + 1 must be blocked
    blocked_res = client.post(
        "/api/registrations/requests",
        json={"customer_name": "Rate User", "customer_email": "rate@test.gy", "domain": "ratelimit-extra.gy"},
    )
    assert blocked_res.status_code == 429
    assert "Retry-After" in blocked_res.headers
    assert "Too many requests" in blocked_res.json()["detail"]["message"]


def test_request_size_limit_rejection(client: TestClient):
    """Payloads exceeding MAX_REQUEST_BODY_BYTES (64 KB) are rejected with HTTP 413."""
    oversized_message = "X" * (settings.MAX_REQUEST_BODY_BYTES + 1024)
    payload = {
        "customer_name": "Giant Payload",
        "customer_email": "giant@test.gy",
        "domain": "giant.gy",
        "message": oversized_message,
    }
    res = client.post("/api/registrations/requests", json=payload)
    assert res.status_code == 413
    assert "exceeds maximum allowed size" in res.json()["detail"]["message"]


# ============================================================================
# 8. Pricing Transparency
# ============================================================================

def test_pricing_service_estimate_labeling():
    from app.models.domain import DomainAvailability
    price_info = PricingService.get_pricing(name="tala", extension=".gy", availability=DomainAvailability.AVAILABLE)
    assert price_info.registration_price == 45.0
    assert price_info.renewal_price == 45.0
    assert price_info.is_mock is True
    assert "estimate" in price_info.pricing_note.lower() or "estimated" in price_info.pricing_note.lower()
