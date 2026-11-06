import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.services.registration_service import RegistrationService

logger = logging.getLogger("dns_audit")


class DnsAuditManager:
    """
    Persistent audit trail for all Cloudflare DNS modifications.
    Records administrator identity, timestamp, domain, zone, and exact record diffs.
    Never logs API credentials or secrets.
    """

    @classmethod
    def _init_table(cls) -> None:
        with RegistrationService._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dns_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    admin_username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    zone_id TEXT NOT NULL,
                    record_type TEXT NOT NULL,
                    record_name TEXT NOT NULL,
                    old_content TEXT,
                    new_content TEXT,
                    ttl INTEGER,
                    proxied INTEGER,
                    details TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dns_audit_domain ON dns_audit_log(domain)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dns_audit_timestamp ON dns_audit_log(timestamp)"
            )
            conn.commit()

    @classmethod
    def record_change(
        cls,
        admin_username: str,
        action: str,
        domain: str,
        zone_id: str,
        record_type: str,
        record_name: str,
        new_content: Optional[str] = None,
        old_content: Optional[str] = None,
        ttl: int = 60,
        proxied: bool = False,
        details: Optional[str] = None,
    ) -> None:
        cls._init_table()
        now = datetime.now(timezone.utc).isoformat()
        with RegistrationService._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO dns_audit_log (
                    timestamp, admin_username, action, domain, zone_id,
                    record_type, record_name, old_content, new_content,
                    ttl, proxied, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    admin_username,
                    action,
                    domain.strip().lower(),
                    zone_id,
                    record_type.upper(),
                    record_name,
                    old_content,
                    new_content,
                    ttl,
                    1 if proxied else 0,
                    details,
                ),
            )
            conn.commit()
        logger.info(
            f"DNS Audit: Admin '{admin_username}' executed '{action}' on domain '{domain}' "
            f"({record_type} {record_name} -> {new_content}) in zone {zone_id}"
        )

    @classmethod
    def list_audit_logs(cls, domain: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        cls._init_table()
        query = "SELECT * FROM dns_audit_log"
        params: list = []
        if domain:
            query += " WHERE domain = ?"
            params.append(domain.strip().lower())
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with RegistrationService._get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            cols = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(cols, row)) for row in rows]


DnsAuditManager._init_table()
