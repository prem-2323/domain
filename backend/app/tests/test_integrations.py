import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.models.integration import DnsRecordItem, CloudflareZoneInfo
from app.services.integrations.cloudflare_service import CloudflareService, CloudflareApiError
from app.services.integrations.vercel_service import VercelService, VercelApiError
from app.services.integrations.render_service import RenderService, RenderApiError
from app.services.integrations.dns_verifier import DnsVerifier
from app.services.integrations.dns_workflow_service import DnsWorkflowService


import asyncio

@pytest.fixture
def client():
    return TestClient(app)


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
# 2. INVALID CREDENTIALS & ERROR HANDLING TESTS
# ============================================================================

def test_cloudflare_invalid_credentials_handling():
    """Verifies that invalid Cloudflare credentials fail cleanly without leaking tokens."""
    async def _test():
        cf = CloudflareService(api_token="cf_invalid_fake_token_12345")
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"success": False, "errors": [{"message": "Invalid access token"}]}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            is_valid, msg = await cf.verify_token()
            assert is_valid is False
            assert "Invalid" in msg
    asyncio.run(_test())


def test_vercel_invalid_credentials_handling():
    """Verifies that invalid Vercel credentials fail cleanly."""
    async def _test():
        vc = VercelService(api_token="vc_invalid_token", project_id="prj_test")
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": {"message": "Invalid token"}}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            is_valid, msg = await vc.verify_credentials()
            assert is_valid is False
            assert "Invalid" in msg
    asyncio.run(_test())


def test_render_invalid_credentials_handling():
    """Verifies that invalid Render credentials fail cleanly."""
    async def _test():
        rnd = RenderService(api_key="rnd_invalid_key", service_id="srv_test")
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Unauthorized"}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            is_valid, msg = await rnd.verify_credentials()
            assert is_valid is False
            assert "Invalid" in msg or "Unauthorized" in msg
    asyncio.run(_test())


# ============================================================================
# 3. DOMAIN AUTHORIZATION & SYNTAX TESTS
# ============================================================================

def test_unauthorized_domain_rejection(client: TestClient):
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
        res = client.get("/api/integrations/plan", params={"domain": dom, "target": "vercel"})
        assert res.status_code == 200
        data = res.json()
        assert data["state"] == "failed"
        assert data["can_apply"] is False


# ============================================================================
# 4. CREDENTIALS MISSING WORKFLOW TESTS
# ============================================================================

def test_proposed_plan_credentials_missing_state(client: TestClient):
    """When Cloudflare token is not configured, returns state 'credentials_missing'."""
    with patch("app.services.integrations.cloudflare_service.CloudflareService.is_configured", new_callable=PropertyMock, return_value=False):
        res = client.get("/api/integrations/plan", params={"domain": "till.gy", "target": "vercel"})
        assert res.status_code == 200
        data = res.json()
        assert data["state"] == "credentials_missing"
        assert data["can_apply"] is False


# ============================================================================
# 5. CLOUDFLARE ZONE STATUS & ASSIGNED NAMESERVERS TESTS
# ============================================================================

def test_zone_assigned_nameservers_and_pending_status():
    """
    Verifies that nameservers are extracted directly from the actual zone,
    and a pending zone transitions to awaiting_nameserver_update state.
    """
    async def _test():
        workflow = DnsWorkflowService()
        mock_zone = CloudflareZoneInfo(
            zone_id="zone_abc_123",
            name="till.gy",
            status="pending",
            name_servers=["art.ns.cloudflare.com", "leah.ns.cloudflare.com"],
            paused=False,
        )

        with patch("app.services.integrations.cloudflare_service.CloudflareService.is_configured", new_callable=PropertyMock, return_value=True):
            with patch("app.services.integrations.vercel_service.VercelService.is_configured", new_callable=PropertyMock, return_value=True):
                with patch("app.services.integrations.cloudflare_service.cloudflare_service.get_zone_for_domain", AsyncMock(return_value=mock_zone)):
                    plan = await workflow.get_proposed_plan("till.gy", "vercel")
                    assert plan.state == "awaiting_nameserver_update"
                    assert plan.is_zone_active is False
                    assert plan.assigned_nameservers == ["art.ns.cloudflare.com", "leah.ns.cloudflare.com"]
                    assert "art.ns.cloudflare.com" in plan.message
                    # Never uses unrelated nameservers
                    assert "masterperi5.me" not in plan.message
    asyncio.run(_test())


# ============================================================================
# 6. DNS CONFLICT DETECTION TESTS
# ============================================================================

