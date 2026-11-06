import hmac
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, Header, HTTPException, status

from app.core.config import settings
from app.services.registration_service import RegistrationService


def hash_password(password: str) -> str:
    """Computes HMAC-SHA256 hash using the secret key."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        password.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_password(plain_password: str, expected_password: str) -> bool:
    """Constant-time password verification supporting both hashed and configured passwords."""
    # Compare against direct config string or hashed version
    if secrets.compare_digest(plain_password, expected_password):
        return True
    expected_hash = hash_password(expected_password)
    provided_hash = hash_password(plain_password)
    return secrets.compare_digest(provided_hash, expected_hash)


class AdminSessionManager:
    """
    Manages server-side admin sessions stored persistently in SQLite.
    Sessions expire after ADMIN_SESSION_EXPIRE_HOURS.
    """

    @classmethod
    def _init_table(cls) -> None:
        with RegistrationService._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_sessions (
                    session_token TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_session_token ON admin_sessions(session_token)"
            )
            conn.commit()

    @classmethod
    def create_session(cls, username: str) -> Dict[str, Any]:
        cls._init_table()
        # 256 bits of cryptographically secure randomness
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=settings.ADMIN_SESSION_EXPIRE_HOURS)

        now_iso = now.isoformat()
        expires_iso = expires.isoformat()

        with RegistrationService._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO admin_sessions (session_token, username, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (token, username, now_iso, expires_iso),
            )
            conn.commit()

        return {
            "session_token": token,
            "username": username,
            "expires_at": expires_iso,
        }

    @classmethod
    def validate_session(cls, session_token: str) -> Optional[Dict[str, Any]]:
        cls._init_table()
        if not session_token or not session_token.strip():
            return None

        clean_token = session_token.strip()
        now_iso = datetime.now(timezone.utc).isoformat()

        with RegistrationService._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT session_token, username, created_at, expires_at
                FROM admin_sessions
                WHERE session_token = ? AND expires_at > ?
                """,
                (clean_token, now_iso),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "session_token": row["session_token"],
                "username": row["username"],
                "created_at": row["created_at"],
                "expires_at": row["expires_at"],
            }

    @classmethod
    def revoke_session(cls, session_token: str) -> bool:
        cls._init_table()
        if not session_token:
            return False

        with RegistrationService._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM admin_sessions WHERE session_token = ?",
                (session_token.strip(),),
            )
            conn.commit()
            return cursor.rowcount > 0


AdminSessionManager._init_table()


async def get_current_admin(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_admin_session: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """
    FastAPI dependency ensuring request is from an authenticated administrator.
    Rejects with HTTP 401 if unauthenticated, or HTTP 403 if unauthorized.
    """
    token: Optional[str] = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif x_admin_session:
        token = x_admin_session.strip()
    elif "admin_session" in request.cookies:
        token = request.cookies.get("admin_session")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHENTICATED",
                "message": "Admin authentication required. Please log in with admin credentials.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    session = AdminSessionManager.validate_session(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_SESSION",
                "message": "Admin session has expired or is invalid. Please log in again.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Authorization verification: username must match configured admin username
    if session["username"].lower() != settings.ADMIN_USERNAME.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "FORBIDDEN",
                "message": "Unauthorized: Admin privileges required.",
            },
        )

    return session
