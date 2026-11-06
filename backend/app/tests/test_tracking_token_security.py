import hashlib
import secrets
import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.services.registration_service import RegistrationService, DEFAULT_DB_PATH


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path):
    """Sets an isolated temporary SQLite database and resets rate limits for each test."""
    db_file = tmp_path / "test_token_security.db"
    RegistrationService.set_db_path(db_file)
    rate_limiter.reset()
    yield
    RegistrationService.set_db_path(DEFAULT_DB_PATH)
    rate_limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


def get_admin_headers(client: TestClient) -> dict:
    """Helper to authenticate admin and return Bearer Authorization header."""
    res = client.post(
        "/api/admin/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert res.status_code == 200
    token = res.json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. New tokens stored only as SHA-256 hashes at rest
# ============================================================================

def test_new_tokens_stored_only_as_sha256_hashes(client: TestClient):
    """
    Verifies that when a registration request is created:
    - Only SHA-256 hashes are stored in SQLite database rows.
    - Plaintext tracking token is never persisted in SQLite.
    """
    payload = {
        "customer_name": "Devin Security",
        "customer_email": "devin@security.gy",
        "domain": "devin-sec.gy",
        "message": "Security verification request.",
    }
    res = client.post("/api/registrations/requests", json=payload)
    assert res.status_code == 201
    data = res.json()
    req_id = data["request_id"]
    raw_token = data["tracking_token"]

    assert len(raw_token) >= 32
    computed_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest().lower()

    # Query the SQLite database directly
    with RegistrationService._get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM registration_requests WHERE request_id = ?",
            (req_id,),
        )
        row = dict(cursor.fetchone())

    # Verify tracking_token_hash column is a 64-char SHA-256 hex string
    stored_hash = row["tracking_token_hash"]
    assert stored_hash is not None
    assert len(stored_hash) == 64
    assert RegistrationService.is_sha256_hash(stored_hash)
    assert stored_hash == computed_hash

    # Verify tracking_token column is also hashed (never plaintext)
    assert row["tracking_token"] == stored_hash
    assert RegistrationService.is_sha256_hash(row["tracking_token"])

    # Ensure raw plaintext token is nowhere in any column of the row
    for col, val in row.items():
        if val is not None:
            assert raw_token not in str(val), f"Raw token leaked in column '{col}': {val}"


# ============================================================================
# 2. Correct token verifies customer ownership via header
# ============================================================================