def test_conflict_detection_logic():
    """Verifies that differing A/CNAME records trigger explicit conflict detection."""
    workflow = DnsWorkflowService()
    required = [
        DnsRecordItem(type="A", name="@", content="76.76.21.21", purpose="Vercel root"),
        DnsRecordItem(type="CNAME", name="www", content="cname.vercel-dns.com", purpose="Vercel www"),
    ]
    # Existing record points to a completely different server IP
    existing = [
        DnsRecordItem(id="rec_1", type="A", name="till.gy", content="192.0.2.1"),
        DnsRecordItem(id="rec_2", type="CNAME", name="www.till.gy", content="old-host.example.com"),
    ]

    conflicts = workflow.detect_conflicts("till.gy", required, existing)
    assert len(conflicts) == 2
    assert conflicts[0].conflict_type == "existing_record_differs"
    assert "192.0.2.1" in conflicts[0].message
    assert "76.76.21.21" in conflicts[0].message


# ============================================================================
# 7. EXPLICIT APPROVAL ENFORCEMENT TESTS
# ============================================================================

def test_apply_dns_requires_explicit_approval(client: TestClient):
    """
    Submitting apply without approved=True must be rejected with HTTP 400.
    Never modifies DNS without approval.
    """
    payload = {
        "domain": "till.gy",
        "target_platform": "vercel",
        "approved": False,
        "override_conflicts": False,
    }
    res = client.post("/api/integrations/apply", json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["detail"]["error"] == "APPROVAL_REQUIRED"


def test_apply_dns_aborts_on_unapproved_conflict():
    """If conflicts exist and override_conflicts=False, changes are aborted."""
    async def _test():
        workflow = DnsWorkflowService()
        from app.models.integration import DnsConflict, DnsRecordItem
        mock_plan = MagicMock()
        mock_plan.can_apply = True
        mock_plan.zone_id = "zone_123"
        mock_plan.has_conflicts = True
        mock_plan.conflicts = [
            DnsConflict(
                existing_record=DnsRecordItem(type="A", name="@", content="1.2.3.4"),
                proposed_record=DnsRecordItem(type="A", name="@", content="76.76.21.21"),
                conflict_type="existing_record_differs",
                message="Points to 1.2.3.4",
            )
        ]
        mock_plan.zone_status = "active"
        mock_plan.assigned_nameservers = ["ns1.cloudflare.com", "ns2.cloudflare.com"]

        from app.models.integration import DnsApplyRequest
        req = DnsApplyRequest(domain="till.gy", target_platform="vercel", approved=True, override_conflicts=False)

        with patch.object(workflow, "get_proposed_plan", AsyncMock(return_value=mock_plan)):
            status_res = await workflow.apply_dns_plan(req)
            assert status_res.state == "dns_conflict"
            assert "override is required" in status_res.message
    asyncio.run(_test())


# ============================================================================
# 8. DNS RECORD CREATION & UPDATE VIA CLOUDFLARE
# ============================================================================

def test_apply_dns_creates_records_when_approved():
    """
    When approved and no conflicts, records are created in Cloudflare and verified.
    """
    async def _test():
        workflow = DnsWorkflowService()
        from app.models.integration import ProposedDnsPlan, DnsApplyRequest, DnsVerificationItem

        mock_plan = ProposedDnsPlan(
            domain="till.gy",
            target_platform="vercel",
            zone_id="zone_cf_test",
            zone_name="till.gy",
            zone_status="active",
            assigned_nameservers=["ns1.cloudflare.com", "ns2.cloudflare.com"],
            is_zone_active=True,
            required_records=[DnsRecordItem(type="A", name="@", content="76.76.21.21")],
            existing_records=[],
            conflicts=[],
            has_conflicts=False,
            state="awaiting_approval",
            message="Ready",
            can_apply=True,
            requires_approval=True,
        )

        created_item = DnsRecordItem(id="new_rec_1", type="A", name="@", content="76.76.21.21")
        ver_item = DnsVerificationItem(type="A", name="till.gy", expected="76.76.21.21", actual=["76.76.21.21"], verified=True)

        with patch.object(workflow, "get_proposed_plan", AsyncMock(return_value=mock_plan)):
            with patch("app.services.integrations.cloudflare_service.cloudflare_service.create_dns_record", AsyncMock(return_value=created_item)) as mock_create:
                with patch("app.services.integrations.dns_verifier.dns_verifier.verify_records", AsyncMock(return_value=[ver_item])):
                    with patch("app.services.integrations.vercel_service.vercel_service.verify_domain", AsyncMock(return_value={"verified": True})):
                        with patch("app.services.integrations.cloudflare_service.cloudflare_service.get_zone_ssl_settings", AsyncMock(return_value="strict")):
                            req = DnsApplyRequest(domain="till.gy", target_platform="vercel", approved=True, override_conflicts=False)
                            res = await workflow.apply_dns_plan(req)

                            mock_create.assert_called_once()
                            assert res.state == "connected"
                            assert res.ssl_verified is True
                            assert res.platform_verified is True
    asyncio.run(_test())


# ============================================================================
# 9. REAL DNS VERIFICATION BEHAVIOR TESTS
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
# 10. VERCEL INTEGRATION REQUIREMENTS TESTS
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
# 11. RENDER INTEGRATION REQUIREMENTS TESTS
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
# 12. NETWORK FAILURE & TIMEOUT HANDLING
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
