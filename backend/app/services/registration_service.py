import re
import sqlite3
import secrets
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from pathlib import Path

from app.models.registration import (
    RegistrationRequestStatus,
    STATUS_LABELS,
    CreateRegistrationRequest,
    UpdateRegistrationRequest,
    CustomerRequestCreatedResponse,
    PublicRegistrationRequestResponse,
    CustomerVerifiedRequestResponse,
    AdminRegistrationRequestResponse,
)
from app.services.validation_service import ValidationService

# Default SQLite database location: backend/data/registrations.db
DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "registrations.db"

# Strict RFC-compliant email validation pattern
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$")

ACTIVE_STATUS_VALUES = (
    RegistrationRequestStatus.PENDING.value,
    RegistrationRequestStatus.VERIFICATION_REQUIRED.value,
    RegistrationRequestStatus.VERIFIED_AVAILABLE.value,
    RegistrationRequestStatus.REGISTRATION_IN_PROGRESS.value,
)


class RegistrationService:
    """
    Core service for managing manual .GY domain registration requests.
    Enforces atomic SQLite transactions, partial unique indexes,
    cryptographic request IDs, and customer privacy controls.
    """

    _db_path: Path = DEFAULT_DB_PATH

    @classmethod
    def set_db_path(cls, path: Path) -> None:
        """Allows overriding database path (e.g. for testing with isolated temporary databases)."""
        cls._db_path = path
        cls._init_db()

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        cls._db_path.parent.mkdir(parents=True, exist_ok=True)
        # Using timeout for concurrent access safety
        conn = sqlite3.connect(str(cls._db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def _init_db(cls) -> None:
        """
        Initializes SQLite schema, partial unique index for active requests,
        and runs automatic schema migrations if needed.
        """
        cls._db_path.parent.mkdir(parents=True, exist_ok=True)
        with cls._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS registration_requests (
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

            # Run safe migrations for existing tables
            cursor = conn.execute("PRAGMA table_info(registration_requests)")
            existing_cols = {row["name"] for row in cursor.fetchall()}

            if "tracking_token" not in existing_cols:
                conn.execute("ALTER TABLE registration_requests ADD COLUMN tracking_token TEXT")
                # Backfill any legacy rows with secure tokens
                cursor_legacy = conn.execute("SELECT request_id FROM registration_requests WHERE tracking_token IS NULL")
                for r in cursor_legacy.fetchall():
                    conn.execute(
                        "UPDATE registration_requests SET tracking_token = ? WHERE request_id = ?",
                        (secrets.token_urlsafe(32), r["request_id"]),
                    )

            if "confirmation_reference" not in existing_cols:
                conn.execute("ALTER TABLE registration_requests ADD COLUMN confirmation_reference TEXT")

            # ATOMIC DUPLICATE PREVENTION:
            # SQLite Partial Unique Index enforces that only ONE active request
            # can exist per normalized domain at any time at the database engine level.
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_active_domain_request 
                ON registration_requests(domain) 
                WHERE status IN ('pending', 'verification_required', 'verified_available', 'registration_in_progress')
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_req_domain ON registration_requests(domain)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_req_status ON registration_requests(status)")
            conn.commit()

    @classmethod
    def validate_request_input(
        cls, req: CreateRegistrationRequest
    ) -> Tuple[bool, Optional[str], str]:
        """
        Validates customer email and domain syntax.
        Returns: (is_valid, error_message, normalized_domain)
        """
        # 1. Customer email validation
        email = req.customer_email.strip().lower()
        if len(email) > 254:
            return False, "Customer email exceeds maximum length of 254 characters.", ""
        if ".." in email or not EMAIL_REGEX.match(email):
            return False, f"Invalid customer email format: '{req.customer_email}'.", ""

        # 2. Customer name validation
        name = req.customer_name.strip()
        if len(name) < 2 or len(name) > 120:
            return False, "Customer name must be between 2 and 120 characters.", ""

        # 3. Domain validation
        raw_domain = req.domain.strip().lower()
        if not raw_domain.endswith(".gy"):
            return False, f"Only .gy domains are supported. '{req.domain}' does not end in .gy.", ""

        if ".." in raw_domain:
            return False, f"Invalid domain syntax: '{req.domain}' contains consecutive dots.", ""

        parts = raw_domain.split(".")
        if len(parts) != 2:
            return False, f"Invalid domain syntax: '{req.domain}'. Only standard <name>.gy domains are supported.", ""

        # Validate SLD using ValidationService
        is_valid, sld, _, err = ValidationService.parse_and_validate(raw_domain)
        if not is_valid or not sld:
            return False, err or f"Invalid .gy domain format: '{req.domain}'.", ""

        normalized_domain = f"{sld}.gy"
        return True, None, normalized_domain

    @classmethod
    def generate_request_id(cls) -> str:
        """
        Generates a request ID with at least 128 bits of cryptographically secure randomness.
        16 bytes = 128 bits = 32 hexadecimal characters.
        """
        random_hex_128bit = secrets.token_hex(16).upper()
        return f"REQ-GY-{random_hex_128bit}"

    @classmethod
    def generate_tracking_token(cls) -> str:
        """
        Generates a 256-bit cryptographically secure tracking token
        for verified customer status lookups.
        """
        return secrets.token_urlsafe(32)

    @classmethod
    def create_request(
        cls, req: CreateRegistrationRequest
    ) -> Tuple[bool, Optional[CustomerRequestCreatedResponse], Optional[str], int]:
        """
        Atomically validates, deduplicates, and creates a new registration request.
        Guaranteed atomic via SQLite transaction and partial unique index.
        Returns: (success, result, error_message, http_status_code)
        """
        cls._init_db()

        # Input validation
        is_valid, err_msg, normalized_domain = cls.validate_request_input(req)
        if not is_valid:
            return False, None, err_msg, 400

        now_iso = datetime.now(timezone.utc).isoformat()
        request_id = cls.generate_request_id()
        tracking_token = cls.generate_tracking_token()
        estimated_price = 45.0  # Standard accredited registrar rate

        try:
            with cls._get_connection() as conn:
                # Pre-check for duplicate active request to provide friendly details if available
                cursor = conn.execute(
                    """
                    SELECT request_id, status FROM registration_requests
                    WHERE domain = ? AND status IN ('pending', 'verification_required', 'verified_available', 'registration_in_progress')
                    LIMIT 1
                    """,
                    (normalized_domain,),
                )
                existing = cursor.fetchone()
                if existing:
                    return (
                        False,
                        None,
                        f"A registration request for '{normalized_domain}' is already active "
                        f"(Request ID: {existing['request_id']}, Status: {existing['status']}). "
                        f"Duplicate requests for the same domain are not accepted while active.",
                        409,
                    )

                # Atomic insert protected by SQLite unique partial index
                conn.execute(
                    """
                    INSERT INTO registration_requests (
                        request_id, tracking_token, domain, customer_name, customer_email, message,
                        status, estimated_annual_price, confirmed_price, currency,
                        admin_notes, confirmation_reference, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request_id,
                        tracking_token,
                        normalized_domain,
                        req.customer_name.strip(),
                        req.customer_email.strip().lower(),
                        req.message.strip() if req.message else None,
                        RegistrationRequestStatus.PENDING.value,
                        estimated_price,
                        None,
                        "USD",
                        None,
                        None,
                        now_iso,
                        now_iso,
                    ),
                )
                conn.commit()

        except sqlite3.IntegrityError:
            # Atomic database-level conflict caught
            return (
                False,
                None,
                f"A registration request for '{normalized_domain}' is already active. "
                f"Duplicate requests for the same domain are not accepted while active.",
                409,
            )

        response = CustomerRequestCreatedResponse(
            request_id=request_id,
            tracking_token=tracking_token,
            domain=normalized_domain,
            customer_name=req.customer_name.strip(),
            customer_email=req.customer_email.strip().lower(),
            status=RegistrationRequestStatus.PENDING,
            status_label=STATUS_LABELS[RegistrationRequestStatus.PENDING],
            estimated_annual_price=estimated_price,
            pricing_status="estimated",
            currency="USD",
            created_at=now_iso,
        )

        return True, response, None, 201

    @classmethod
    def get_public_request(cls, request_id: str) -> Optional[PublicRegistrationRequestResponse]:
        """
        Public tracking lookup. Strictly sanitized.
        NEVER returns customer name, email, message, or internal admin notes.
        """
        cls._init_db()
        clean_id = request_id.strip().upper()

        with cls._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT request_id, domain, status, estimated_annual_price, confirmed_price, currency, created_at, updated_at
                FROM registration_requests WHERE request_id = ?
                """,
                (clean_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            status_enum = RegistrationRequestStatus(row["status"])
            has_confirmed = row["confirmed_price"] is not None
            pricing_type = "confirmed" if has_confirmed else "estimated"
            pricing_amount = float(row["confirmed_price"]) if has_confirmed else float(row["estimated_annual_price"])

            return PublicRegistrationRequestResponse(
                request_id=row["request_id"],
                domain=row["domain"],
                status=status_enum,
                status_label=STATUS_LABELS.get(status_enum, "Unknown Status"),
                pricing_type=pricing_type,
                pricing_amount=pricing_amount,
                currency=row["currency"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    @classmethod
    def get_customer_verified_request(
        cls, request_id: str, tracking_token: str
    ) -> Optional[CustomerVerifiedRequestResponse]:
        """
        Returns full customer submission view if the customer provides their private tracking_token.
        Still excludes internal admin notes and private registrar liaison comments.
        """
        cls._init_db()
        clean_id = request_id.strip().upper()
        clean_token = tracking_token.strip()

        with cls._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT request_id, tracking_token, domain, customer_name, customer_email, message,
                       status, estimated_annual_price, confirmed_price, currency, created_at, updated_at
                FROM registration_requests WHERE request_id = ?
                """,
                (clean_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            # Constant-time comparison of tracking token
            if not secrets.compare_digest(row["tracking_token"], clean_token):
                return None

            status_enum = RegistrationRequestStatus(row["status"])
            has_confirmed = row["confirmed_price"] is not None

            return CustomerVerifiedRequestResponse(
                request_id=row["request_id"],
                domain=row["domain"],
                customer_name=row["customer_name"],
                customer_email=row["customer_email"],
                message=row["message"],
                status=status_enum,
                status_label=STATUS_LABELS.get(status_enum, "Unknown Status"),
                estimated_annual_price=float(row["estimated_annual_price"]),
                confirmed_price=float(row["confirmed_price"]) if has_confirmed else None,
                pricing_type="confirmed" if has_confirmed else "estimated",
                currency=row["currency"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                disclaimer="Submitting a request does NOT register, hold, or reserve the domain name.",
            )

    @classmethod
    def get_admin_request(cls, request_id: str) -> Optional[AdminRegistrationRequestResponse]:
        """Full request record for authenticated administrators."""
        cls._init_db()
        clean_id = request_id.strip().upper()

        with cls._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM registration_requests WHERE request_id = ?",
                (clean_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            status_enum = RegistrationRequestStatus(row["status"])
            has_confirmed = row["confirmed_price"] is not None

            return AdminRegistrationRequestResponse(
                request_id=row["request_id"],
                tracking_token=row["tracking_token"],
                domain=row["domain"],
                customer_name=row["customer_name"],
                customer_email=row["customer_email"],
                message=row["message"],
                status=status_enum,
                status_label=STATUS_LABELS.get(status_enum, "Unknown Status"),
                estimated_annual_price=float(row["estimated_annual_price"]),
                confirmed_price=float(row["confirmed_price"]) if has_confirmed else None,
                pricing_type="confirmed" if has_confirmed else "estimated",
                currency=row["currency"],
                admin_notes=row["admin_notes"],
                confirmation_reference=row["confirmation_reference"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                disclaimer="Submitting a request does NOT register, hold, or reserve the domain name.",
            )

    @classmethod
    def list_admin_requests(
        cls, status_filter: Optional[RegistrationRequestStatus] = None
    ) -> List[AdminRegistrationRequestResponse]:
        """Lists requests for authenticated administrators, ordered newest first."""
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
            results = []
            for row in rows:
                status_enum = RegistrationRequestStatus(row["status"])
                has_confirmed = row["confirmed_price"] is not None
                results.append(
                    AdminRegistrationRequestResponse(
                        request_id=row["request_id"],
                        tracking_token=row["tracking_token"],
                        domain=row["domain"],
                        customer_name=row["customer_name"],
                        customer_email=row["customer_email"],
                        message=row["message"],
                        status=status_enum,
                        status_label=STATUS_LABELS.get(status_enum, "Unknown Status"),
                        estimated_annual_price=float(row["estimated_annual_price"]),
                        confirmed_price=float(row["confirmed_price"]) if has_confirmed else None,
                        pricing_type="confirmed" if has_confirmed else "estimated",
                        currency=row["currency"],
                        admin_notes=row["admin_notes"],
                        confirmation_reference=row["confirmation_reference"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        disclaimer="Submitting a request does NOT register, hold, or reserve the domain name.",
                    )
                )
            return results

    @classmethod
    def update_request(
        cls, request_id: str, updates: UpdateRegistrationRequest
    ) -> Tuple[bool, Optional[AdminRegistrationRequestResponse], Optional[str], int]:
        """
        Updates an existing request status, confirmed price, admin notes, or confirmation reference.
        Enforces status integrity: 'registered' requires both confirmation notes and reference evidence.
        Returns: (success, updated_request, error_message, http_status_code)
        """
        cls._init_db()
        clean_id = request_id.strip().upper()
        existing = cls.get_admin_request(clean_id)
        if not existing:
            return False, None, f"Registration request '{request_id}' not found.", 404

        now_iso = datetime.now(timezone.utc).isoformat()

        # Target status
        target_status = updates.status if updates.status is not None else existing.status

        # REGISTRATION STATUS INTEGRITY CHECK:
        # 'registered' requires both an explicit confirmation note and registrar reference evidence
        if target_status == RegistrationRequestStatus.REGISTERED:
            notes = updates.admin_notes if updates.admin_notes is not None else existing.admin_notes
            ref = updates.confirmation_reference if updates.confirmation_reference is not None else existing.confirmation_reference

            if not ref or len(ref.strip()) < 3:
                return (
                    False,
                    None,
                    "Changing status to 'registered' requires confirmation reference/evidence "
                    "(e.g. University of Guyana Registry or accredited registrar receipt reference).",
                    422,
                )
            if not notes or len(notes.strip()) < 10:
                return (
                    False,
                    None,
                    "Changing status to 'registered' requires an explicit confirmation note (at least 10 characters).",
                    422,
                )

        new_status_str = target_status.value
        new_confirmed_price = (
            updates.confirmed_price if updates.confirmed_price is not None else existing.confirmed_price
        )
        new_admin_notes = (
            updates.admin_notes if updates.admin_notes is not None else existing.admin_notes
        )
        new_ref = (
            updates.confirmation_reference
            if updates.confirmation_reference is not None
            else existing.confirmation_reference
        )

        with cls._get_connection() as conn:
            conn.execute(
                """
                UPDATE registration_requests
                SET status = ?, confirmed_price = ?, admin_notes = ?, confirmation_reference = ?, updated_at = ?
                WHERE request_id = ?
                """,
                (new_status_str, new_confirmed_price, new_admin_notes, new_ref, now_iso, clean_id),
            )
            conn.commit()

        updated = cls.get_admin_request(clean_id)
        return True, updated, None, 200


# Ensure database and table initialization on load
RegistrationService._init_db()