def test_customer_verification_with_header(client: TestClient):
    """
    Verifies that providing the correct tracking token via X-Customer-Tracking-Token
    authenticates the customer and returns their submission data while keeping admin notes private.
    """
    payload = {
        "customer_name": "Tala Registered",
        "customer_email": "tala@verified-owner.gy",
        "domain": "tala-owner.gy",
        "message": "Connecting to Vercel and Render.",
    }
    create_res = client.post("/api/registrations/requests", json=payload)
    assert create_res.status_code == 201
    create_data = create_res.json()
    req_id = create_data["request_id"]
    token = create_data["tracking_token"]

    # Lookup with header X-Customer-Tracking-Token
    res = client.get(
        f"/api/registrations/requests/{req_id}",
        headers={"X-Customer-Tracking-Token": token},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["request_id"] == req_id
    assert data["customer_name"] == "Tala Registered"
    assert data["customer_email"] == "tala@verified-owner.gy"
    assert data["message"] == "Connecting to Vercel and Render."
    assert data["domain"] == "tala-owner.gy"
    assert data["status"] == "pending"
    # Admin-only fields must never be exposed to customer
    assert "admin_notes" not in data
    assert "confirmation_reference" not in data


# ============================================================================
# 3. Incorrect token rejected and returns sanitized public response
# ============================================================================

def test_customer_verification_rejects_incorrect_token(client: TestClient):
    """
    Verifies that an incorrect tracking token does not fail abruptly,
    but safely falls back to returning only the sanitized public view.
    """
    payload = {
        "customer_name": "Private Customer",
        "customer_email": "private@confidential.gy",
        "domain": "private-confidential.gy",
        "message": "Confidential corporate plan.",
    }
    create_res = client.post("/api/registrations/requests", json=payload)
    req_id = create_res.json()["request_id"]

    # Provide completely wrong token
    res = client.get(
        f"/api/registrations/requests/{req_id}",
        headers={"X-Customer-Tracking-Token": "invalid-wrong-token-12345"},
    )
    assert res.status_code == 200
    data = res.json()

    # Public fields present
    assert data["request_id"] == req_id
    assert data["domain"] == "private-confidential.gy"
    assert data["status"] == "pending"
    assert "pricing_amount" in data
    assert "disclaimer" in data

    # Customer private fields strictly excluded
    assert "customer_name" not in data
    assert "customer_email" not in data
    assert "message" not in data
    assert "admin_notes" not in data


# ============================================================================
# 4. Query parameter ?token= does not leak customer data
# ============================================================================

def test_query_parameter_token_does_not_leak_customer_data(client: TestClient):
    """
    Verifies that passing a valid token as a URL query parameter (?token=... or ?tracking_token=...)
    is completely ignored and does NOT return customer private data.
    """
    payload = {
        "customer_name": "Url Test Customer",
        "customer_email": "urltest@secure.gy",
        "domain": "url-test-protection.gy",
        "message": "Sensitive notes in message.",
    }
    create_res = client.post("/api/registrations/requests", json=payload)
    req_id = create_res.json()["request_id"]
    token = create_res.json()["tracking_token"]

    # 1. Try ?token=
    res_token_query = client.get(f"/api/registrations/requests/{req_id}?token={token}")
    assert res_token_query.status_code == 200
    data1 = res_token_query.json()
    assert "customer_name" not in data1
    assert "customer_email" not in data1
    assert "message" not in data1

    # 2. Try ?tracking_token=
    res_tt_query = client.get(f"/api/registrations/requests/{req_id}?tracking_token={token}")
    assert res_tt_query.status_code == 200
    data2 = res_tt_query.json()
    assert "customer_name" not in data2
    assert "customer_email" not in data2
    assert "message" not in data2


# ============================================================================
# 5. Legacy plaintext tokens remain valid after migration
# ============================================================================

def test_legacy_plaintext_migration_and_preservation(tmp_path: Path, client: TestClient):
    """
    Simulates a legacy SQLite database where tracking tokens were stored in plaintext.
    Verifies that:
    1. Migration converts plaintext tokens into SHA-256 hashes.
    2. Previously issued plaintext tokens continue to verify successfully.
    """
    legacy_db = tmp_path / "legacy_migration_test.db"
    conn = sqlite3.connect(str(legacy_db))
    conn.execute(
        """
        CREATE TABLE registration_requests (
            request_id TEXT PRIMARY KEY,
            tracking_token TEXT NOT NULL,
            domain TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            message TEXT,
            status TEXT NOT NULL,
            estimated_annual_price REAL NOT NULL,
            confirmed_price REAL,
            currency TEXT NOT NULL DEFAULT 'USD',
            admin_notes TEXT,
            confirmation_reference TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    legacy_raw_token_1 = secrets.token_urlsafe(32)
    legacy_raw_token_2 = secrets.token_urlsafe(32)

    conn.execute(
        """
        INSERT INTO registration_requests (
            request_id, tracking_token, domain, customer_name, customer_email,
            status, estimated_annual_price, currency, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "REQ-GY-LEGACY001",
            legacy_raw_token_1,
            "legacy-one.gy",
            "Legacy Customer One",
            "legacy1@example.gy",
            "pending",
            45.0,
            "USD",
            "2026-11-01T00:00:00Z",
            "2026-11-01T00:00:00Z",
        ),
    )
    conn.execute(
        """
        INSERT INTO registration_requests (
            request_id, tracking_token, domain, customer_name, customer_email,
            status, estimated_annual_price, currency, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "REQ-GY-LEGACY002",
            legacy_raw_token_2,
            "legacy-two.gy",
            "Legacy Customer Two",
            "legacy2@example.gy",
            "verification_required",
            45.0,
            "USD",
            "2026-11-02T00:00:00Z",
            "2026-11-02T00:00:00Z",
        ),
    )
    conn.commit()
    conn.close()

    # Point service to this legacy database (triggers _init_db and migrate_tracking_tokens)
    RegistrationService.set_db_path(legacy_db)

    # 1. Verify rows in database now hold 64-char hashes, not plaintext tokens
    with RegistrationService._get_connection() as c:
        rows = c.execute("SELECT * FROM registration_requests").fetchall()
        for r in rows:
            stored_hash = r["tracking_token_hash"]
            assert stored_hash is not None
            assert len(stored_hash) == 64
            assert RegistrationService.is_sha256_hash(stored_hash)
            assert r["tracking_token"] == stored_hash

    # 2. Verify that customer using legacy_raw_token_1 can still verify ownership
    verified_1 = RegistrationService.get_customer_verified_request("REQ-GY-LEGACY001", legacy_raw_token_1)
    assert verified_1 is not None
    assert verified_1.customer_name == "Legacy Customer One"
    assert verified_1.customer_email == "legacy1@example.gy"

    # 3. Verify via HTTP API with X-Customer-Tracking-Token header
    http_res = client.get(
        "/api/registrations/requests/REQ-GY-LEGACY002",
        headers={"X-Customer-Tracking-Token": legacy_raw_token_2},
    )
    assert http_res.status_code == 200
    http_data = http_res.json()
    assert http_data["customer_name"] == "Legacy Customer Two"
    assert http_data["customer_email"] == "legacy2@example.gy"
    assert http_data["status"] == "verification_required"


# ============================================================================
# 6. Migration is idempotent and safe to run multiple times
# ============================================================================

def test_migration_is_idempotent_and_safe_to_run_multiple_times(tmp_path: Path):
    """
    Verifies that running migrate_tracking_tokens() repeatedly:
    - Modifies 0 rows on subsequent runs.
    - Does not re-hash already-hashed values (no double hashing).
    - Preserves token verification fidelity across runs.
    """
    test_db = tmp_path / "idempotent_migration.db"
    conn = sqlite3.connect(str(test_db))
    conn.execute(
        """
        CREATE TABLE registration_requests (
            request_id TEXT PRIMARY KEY,
            tracking_token TEXT NOT NULL,
            domain TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            status TEXT NOT NULL,
            estimated_annual_price REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    raw_token = secrets.token_urlsafe(32)
    conn.execute(
        """
        INSERT INTO registration_requests (
            request_id, tracking_token, domain, customer_name, customer_email,
            status, estimated_annual_price, currency, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "REQ-GY-IDEMP01",
            raw_token,
            "idemp.gy",
            "Idemp User",
            "idemp@example.gy",
            "pending",
            45.0,
            "USD",
            "2026-11-01T00:00:00Z",
            "2026-11-01T00:00:00Z",
        ),
    )
    conn.commit()
    conn.close()

    RegistrationService.set_db_path(test_db)

    # First migration run: converts 1 legacy record
    # Note: set_db_path already ran it once. Let's inspect database state.
    with RegistrationService._get_connection() as c:
        row = c.execute("SELECT tracking_token_hash FROM registration_requests WHERE request_id = 'REQ-GY-IDEMP01'").fetchone()
        first_hash = row["tracking_token_hash"]

    assert len(first_hash) == 64
    assert RegistrationService.is_sha256_hash(first_hash)

    # Second migration run: should migrate 0 rows
    count_second = RegistrationService.migrate_tracking_tokens()
    assert count_second == 0

    # Third migration run: should also migrate 0 rows
    count_third = RegistrationService.migrate_tracking_tokens()
    assert count_third == 0

    # Hash must remain unchanged (not double-hashed)
    with RegistrationService._get_connection() as c:
        row = c.execute("SELECT tracking_token_hash FROM registration_requests WHERE request_id = 'REQ-GY-IDEMP01'").fetchone()
        final_hash = row["tracking_token_hash"]

    assert final_hash == first_hash

    # Raw token must still verify successfully
    verified = RegistrationService.get_customer_verified_request("REQ-GY-IDEMP01", raw_token)
    assert verified is not None
    assert verified.customer_name == "Idemp User"


# ============================================================================
# 7. Admin list and detail endpoints never contain tracking tokens
# ============================================================================

def test_admin_list_and_detail_endpoints_never_contain_tracking_tokens(client: TestClient):
    """
    Verifies that neither admin list (/api/registrations/requests) nor admin detail
    (/api/admin/registrations/requests/{id}) ever exposes customer tracking tokens or hashes.
    """
    payload = {
        "customer_name": "Admin Privacy Test",
        "customer_email": "privacy@corp.gy",
        "domain": "admin-privacy.gy",
        "message": "Verify admin views do not expose tokens.",
    }
    create_res = client.post("/api/registrations/requests", json=payload)
    assert create_res.status_code == 201
    req_id = create_res.json()["request_id"]
    token = create_res.json()["tracking_token"]

    admin_headers = get_admin_headers(client)

    # 1. Admin list: /api/registrations/requests
    list_res1 = client.get("/api/registrations/requests", headers=admin_headers)
    assert list_res1.status_code == 200
    items1 = list_res1.json()["requests"]
    assert len(items1) >= 1
    for item in items1:
        assert "tracking_token" not in item
        assert "tracking_token_hash" not in item

    # 2. Admin list: /api/admin/registrations/requests
    list_res2 = client.get("/api/admin/registrations/requests", headers=admin_headers)
    assert list_res2.status_code == 200
    items2 = list_res2.json()["requests"]
    for item in items2:
        assert "tracking_token" not in item
        assert "tracking_token_hash" not in item

    # 3. Admin detail: /api/admin/registrations/requests/{id}
    detail_res = client.get(f"/api/admin/registrations/requests/{req_id}", headers=admin_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert "tracking_token" not in detail
    assert "tracking_token_hash" not in detail
    assert detail["customer_name"] == "Admin Privacy Test"
    assert detail["customer_email"] == "privacy@corp.gy"

    # Verify token does not appear anywhere in admin JSON serialization
    detail_text = detail_res.text
    assert token not in detail_text


# ============================================================================
# 8. Creation response returns a usable token only once
# ============================================================================

def test_creation_response_returns_usable_token_only_once(client: TestClient):
    """
    Verifies that the customer tracking token is returned ONLY in the initial creation response
    and is never retrievable again in subsequent lookups (public, verified, or admin).
    """
    payload = {
        "customer_name": "Single Exposure Test",
        "customer_email": "single@exposure.gy",
        "domain": "single-exposure.gy",
    }
    create_res = client.post("/api/registrations/requests", json=payload)
    assert create_res.status_code == 201
    create_data = create_res.json()
    assert "tracking_token" in create_data
    token = create_data["tracking_token"]
    req_id = create_data["request_id"]

    # Subsequent public lookup: tracking_token not present
    pub_res = client.get(f"/api/registrations/requests/{req_id}")
    assert pub_res.status_code == 200
    assert "tracking_token" not in pub_res.json()

    # Subsequent verified lookup (even with valid token): tracking_token not in response body
    verified_res = client.get(
        f"/api/registrations/requests/{req_id}",
        headers={"X-Customer-Tracking-Token": token},
    )
    assert verified_res.status_code == 200
    assert "tracking_token" not in verified_res.json()

    # Subsequent admin lookup: tracking_token not present
    admin_headers = get_admin_headers(client)
    adm_res = client.get(f"/api/admin/registrations/requests/{req_id}", headers=admin_headers)
    assert adm_res.status_code == 200
    assert "tracking_token" not in adm_res.json()


# ============================================================================
# 9. Tracking tokens never appear in URLs or application logs/error messages
# ============================================================================

def test_tracking_tokens_never_appear_in_error_messages(client: TestClient):
    """
    Verifies that invalid requests or errors do not echo tracking tokens back
    in response bodies or headers.
    """
    secret_token = "ultra-secret-tracking-token-998877"

    # 404 for unknown request ID
    not_found_res = client.get(
        "/api/registrations/requests/REQ-GY-NONEXISTENT999",
        headers={"X-Customer-Tracking-Token": secret_token},
    )
    assert not_found_res.status_code == 404
    assert secret_token not in not_found_res.text
    for h_name, h_val in not_found_res.headers.items():
        assert secret_token not in h_val

    # 422 validation error
    bad_res = client.post(
        "/api/registrations/requests",
        json={"invalid_field": "data"},
        headers={"X-Customer-Tracking-Token": secret_token},
    )
    assert bad_res.status_code == 422
    assert secret_token not in bad_res.text
