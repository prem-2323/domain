import logging
from typing import List, Optional
import httpx

from app.models.integration import DnsRecordItem, DnsVerificationItem

logger = logging.getLogger("dns_verifier")

DOH_ENDPOINT = "https://cloudflare-dns.com/dns-query"


class DnsVerifier:
    """
    Performs real authoritative DNS queries using DNS-over-HTTPS (DoH)
    to verify live propagation of A, CNAME, and TXT records.
    Never claims a record is live without verifying actual resolver results.
    """

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    async def query_dns(self, name: str, record_type: str) -> List[str]:
        """
        Queries actual DNS resolver via DNS-over-HTTPS.
        Returns list of answer data strings.
        """
        clean_name = name.strip().rstrip(".")
        clean_type = record_type.strip().upper()

        headers = {"Accept": "application/dns-json"}
        params = {"name": clean_name, "type": clean_type}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(DOH_ENDPOINT, headers=headers, params=params)
                if res.status_code == 200:
                    data = res.json()
                    answers = data.get("Answer") or []
                    results = []
                    for ans in answers:
                        val = ans.get("data", "")
                        # Remove surrounding quotes from TXT strings
                        if val.startswith('"') and val.endswith('"'):
                            val = val[1:-1]
                        # Remove trailing dot from FQDNs
                        val = val.rstrip(".")
                        if val:
                            results.append(val)
                    return results
                return []
        except httpx.RequestError as e:
            logger.warning(f"DoH query error for {clean_name} ({clean_type}): {e}")
            return []

    async def verify_record(self, domain: str, record: DnsRecordItem) -> DnsVerificationItem:
        """
        Verifies a single expected DNS record against live DNS results.
        """
        # Determine FQDN for the record
        dom = domain.strip().lower().rstrip(".")
        rec_name = record.name.strip().lower()

        if rec_name in ("@", "", dom):
            fqdn = dom
        elif rec_name.endswith(f".{dom}"):
            fqdn = rec_name
        else:
            fqdn = f"{rec_name}.{dom}"

        expected_val = record.content.strip().rstrip(".")
        # For TXT records, strip quotes
        if expected_val.startswith('"') and expected_val.endswith('"'):
            expected_val = expected_val[1:-1]

        actual_vals = await self.query_dns(fqdn, record.type)

        # Match check
        verified = False
        for act in actual_vals:
            # Case-insensitive comparison for hostnames, case-sensitive for TXT tokens
            if record.type.upper() in ("A", "AAAA"):
                if act.strip() == expected_val:
                    verified = True
                    break
            elif record.type.upper() == "CNAME":
                if act.lower().rstrip(".") == expected_val.lower().rstrip("."):
                    verified = True
                    break
            elif record.type.upper() == "TXT":
                if expected_val in act or act == expected_val:
                    verified = True
                    break

        error_msg = None
        if not verified:
            if not actual_vals:
                error_msg = f"No {record.type} records found for '{fqdn}' in DNS."
            else:
                error_msg = f"DNS returned [{', '.join(actual_vals)}] but expected '{expected_val}'."

        return DnsVerificationItem(
            type=record.type.upper(),
            name=fqdn,
            expected=expected_val,
            actual=actual_vals,
            verified=verified,
            error=error_msg,
        )

    async def verify_records(self, domain: str, records: List[DnsRecordItem]) -> List[DnsVerificationItem]:
        """
        Verifies multiple DNS records.
        """
        results: List[DnsVerificationItem] = []
        for r in records:
            res = await self.verify_record(domain, r)
            results.append(res)
        return results


dns_verifier = DnsVerifier()
