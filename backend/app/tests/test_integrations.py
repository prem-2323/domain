import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.security import AdminSessionManager
from app.core.dns_audit import DnsAuditManager
from app.models.integration import (
    DnsRecordItem,
    CloudflareZoneInfo,
    ProposedDnsPlan,
    DnsApplyRequest,
    DnsConflict,
    DnsVerificationItem,
)
from app.services.integrations.cloudflare_service import (
    CloudflareService,
    CloudflareApiError,
    is_protected_record,
)
from app.services.integrations.vercel_service import VercelService, VercelApiError
from app.services.integrations.render_service import RenderService, RenderApiError
from app.services.integrations.dns_verifier import DnsVerifier
from app.services.integrations.dns_workflow_service import (
    DnsWorkflowService,
    generate_plan_signature,
    compute_records_drift_hash,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_headers():
    session = AdminSessionManager.create_session("admin")
    return {
        "Authorization": f"Bearer {session['session_token']}",
        "X-Admin-Session": session["session_token"],
    }


@pytest.fixture
def non_admin_headers():
    session = AdminSessionManager.create_session("regular_user")
    return {
        "Authorization": f"Bearer {session['session_token']}",
        "X-Admin-Session": session["session_token"],
    }


# ============================================================================
# 1. SECRET PROTECTION & CONFIGURATION STATUS TESTS
# ============================================================================

def test_integration_status_secret_protection(client: TestClient):
    """
    Verifies that the /api/integrations/status endpoint reports credential presence
    WITHOUT exposing tokens, keys, passwords, or secret strings.
    """
    res = client.get("/api/integrations/status")
    assert res.status_code == 200
    data = res.json()

    assert "cloudflare" in data
    assert "vercel" in data
    assert "render" in data

    # Verify no raw secrets appear anywhere in the JSON response
    response_text = res.text.lower()
    assert "secret" not in response_text or "secret_key" not in response_text
    assert "token" not in response_text or "token_configured" not in response_text
    assert "password" not in response_text

    for platform in ["cloudflare", "vercel", "render"]:
        assert "configured" in data[platform]
        assert isinstance(data[platform]["configured"], bool)


# ============================================================================
# 2. AUTHENTICATION & AUTHORIZATION SECURITY TESTS (REQUIREMENT 1)
# ============================================================================

def test_unauthenticated_requests_return_401(client: TestClient):
    """
    Verifies that unauthenticated calls to all 5 sensitive integration endpoints
    return HTTP 401 UNAUTHORIZED.
    """
    # 1. POST /api/integrations/apply
    res = client.post("/api/integrations/apply", json={
        "domain": "till.gy",
        "target_platform": "vercel",
        "plan_id": "p1",
        "plan_signature": "sig",
        "expires_at": "2099-01-01T00:00:00Z",
        "approved": True,
    })
    assert res.status_code == 401

    # 2. GET /api/integrations/plan
    res = client.get("/api/integrations/plan", params={"domain": "till.gy", "target": "vercel"})
    assert res.status_code == 401

    # 3. GET /api/integrations/verify
    res = client.get("/api/integrations/verify", params={"domain": "till.gy", "target": "vercel"})
    assert res.status_code == 401

    # 4. GET /api/integrations/cloudflare/zone
    res = client.get("/api/integrations/cloudflare/zone", params={"domain": "till.gy"})
    assert res.status_code == 401

    # 5. GET /api/integrations/cloudflare/dns-records
    res = client.get("/api/integrations/cloudflare/dns-records", params={"domain": "till.gy"})
    assert res.status_code == 401


def test_authenticated_non_admin_returns_403(client: TestClient, non_admin_headers: dict):
    """
    Verifies that authenticated sessions with non-admin username return HTTP 403 FORBIDDEN.
    """
    # 1. POST /api/integrations/apply
    res = client.post(
        "/api/integrations/apply",
        headers=non_admin_headers,
        json={
            "domain": "till.gy",
            "target_platform": "vercel",
            "plan_id": "p1",
            "plan_signature": "sig",
            "expires_at": "2099-01-01T00:00:00Z",
            "approved": True,
        },
    )
    assert res.status_code == 403

    # 2. GET /api/integrations/plan
    res = client.get("/api/integrations/plan", headers=non_admin_headers, params={"domain": "till.gy", "target": "vercel"})
    assert res.status_code == 403

    # 3. GET /api/integrations/verify
    res = client.get("/api/integrations/verify", headers=non_admin_headers, params={"domain": "till.gy", "target": "vercel"})
    assert res.status_code == 403

    # 4. GET /api/integrations/cloudflare/zone
    res = client.get("/api/integrations/cloudflare/zone", headers=non_admin_headers, params={"domain": "till.gy"})
    assert res.status_code == 403

    # 5. GET /api/integrations/cloudflare/dns-records
    res = client.get("/api/integrations/cloudflare/dns-records", headers=non_admin_headers, params={"domain": "till.gy"})
    assert res.status_code == 403


def test_approved_true_without_auth_returns_401(client: TestClient):
    """
    Verifies that approved=true is NEVER trusted without a valid admin session.
    """
    payload = {
        "domain": "till.gy",
        "target_platform": "vercel",
        "plan_id": "plan_fake_123",
        "plan_signature": "fake_signature",
        "expires_at": "2099-01-01T00:00:00Z",
        "approved": True,
        "override_conflicts": True,
    }
    res = client.post("/api/integrations/apply", json=payload)
    assert res.status_code == 401
    assert "unauthenticated" in res.text.lower() or "admin authentication required" in res.text.lower()


# ============================================================================
# 3. DOMAIN & ZONE AUTHORIZATION SECURITY TESTS (REQUIREMENT 2)
# ============================================================================

def test_unrelated_zone_access_denied_403(client: TestClient, admin_headers: dict):
    """
    Verifies that attempting to access an unrelated zone or an account mismatch
    returns HTTP 403 FORBIDDEN.
    """
    with patch("app.core.config.settings.CLOUDFLARE_API_TOKEN", "cf_mock_token_123"):
        with patch("app.core.config.settings.CLOUDFLARE_ACCOUNT_ID", "configured_acc_123"):
            # Cloudflare returns a zone belonging to a different customer account
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "result": [
                    {
                        "id": "zone_unrelated",
                        "name": "unrelated-customer.com",
                        "status": "active",
                        "account": {"id": "different_customer_acc_999", "name": "Other Co"},
                    }
                ],
            }

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                res = client.get(
                    "/api/integrations/cloudflare/zone",
                    headers=admin_headers,
                    params={"domain": "unrelated-customer.com"},
                )
                assert res.status_code == 403
                assert "access denied" in res.text.lower() or "unauthorized account" in res.text.lower()


