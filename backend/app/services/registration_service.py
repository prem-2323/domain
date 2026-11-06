import os
import re
import sqlite3
import secrets
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from pathlib import Path

from app.models.registration import (
    RegistrationRequestStatus,
    RegistrationRequestResponse,
    STATUS_LABELS,
    CreateRegistrationRequest,
    UpdateRegistrationRequest,
)
from app.services.validation_service import ValidationService

# Database location: backend/data/registrations.db
DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "registrations.db"

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

ACTIVE_STATUSES = {
    RegistrationRequestStatus.PENDING.value,
    RegistrationRequestStatus.VERIFICATION_REQUIRED.value,
    RegistrationRequestStatus.VERIFIED_AVAILABLE.value,
    RegistrationRequestStatus.REGISTRATION_IN_PROGRESS.value,
}


class RegistrationService:
    """
    Service responsible for managing manual .GY domain registration requests.
    Stores data persistently in SQLite and enforces validation and deduplication.
    """

    _db_path: Path = DEFAULT_DB_PATH

    @classmethod
    def set_db_path(cls, path: Path) -> None:
        """Allows overriding database path for testing or custom environments."""
        cls._db_path = path
        cls._init_db()

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        cls._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(cls._db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def _init_db(cls) -> None:
        """Initializes database tables and indexes if they do not exist."""
        with cls._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS registration_requests (
                    request_id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    customer_email TEXT NOT NULL,
                    message TEXT,
                    status TEXT NOT NULL,
                    estimated_annual_price REAL NOT NULL,
                    confirmed_price REAL,
                    currency TEXT NOT NULL DEFAULT 'USD',
                    admin_notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_req_domain ON registration_requests(domain)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_req_status ON registration_requests(status)"
            )
            conn.commit()

    @classmethod
    def validate_request_input(
        cls, req: CreateRegistrationRequest
    ) -> Tuple[bool, Optional[str], str]:
        """
        Validates customer email and domain syntax.
        Returns: (is_valid, error_message, normalized_domain)
        """
        # 1. Validate customer email
        email = req.customer_email.strip()
        if not EMAIL_REGEX.match(email):
            return False, f"Invalid customer email format: '{req.customer_email}'.", ""

        # 2. Validate customer name
        name = req.customer_name.strip()
        if len(name) < 2:
            return False, "Customer name must be at least 2 characters.", ""

        # 3. Validate domain
        raw_domain = req.domain.strip().lower()
        if not raw_domain.endswith(".gy"):
            return False, f"Only .gy domains are supported. Provided domain '{req.domain}' does not end in .gy.", ""

        # Validate SLD using ValidationService
        is_valid, sld, _, err = ValidationService.parse_and_validate(raw_domain)
        if not is_valid or not sld:
            return False, err or f"Invalid .gy domain format: '{req.domain}'.", ""

        normalized_domain = f"{sld}.gy"
        return True, None, normalized_domain

    @classmethod
    def generate_request_id(cls) -> str:
        """Generates a memorable, unique request ID (e.g. REQ-GY-9B41F28C)."""
        random_hex = secrets.token_hex(4).upper()
        return f"REQ-GY-{random_hex}"

    @classmethod
    def _row_to_response(cls, row: sqlite3.Row) -> RegistrationRequestResponse:
        status_enum = RegistrationRequestStatus(row["status"])
        return RegistrationRequestResponse(
            request_id=row["request_id"],
            domain=row["domain"],
            customer_name=row["customer_name"],
            customer_email=row["customer_email"],
            message=row["message"],
            status=status_enum,
            status_label=STATUS_LABELS.get(status_enum, "Unknown Status"),
            estimated_annual_price=float(row["estimated_annual_price"]),
            confirmed_price=float(row["confirmed_price"]) if row["confirmed_price"] is not None else None,
            currency=row["currency"],
            admin_notes=row["admin_notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @classmethod
    def create_request(
        cls, req: CreateRegistrationRequest
    ) -> Tuple[bool, Optional[RegistrationRequestResponse], Optional[str], int]:
        """
        Validates, deduplicates, and creates a new registration request.
        Returns: (success, result, error_message, http_status_code)
        """
        cls._init_db()

        # Input validation
        is_valid, err_msg, normalized_domain = cls.validate_request_input(req)
        if not is_valid:
            return False, None, err_msg, 400

        now_iso = datetime.now(timezone.utc).isoformat()

        with cls._get_connection() as conn:
            # Check for existing active requests for the exact domain
            cursor = conn.execute(
                """
                SELECT request_id, customer_email, status, created_at
                FROM registration_requests
                WHERE domain = ? AND status IN (?, ?, ?, ?)
                ORDER BY created_at DESC LIMIT 1
                """,
                (
                    normalized_domain,
                    RegistrationRequestStatus.PENDING.value,
                    RegistrationRequestStatus.VERIFICATION_REQUIRED.value,
                    RegistrationRequestStatus.VERIFIED_AVAILABLE.value,
                    RegistrationRequestStatus.REGISTRATION_IN_PROGRESS.value,
                ),
            )
            existing = cursor.fetchone()

            if existing:
                existing_id = existing["request_id"]
                existing_status = existing["status"]
                return (
                    False,
                    None,
                    f"A pending registration request for '{normalized_domain}' is already active "
                    f"(Request ID: {existing_id}, Status: {existing_status}). "
                    f"Duplicate requests for the same domain are not accepted while active.",
                    409,
                )

            request_id = cls.generate_request_id()
            estimated_price = 45.0  # Standard accredited registrar rate

            conn.execute(
                """
                INSERT INTO registration_requests (
                    request_id, domain, customer_name, customer_email, message,
                    status, estimated_annual_price, confirmed_price, currency,
                    admin_notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    normalized_domain,
                    req.customer_name.strip(),
                    req.customer_email.strip().lower(),
                    req.message.strip() if req.message else None,
                    RegistrationRequestStatus.PENDING.value,
                    estimated_price,
                    None,
                    "USD",
                    None,
                    now_iso,
                    now_iso,
                ),
            )
            conn.commit()

        created = cls.get_request(request_id)
        if not created:
            return False, None, "Failed to retrieve newly created registration request.", 500

        return True, created, None, 201

    @classmethod
    def get_request(cls, request_id: str) -> Optional[RegistrationRequestResponse]:
        """Fetches a registration request by unique ID."""
        cls._init_db()
        with cls._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM registration_requests WHERE request_id = ?",
                (request_id.strip().upper(),),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return cls._row_to_response(row)

    @classmethod
    def list_requests(
        cls, status_filter: Optional[RegistrationRequestStatus] = None
    ) -> List[RegistrationRequestResponse]:
        """Lists registration requests, ordered newest first, with optional status filtering."""
        cls._init_db()
        with cls._get_connection() as conn:
            if status_filter:
                cursor = conn.execute(
                    "SELECT * FROM registration_requests WHERE status = ? ORDER BY created_at DESC",
                    (status_filter.value,),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM registration_requests ORDER BY created_at DESC"
                )
            rows = cursor.fetchall()
            return [cls._row_to_response(row) for row in rows]

    @classmethod
    def update_request(
        cls, request_id: str, updates: UpdateRegistrationRequest
    ) -> Tuple[bool, Optional[RegistrationRequestResponse], Optional[str]]:
        """
        Updates an existing request status, confirmed price, or internal admin notes.
        Returns: (success, updated_request, error_message)
        """
        cls._init_db()
        normalized_id = request_id.strip().upper()
        existing = cls.get_request(normalized_id)
        if not existing:
            return False, None, f"Registration request '{request_id}' not found."

        now_iso = datetime.now(timezone.utc).isoformat()

        # Prepare field updates
        new_status = updates.status.value if updates.status is not None else existing.status.value
        new_confirmed_price = (
            updates.confirmed_price if updates.confirmed_price is not None else existing.confirmed_price
        )
        new_admin_notes = (
            updates.admin_notes if updates.admin_notes is not None else existing.admin_notes
        )

        with cls._get_connection() as conn:
            conn.execute(
                """
                UPDATE registration_requests
                SET status = ?, confirmed_price = ?, admin_notes = ?, updated_at = ?
                WHERE request_id = ?
                """,
                (new_status, new_confirmed_price, new_admin_notes, now_iso, normalized_id),
            )
            conn.commit()

        updated = cls.get_request(normalized_id)
        return True, updated, None


# Ensure DB initialization on import
RegistrationService._init_db()