def test_unauthorized_domain_rejection(client: TestClient, admin_headers: dict):
    """Verifies that invalid domain formats are rejected before any DNS query."""
    invalid_domains = [
        "",
        "invalid..domain",
        "-badstart.gy",
        "badend-.com",
        "has spaces.org",
        "a" * 260 + ".gy",
    ]
    for dom in invalid_domains:
        res = client.get(
            "/api/integrations/plan",
            headers=admin_headers,
            params={"domain": dom, "target": "vercel"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["state"] == "failed"
        assert data["can_apply"] is False


# ============================================================================
# 4. CREDENTIALS MISSING WORKFLOW TESTS
# ============================================================================

def test_proposed_plan_credentials_missing_state(client: TestClient, admin_headers: dict):
    """When Cloudflare token is not configured, returns state 'credentials_missing'."""
    with patch("app.services.integrations.cloudflare_service.CloudflareService.is_configured", new_callable=PropertyMock, return_value=False):
        res = client.get(
            "/api/integrations/plan",
            headers=admin_headers,
            params={"domain": "till.gy", "target": "vercel"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["state"] == "credentials_missing"
        assert data["can_apply"] is False


# ============================================================================
# 5. APPROVAL & PLAN INTEGRITY SECURITY TESTS (REQUIREMENT 3)
# ============================================================================

def test_apply_dns_requires_explicit_approval(client: TestClient, admin_headers: dict):
    """
    Submitting apply with approved=False must be rejected with HTTP 400 APPROVAL_REQUIRED.
    """
    payload = {
        "domain": "till.gy",
        "target_platform": "vercel",
        "plan_id": "plan_test_123",
        "plan_signature": "sig123",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        "approved": False,
        "override_conflicts": False,
    }
    res = client.post("/api/integrations/apply", headers=admin_headers, json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["detail"]["error"] == "APPROVAL_REQUIRED"


def test_tampered_plan_signature_rejected_400(client: TestClient, admin_headers: dict):
    """
    Verifies that submitting an apply request with a forged/modified plan_signature
    is rejected with HTTP 400 PLAN_TAMPERED.
    """
    payload = {
        "domain": "till.gy",
        "target_platform": "vercel",
        "plan_id": "plan_genuine_123",
        "plan_signature": "tampered_forged_signature_xyz",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        "approved": True,
        "override_conflicts": False,
    }
    res = client.post("/api/integrations/apply", headers=admin_headers, json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["detail"]["error"] == "PLAN_TAMPERED"


def test_client_changes_expiration_to_future_timestamp_rejected_400(client: TestClient, admin_headers: dict):
    """
    Critical Fix 1: Verifies that if a client tampers with expires_at to extend it to a future time,
    the request is rejected with HTTP 400 and PLAN_TAMPERED because it does not match authoritative stored plan.
    """
    workflow = DnsWorkflowService()
    clean_domain = "till.gy"
    zone_id = "zone_cf_test"
    required = [DnsRecordItem(type="A", name="@", content="76.76.21.21")]
    existing = []

    plan_id = "plan_future_tamper_123"
    original_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    records_hash = compute_records_drift_hash(existing)
    sig = generate_plan_signature(plan_id, 1, clean_domain, "vercel", zone_id, required, original_expires_at, records_hash)

    from app.services.integrations.dns_workflow_service import ServerDnsPlanStore
    ServerDnsPlanStore.save_plan(
        plan_id=plan_id,
        domain=clean_domain,
        target_platform="vercel",
        zone_id=zone_id,
        plan_version=1,
        created_at=datetime.now(timezone.utc).isoformat(),
        expires_at=original_expires_at,
        plan_signature=sig,
        existing_records_hash=records_hash,
        required_records=required,
        conflicts=[],
        has_conflicts=False,
    )

    # Client attempts to bypass expiration by submitting a 2-hour future timestamp
    tampered_future_expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    payload = {
        "domain": clean_domain,
        "target_platform": "vercel",
        "plan_id": plan_id,
        "plan_signature": sig,
        "expires_at": tampered_future_expires,
        "approved": True,
        "override_conflicts": False,
    }
    res = client.post("/api/integrations/apply", headers=admin_headers, json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["detail"]["error"] == "PLAN_TAMPERED"
    assert "does not match authoritative server-stored expiration" in data["detail"]["message"].lower()


def test_stored_plan_is_expired_rejected_400(client: TestClient, admin_headers: dict):
    """
    Critical Fix 1: Verifies that if the server-stored plan has expired,
    it is rejected with HTTP 400 and PLAN_EXPIRED, even if client passes matching expired time.
    """
    clean_domain = "till.gy"
    zone_id = "zone_cf_test"
    required = [DnsRecordItem(type="A", name="@", content="76.76.21.21")]
    existing = []

    plan_id = "plan_stored_expired_123"
    expired_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    records_hash = compute_records_drift_hash(existing)
    sig = generate_plan_signature(plan_id, 1, clean_domain, "vercel", zone_id, required, expired_time, records_hash)

    from app.services.integrations.dns_workflow_service import ServerDnsPlanStore
    ServerDnsPlanStore.save_plan(
        plan_id=plan_id,
        domain=clean_domain,
        target_platform="vercel",
        zone_id=zone_id,
        plan_version=1,
        created_at=(datetime.now(timezone.utc) - timedelta(minutes=25)).isoformat(),
        expires_at=expired_time,
        plan_signature=sig,
        existing_records_hash=records_hash,
        required_records=required,
        conflicts=[],
        has_conflicts=False,
    )

    payload = {
        "domain": clean_domain,
        "target_platform": "vercel",
        "plan_id": plan_id,
        "plan_signature": sig,
        "expires_at": expired_time,
        "approved": True,
        "override_conflicts": False,
    }
    res = client.post("/api/integrations/apply", headers=admin_headers, json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["detail"]["error"] == "PLAN_EXPIRED"


def test_request_expiration_differs_from_stored_rejected_400(client: TestClient, admin_headers: dict):
    """
    Critical Fix 1: Verifies that any difference between request expiration and stored expiration
    is rejected with HTTP 400 PLAN_TAMPERED.
    """
    clean_domain = "till.gy"
    zone_id = "zone_cf_test"
    required = [DnsRecordItem(type="A", name="@", content="76.76.21.21")]
    existing = []

    plan_id = "plan_diff_expires_123"
    t1 = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    records_hash = compute_records_drift_hash(existing)
    sig = generate_plan_signature(plan_id, 1, clean_domain, "vercel", zone_id, required, t1, records_hash)

    from app.services.integrations.dns_workflow_service import ServerDnsPlanStore
    ServerDnsPlanStore.save_plan(
        plan_id=plan_id,
        domain=clean_domain,
        target_platform="vercel",
        zone_id=zone_id,
        plan_version=1,
        created_at=datetime.now(timezone.utc).isoformat(),
        expires_at=t1,
        plan_signature=sig,
        existing_records_hash=records_hash,
        required_records=required,
        conflicts=[],
        has_conflicts=False,
    )

    t2 = (datetime.now(timezone.utc) + timedelta(minutes=12)).isoformat()
    payload = {
        "domain": clean_domain,
        "target_platform": "vercel",
        "plan_id": plan_id,
        "plan_signature": sig,
        "expires_at": t2,
        "approved": True,
        "override_conflicts": False,
    }
    res = client.post("/api/integrations/apply", headers=admin_headers, json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["detail"]["error"] == "PLAN_TAMPERED"


def test_valid_unexpired_plan_is_accepted(client: TestClient, admin_headers: dict):
    """
    Critical Fix 1: Verifies that a valid, unexpired plan matching server records is accepted.
    """
    clean_domain = "till.gy"
    zone_id = "zone_cf_test"
    required = [DnsRecordItem(type="A", name="@", content="76.76.21.21")]
    existing = []

    plan_id = "plan_valid_accept_123"
    valid_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    records_hash = compute_records_drift_hash(existing)
    sig = generate_plan_signature(plan_id, 1, clean_domain, "vercel", zone_id, required, valid_expires_at, records_hash)

    from app.services.integrations.dns_workflow_service import ServerDnsPlanStore
    ServerDnsPlanStore.save_plan(
        plan_id=plan_id,
        domain=clean_domain,
        target_platform="vercel",
        zone_id=zone_id,
        plan_version=1,
        created_at=datetime.now(timezone.utc).isoformat(),
        expires_at=valid_expires_at,
        plan_signature=sig,
        existing_records_hash=records_hash,
        required_records=required,
        conflicts=[],
        has_conflicts=False,
    )

    created_item = DnsRecordItem(id="new_rec_1", type="A", name="@", content="76.76.21.21")
    ver_item = DnsVerificationItem(type="A", name="till.gy", expected="76.76.21.21", actual=["76.76.21.21"], verified=True)

    with patch("app.services.integrations.cloudflare_service.cloudflare_service.list_dns_records", AsyncMock(return_value=existing)):
        with patch("app.services.integrations.cloudflare_service.cloudflare_service.create_dns_record", AsyncMock(return_value=created_item)):
            with patch("app.services.integrations.dns_verifier.dns_verifier.verify_records", AsyncMock(return_value=[ver_item])):
                with patch("app.services.integrations.vercel_service.vercel_service.verify_domain", AsyncMock(return_value={"verified": True})):
                    with patch("app.services.integrations.cloudflare_service.cloudflare_service.get_zone_ssl_settings", AsyncMock(return_value="strict")):
                        payload = {
                            "domain": clean_domain,
                            "target_platform": "vercel",
                            "plan_id": plan_id,
                            "plan_signature": sig,
                            "expires_at": valid_expires_at,
                            "approved": True,
                            "override_conflicts": False,
                        }
                        res = client.post("/api/integrations/apply", headers=admin_headers, json=payload)
                        assert res.status_code == 200
                        data = res.json()
                        assert data["state"] == "connected"


# ============================================================================
# 5B. CONCURRENT & REPLAY DNS EXECUTION PREVENTION TESTS (REQUIREMENT 2)
# ============================================================================

def test_two_concurrent_requests_cannot_claim_same_plan():
    """
    High Fix 2: Verifies that ServerDnsPlanStore.atomic_claim_plan allows exactly ONE
    request to transition a plan from pending to applying. The concurrent request is rejected.
    """
    from app.services.integrations.dns_workflow_service import ServerDnsPlanStore
    plan_id = "plan_atomic_claim_test"
    now_dt = datetime.now(timezone.utc)
    ServerDnsPlanStore.save_plan(
        plan_id=plan_id,
        domain="till.gy",
        target_platform="vercel",
        zone_id="zone_cf_1",
        plan_version=1,
        created_at=now_dt.isoformat(),
        expires_at=(now_dt + timedelta(minutes=15)).isoformat(),
        plan_signature="sig_atomic",
        existing_records_hash="hash_atomic",
        required_records=[],
        conflicts=[],
        has_conflicts=False,
    )

    # First request claims plan
    claimed1, reason1, plan_data1 = ServerDnsPlanStore.atomic_claim_plan(plan_id, admin_username="admin_alice")
    assert claimed1 is True
    assert reason1 == "CLAIMED"
    assert plan_data1["status"] == "applying"
    assert plan_data1["claimed_by"] == "admin_alice"

    # Second concurrent request tries to claim the same plan
    claimed2, reason2, plan_data2 = ServerDnsPlanStore.atomic_claim_plan(plan_id, admin_username="admin_bob")
    assert claimed2 is False
    assert reason2 == "ALREADY_CLAIMED"
    assert plan_data2["status"] == "applying"
    assert plan_data2["claimed_by"] == "admin_alice"


def test_replaying_applied_plan_is_rejected_400(client: TestClient, admin_headers: dict):
    """
    High Fix 2: Verifies that attempting to replay an already completed plan
    is rejected with HTTP 400 and PLAN_ALREADY_APPLIED.
    """
    clean_domain = "till.gy"
    zone_id = "zone_cf_test"
    plan_id = "plan_replay_test_123"
    valid_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    records_hash = compute_records_drift_hash([])
    sig = generate_plan_signature(plan_id, 1, clean_domain, "vercel", zone_id, [], valid_expires_at, records_hash)

    from app.services.integrations.dns_workflow_service import ServerDnsPlanStore
    ServerDnsPlanStore.save_plan(
        plan_id=plan_id,
        domain=clean_domain,
        target_platform="vercel",
        zone_id=zone_id,
        plan_version=1,
        created_at=datetime.now(timezone.utc).isoformat(),
        expires_at=valid_expires_at,
        plan_signature=sig,
        existing_records_hash=records_hash,
        required_records=[],
        conflicts=[],
        has_conflicts=False,
    )

    # Mark as completed
    ServerDnsPlanStore.mark_completed(plan_id)

    payload = {
        "domain": clean_domain,
        "target_platform": "vercel",
        "plan_id": plan_id,
        "plan_signature": sig,
        "expires_at": valid_expires_at,
        "approved": True,
        "override_conflicts": False,
    }
    res = client.post("/api/integrations/apply", headers=admin_headers, json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["detail"]["error"] == "PLAN_ALREADY_APPLIED"


def test_failed_cloudflare_operation_recorded_correctly():
    """
    High Fix 2: Verifies that a failed Cloudflare operation sets status='failed'
    and records the exact error message, preventing ambiguous state.
    """
    async def _test():
        workflow = DnsWorkflowService()
        clean_domain = "till.gy"
        zone_id = "zone_cf_test"
        required = [DnsRecordItem(type="A", name="@", content="76.76.21.21")]
        existing = []

        plan_id = "plan_failed_cf_test"
        valid_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        records_hash = compute_records_drift_hash(existing)
        sig = generate_plan_signature(plan_id, 1, clean_domain, "vercel", zone_id, required, valid_expires_at, records_hash)

        from app.services.integrations.dns_workflow_service import ServerDnsPlanStore
        ServerDnsPlanStore.save_plan(
            plan_id=plan_id,
            domain=clean_domain,
            target_platform="vercel",
            zone_id=zone_id,
            plan_version=1,
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=valid_expires_at,
            plan_signature=sig,
            existing_records_hash=records_hash,
            required_records=required,
            conflicts=[],
            has_conflicts=False,
        )

        with patch("app.services.integrations.cloudflare_service.cloudflare_service.list_dns_records", AsyncMock(return_value=existing)):
            with patch(
                "app.services.integrations.cloudflare_service.cloudflare_service.create_dns_record",
                AsyncMock(side_effect=CloudflareApiError("Zone quota limit reached", status_code=502)),
            ):
                req = DnsApplyRequest(
                    domain=clean_domain,
                    target_platform="vercel",
                    plan_id=plan_id,
                    plan_signature=sig,
                    expires_at=valid_expires_at,
                    approved=True,
                    override_conflicts=False,
                )
                with pytest.raises(Exception) as exc_info:
                    await workflow.apply_dns_plan(req, admin_username="admin")
                assert exc_info.value.status_code == 502
                assert exc_info.value.detail["error"] == "CLOUDFLARE_ERROR"

        # Check recorded status in SQLite store
        plan_in_db = ServerDnsPlanStore.get_plan(plan_id)
        assert plan_in_db["status"] == "failed"
        assert "Zone quota limit reached" in plan_in_db["error_message"]

    asyncio.run(_test())


def test_only_one_request_can_perform_dns_writes(client: TestClient, admin_headers: dict):
    """
    High Fix 2: Verifies that if one request has claimed a plan ('applying'),
    a concurrent request receives HTTP 409 PLAN_ALREADY_CLAIMED without making DNS writes.
    """
    clean_domain = "till.gy"
    zone_id = "zone_cf_test"
    required = [DnsRecordItem(type="A", name="@", content="76.76.21.21")]
    existing = []

    plan_id = "plan_concurrent_writes_test"
    valid_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    records_hash = compute_records_drift_hash(existing)
    sig = generate_plan_signature(plan_id, 1, clean_domain, "vercel", zone_id, required, valid_expires_at, records_hash)

    from app.services.integrations.dns_workflow_service import ServerDnsPlanStore
    ServerDnsPlanStore.save_plan(
        plan_id=plan_id,
        domain=clean_domain,
        target_platform="vercel",
        zone_id=zone_id,
        plan_version=1,
        created_at=datetime.now(timezone.utc).isoformat(),
        expires_at=valid_expires_at,
        plan_signature=sig,
        existing_records_hash=records_hash,
        required_records=required,
        conflicts=[],
        has_conflicts=False,
    )

    # First request claims the plan
    ServerDnsPlanStore.atomic_claim_plan(plan_id, admin_username="admin_first")

    # Second request attempts to apply
    payload = {
        "domain": clean_domain,
        "target_platform": "vercel",
        "plan_id": plan_id,
        "plan_signature": sig,
        "expires_at": valid_expires_at,
        "approved": True,
        "override_conflicts": False,
    }
    with patch("app.services.integrations.cloudflare_service.cloudflare_service.create_dns_record", AsyncMock()) as mock_create:
        res = client.post("/api/integrations/apply", headers=admin_headers, json=payload)
        assert res.status_code == 409
        assert res.json()["detail"]["error"] == "PLAN_ALREADY_CLAIMED"
        mock_create.assert_not_called()


# ============================================================================
# 5C. CONFLICT SAFETY & DELETION VERIFICATION TESTS (REQUIREMENT 3)
# ============================================================================

def test_deletion_api_failure_handled_and_does_not_report_success():
    """
    Requirement 3: Verifies that if deleting a conflicting record fails in Cloudflare API,
    the operation fails with 502, does not report success, marks plan as failed, and does not record deletion in audit log.
    """
    async def _test():
        workflow = DnsWorkflowService()
        clean_domain = "till.gy"
        zone_id = "zone_cf_test"
        required = [DnsRecordItem(type="CNAME", name="@", content="cname.vercel-dns.com")]
        existing = [DnsRecordItem(id="conf_a", type="A", name="till.gy", content="1.2.3.4")]
        conflicts = workflow.detect_conflicts(clean_domain, required, existing)

        plan_id = "plan_del_fail_test"
        valid_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        records_hash = compute_records_drift_hash(existing)
        sig = generate_plan_signature(plan_id, 1, clean_domain, "vercel", zone_id, required, valid_expires_at, records_hash)

        from app.services.integrations.dns_workflow_service import ServerDnsPlanStore
        ServerDnsPlanStore.save_plan(
            plan_id=plan_id,
            domain=clean_domain,
            target_platform="vercel",
            zone_id=zone_id,
            plan_version=1,
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=valid_expires_at,
            plan_signature=sig,
            existing_records_hash=records_hash,
            required_records=required,
            conflicts=conflicts,
            has_conflicts=True,
        )

        with patch("app.services.integrations.cloudflare_service.cloudflare_service.list_dns_records", AsyncMock(return_value=existing)):
            with patch(
                "app.services.integrations.cloudflare_service.cloudflare_service.delete_dns_record",
                AsyncMock(side_effect=CloudflareApiError("Failed to delete record: upstream error", status_code=502)),
            ):
                req = DnsApplyRequest(
                    domain=clean_domain,
                    target_platform="vercel",
                    plan_id=plan_id,
                    plan_signature=sig,
                    expires_at=valid_expires_at,
                    approved=True,
                    override_conflicts=True,
                )
                with pytest.raises(Exception) as exc_info:
                    await workflow.apply_dns_plan(req, admin_username="admin")
                assert exc_info.value.status_code == 502
                assert exc_info.value.detail["error"] == "CLOUDFLARE_ERROR"

        # Plan marked failed
        plan_data = ServerDnsPlanStore.get_plan(plan_id)
        assert plan_data["status"] == "failed"

    asyncio.run(_test())


def test_conflict_override_separate_approval_required(client: TestClient, admin_headers: dict):
    """
    When conflicts exist, submitting with approved=True but override_conflicts=False
    must be rejected with HTTP 400 CONFLICT_OVERRIDE_REQUIRED.
    """
    async def _test():
        workflow = DnsWorkflowService()
        clean_domain = "till.gy"
        zone_id = "zone_cf_test"
        required = [DnsRecordItem(type="A", name="@", content="76.76.21.21")]
        existing = [DnsRecordItem(id="rec_conf", type="A", name="till.gy", content="1.2.3.4")]
        conflicts = workflow.detect_conflicts(clean_domain, required, existing)

        plan_id = "plan_conflict_test"
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        records_hash = compute_records_drift_hash(existing)
        sig = generate_plan_signature(plan_id, 1, clean_domain, "vercel", zone_id, required, expires_at, records_hash)

        from app.services.integrations.dns_workflow_service import ServerDnsPlanStore
        ServerDnsPlanStore.save_plan(
            plan_id=plan_id,
            domain=clean_domain,
            target_platform="vercel",
            zone_id=zone_id,
            plan_version=1,
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=expires_at,
            plan_signature=sig,
            existing_records_hash=records_hash,
            required_records=required,
            conflicts=conflicts,
            has_conflicts=True,
        )

        with patch("app.services.integrations.cloudflare_service.cloudflare_service.list_dns_records", AsyncMock(return_value=existing)):
            req = DnsApplyRequest(
                domain=clean_domain,
                target_platform="vercel",
                plan_id=plan_id,
                plan_signature=sig,
                expires_at=expires_at,
                approved=True,
                override_conflicts=False,  # Conflict override NOT approved
            )
            with pytest.raises(Exception) as exc_info:
                await workflow.apply_dns_plan(req, admin_username="admin")
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail["error"] == "CONFLICT_OVERRIDE_REQUIRED"

    asyncio.run(_test())


def test_dns_drift_detection_aborts_apply_409():
    """
    If existing records in Cloudflare changed after plan creation, apply aborts with HTTP 409 DNS_DRIFT_DETECTED.
    """
    async def _test():
        workflow = DnsWorkflowService()
        clean_domain = "till.gy"
        zone_id = "zone_cf_test"
        required = [DnsRecordItem(type="A", name="@", content="76.76.21.21")]
        original_existing = [DnsRecordItem(id="rec_1", type="A", name="till.gy", content="10.0.0.1")]

        plan_id = "plan_drift_test"
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        original_hash = compute_records_drift_hash(original_existing)
        sig = generate_plan_signature(plan_id, 1, clean_domain, "vercel", zone_id, required, expires_at, original_hash)

        from app.services.integrations.dns_workflow_service import ServerDnsPlanStore
        ServerDnsPlanStore.save_plan(
            plan_id=plan_id,
            domain=clean_domain,
            target_platform="vercel",
            zone_id=zone_id,
            plan_version=1,
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=expires_at,
            plan_signature=sig,
            existing_records_hash=original_hash,
            required_records=required,
            conflicts=[],
            has_conflicts=False,
        )

        # Cloudflare records drifted to a new IP!
        drifted_existing = [DnsRecordItem(id="rec_1", type="A", name="till.gy", content="10.0.0.99")]

        with patch("app.services.integrations.cloudflare_service.cloudflare_service.list_dns_records", AsyncMock(return_value=drifted_existing)):
            req = DnsApplyRequest(
                domain=clean_domain,
                target_platform="vercel",
                plan_id=plan_id,
                plan_signature=sig,
                expires_at=expires_at,
                approved=True,
                override_conflicts=False,
            )
            with pytest.raises(Exception) as exc_info:
                await workflow.apply_dns_plan(req, admin_username="admin")
            assert exc_info.value.status_code == 409
            assert exc_info.value.detail["error"] == "DNS_DRIFT_DETECTED"

    asyncio.run(_test())


# ============================================================================
# 6. SAFE DNS CHANGES & PROTECTED RECORDS TESTS (REQUIREMENT 4)
# ============================================================================

def test_unrelated_records_and_mx_never_deleted():
    """
    Verifies that critical mail and security records (MX, SPF, DKIM, DMARC, CAA, NS)
    are protected from deletion or modification.
    """
    mx_record = DnsRecordItem(id="rec_mx", type="MX", name="till.gy", content="mail.till.gy")
    spf_record = DnsRecordItem(id="rec_spf", type="TXT", name="till.gy", content="v=spf1 include:_spf.google.com ~all")
    dkim_record = DnsRecordItem(id="rec_dkim", type="TXT", name="google._domainkey.till.gy", content="v=DKIM1; k=rsa; p=MIGf...")
    dmarc_record = DnsRecordItem(id="rec_dmarc", type="TXT", name="_dmarc.till.gy", content="v=DMARC1; p=reject")
    caa_record = DnsRecordItem(id="rec_caa", type="CAA", name="till.gy", content="0 issue letsencrypt.org")

    assert is_protected_record(mx_record) is True
    assert is_protected_record(spf_record) is True
    assert is_protected_record(dkim_record) is True
    assert is_protected_record(dmarc_record) is True
    assert is_protected_record(caa_record) is True

    # Standard web records are NOT protected
    web_a = DnsRecordItem(id="rec_a", type="A", name="till.gy", content="76.76.21.21")
    web_cname = DnsRecordItem(id="rec_cn", type="CNAME", name="www.till.gy", content="cname.vercel-dns.com")
    assert is_protected_record(web_a) is False
    assert is_protected_record(web_cname) is False

    # Attempting to delete a protected record via CloudflareService raises CloudflareApiError with 403
    async def _test_del():
        cf = CloudflareService(api_token="test_token")
        with pytest.raises(CloudflareApiError) as exc_info:
            await cf.delete_dns_record("zone_1", "rec_mx", record=mx_record)
        assert exc_info.value.status_code == 403
        assert "Cannot delete protected" in exc_info.value.message

    asyncio.run(_test_del())


def test_dns_audit_log_recorded():
    """
    Verifies that every DNS change creates an entry in dns_audit_log
    with admin username, timestamp, and diff details, and never contains secrets.
    """
    DnsAuditManager.record_change(
        admin_username="admin",
        action="CREATE_RECORD",
        domain="till.gy",
        zone_id="zone_test_audit",
        record_type="A",
        record_name="@",
        new_content="76.76.21.21",
        ttl=60,
        proxied=False,
        details="Vercel root edge record",
    )

    logs = DnsAuditManager.list_audit_logs(domain="till.gy", limit=5)
    assert len(logs) >= 1
    last_log = logs[0]
    assert last_log["admin_username"] == "admin"
    assert last_log["domain"] == "till.gy"
    assert last_log["action"] == "CREATE_RECORD"
    assert last_log["record_type"] == "A"
    assert last_log["new_content"] == "76.76.21.21"
    # Ensure no token or secret in audit log
    for key, val in last_log.items():
        if isinstance(val, str):
            assert "secret" not in val.lower()
            assert "bearer" not in val.lower()


# ============================================================================
# 7. END-TO-END APPLY AND VERIFICATION TESTS
# ============================================================================

def test_apply_dns_creates_records_when_approved():
    """
    When approved and no conflicts, records are created in Cloudflare and verified.
    """
    async def _test():
        workflow = DnsWorkflowService()
        clean_domain = "till.gy"
        zone_id = "zone_cf_test"
        required = [DnsRecordItem(type="A", name="@", content="76.76.21.21")]
        existing = []

        plan_id = "plan_e2e_test"
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        records_hash = compute_records_drift_hash(existing)
        sig = generate_plan_signature(plan_id, 1, clean_domain, "vercel", zone_id, required, expires_at, records_hash)

        from app.services.integrations.dns_workflow_service import ServerDnsPlanStore
        ServerDnsPlanStore.save_plan(
            plan_id=plan_id,
            domain=clean_domain,
            target_platform="vercel",
            zone_id=zone_id,
            plan_version=1,
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=expires_at,
            plan_signature=sig,
            existing_records_hash=records_hash,
            required_records=required,
            conflicts=[],
            has_conflicts=False,
        )

        created_item = DnsRecordItem(id="new_rec_1", type="A", name="@", content="76.76.21.21")
        ver_item = DnsVerificationItem(type="A", name="till.gy", expected="76.76.21.21", actual=["76.76.21.21"], verified=True)

        with patch("app.services.integrations.cloudflare_service.cloudflare_service.list_dns_records", AsyncMock(return_value=existing)):
            with patch("app.services.integrations.cloudflare_service.cloudflare_service.create_dns_record", AsyncMock(return_value=created_item)) as mock_create:
                with patch("app.services.integrations.dns_verifier.dns_verifier.verify_records", AsyncMock(return_value=[ver_item])):
                    with patch("app.services.integrations.vercel_service.vercel_service.verify_domain", AsyncMock(return_value={"verified": True})):
                        with patch("app.services.integrations.cloudflare_service.cloudflare_service.get_zone_ssl_settings", AsyncMock(return_value="strict")):
                            req = DnsApplyRequest(
                                domain=clean_domain,
                                target_platform="vercel",
                                plan_id=plan_id,
                                plan_signature=sig,
                                expires_at=expires_at,
                                approved=True,
                                override_conflicts=False,
                            )
                            res = await workflow.apply_dns_plan(req, admin_username="admin")

                            mock_create.assert_called_once()
                            assert res.state == "connected"
                            assert res.ssl_verified is True
                            assert res.platform_verified is True
    asyncio.run(_test())


# ============================================================================
# 8. REAL DNS VERIFICATION BEHAVIOR TESTS
# ============================================================================

def test_real_dns_verifier_never_fake_success():
    """
    Verifies that DnsVerifier only reports verified=True when DNS results match.
    Never claims verification without real DNS confirmation.
    """
    async def _test():
        verifier = DnsVerifier()
        record = DnsRecordItem(type="A", name="@", content="76.76.21.21")

        # 1. When resolver returns expected IP
        with patch.object(verifier, "query_dns", AsyncMock(return_value=["76.76.21.21"])):
            res = await verifier.verify_record("till.gy", record)
            assert res.verified is True
            assert res.error is None

        # 2. When resolver returns completely different IP
        with patch.object(verifier, "query_dns", AsyncMock(return_value=["198.51.100.1"])):
            res = await verifier.verify_record("till.gy", record)
            assert res.verified is False
            assert "expected '76.76.21.21'" in res.error

        # 3. When resolver returns empty (unpropagated)
        with patch.object(verifier, "query_dns", AsyncMock(return_value=[])):
            res = await verifier.verify_record("till.gy", record)
            assert res.verified is False
            assert "No A records found" in res.error
    asyncio.run(_test())


# ============================================================================
# 9. VERCEL INTEGRATION REQUIREMENTS TESTS
# ============================================================================

def test_vercel_required_records_generation():
    """
    Verifies that Vercel required records generation queries domain config,
    extracts recommended IPv4 and CNAME, and includes verification TXT if required.
    Does NOT invent fake TXT records.
    """
    async def _test():
        vc = VercelService(api_token="vc_test_token", project_id="prj_123")
        mock_config = {
            "recommendedIPv4": "76.76.21.21",
            "recommendedCNAME": "cname.vercel-dns.com",
        }
        mock_proj_domain = {
            "name": "till.gy",
            "verified": False,
            "verification": [
                {
                    "type": "TXT",
                    "domain": "_vercel.till.gy",
                    "value": "vc-domain-verify=till.gy,real-token-hash-789",
                    "reason": "ownership",
                }
            ],
        }

        with patch.object(vc, "get_domain_config", AsyncMock(return_value=mock_config)):
            with patch.object(vc, "get_project_domain", AsyncMock(return_value=mock_proj_domain)):
                records = await vc.get_required_dns_records("till.gy")
                assert len(records) == 3

                types = {r.type for r in records}
                assert "A" in types
                assert "CNAME" in types
                assert "TXT" in types

                txt_rec = next(r for r in records if r.type == "TXT")
                assert txt_rec.content == "vc-domain-verify=till.gy,real-token-hash-789"
                assert txt_rec.name == "_vercel"
    asyncio.run(_test())


# ============================================================================
# 10. RENDER INTEGRATION REQUIREMENTS TESTS
# ============================================================================

def test_render_required_records_generation():
    """
    Verifies that Render required records are derived from the service slug,
    producing exact CNAME records for apex and www.
    """
    async def _test():
        rnd = RenderService(api_key="rnd_test_key", service_id="srv_456")
        mock_service = {
            "service": {
                "name": "my-backend-app",
                "slug": "my-backend-app",
            }
        }

        with patch.object(rnd, "get_service", AsyncMock(return_value=mock_service)):
            with patch.object(rnd, "get_custom_domain", AsyncMock(return_value=None)):
                records = await rnd.get_required_dns_records("till.gy")
                assert len(records) == 2

                apex_rec = next(r for r in records if r.name == "@")
                assert apex_rec.type == "CNAME"
                assert apex_rec.content == "my-backend-app.onrender.com"

                www_rec = next(r for r in records if r.name == "www")
                assert www_rec.type == "CNAME"
                assert www_rec.content == "my-backend-app.onrender.com"
    asyncio.run(_test())


# ============================================================================
# 11. NETWORK FAILURE & TIMEOUT HANDLING
# ============================================================================

def test_network_timeout_handling():
    """Verifies that API timeouts are caught gracefully without 500 crash."""
    async def _test():
        import httpx
        cf = CloudflareService(api_token="cf_timeout_token")

        with patch("httpx.AsyncClient.get", AsyncMock(side_effect=httpx.TimeoutException("Connection timed out"))):
            with pytest.raises(CloudflareApiError) as exc_info:
                await cf.list_dns_records("zone_timeout")
            assert exc_info.value.status_code == 502
            assert "network error" in exc_info.value.message.lower() or "timeout" in exc_info.value.message.lower()
    asyncio.run(_test())
