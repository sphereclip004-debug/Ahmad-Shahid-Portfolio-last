"""Password hashing, login throttling, and request security helpers."""
from __future__ import annotations
import hashlib, secrets, time
from collections import defaultdict, deque
from threading import Lock
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import HTTPException, Request

_password_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=2)
_DUMMY_PASSWORD_HASH = _password_hasher.hash("portfolio-invalid-account-dummy-password")
_attempts: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()
MAX_LOGIN_ATTEMPTS = 8
MAX_IP_LOGIN_ATTEMPTS = 24
LOGIN_WINDOW_SECONDS = 15 * 60

def hash_password(password: str) -> str:
    return _password_hasher.hash(password)

def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, ValueError):
        return False

def _keys(request: Request, username: str = "") -> tuple[str, str]:
    # Avoid retaining raw IP addresses in application memory or logs.
    address = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(address.encode("utf-8", "ignore")).hexdigest()
    account_hash = hashlib.sha256(f"{address}:{username.strip().lower()}".encode("utf-8", "ignore")).hexdigest()
    return f"ip:{ip_hash}", f"account:{account_hash}"

def _trim(q: deque[float], now: float) -> None:
    while q and now - q[0] > LOGIN_WINDOW_SECONDS:
        q.popleft()

def login_is_limited(request: Request, username: str = "") -> bool:
    ip_key, account_key = _keys(request, username)
    now = time.monotonic()
    with _lock:
        ip_q, account_q = _attempts[ip_key], _attempts[account_key]
        _trim(ip_q, now); _trim(account_q, now)
        return len(ip_q) >= MAX_IP_LOGIN_ATTEMPTS or len(account_q) >= MAX_LOGIN_ATTEMPTS

def record_login_failure(request: Request, username: str = "") -> None:
    ip_key, account_key = _keys(request, username)
    now = time.monotonic()
    with _lock:
        for key in (ip_key, account_key):
            q = _attempts[key]
            _trim(q, now)
            q.append(now)

def clear_login_failures(request: Request, username: str = "") -> None:
    # Clear only this account's failures; the per-IP bucket continues to dampen sprays
    # across many guessed usernames.
    _, account_key = _keys(request, username)
    with _lock:
        _attempts.pop(account_key, None)

def admin_username(request: Request) -> str:
    username = request.session.get("admin_username") if hasattr(request, "session") else None
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return str(username)

def require_csrf(request: Request) -> None:
    expected = request.session.get("csrf_token")
    supplied = request.headers.get("x-csrf-token", "")
    if not expected or not supplied or not secrets.compare_digest(str(expected), str(supplied)):
        raise HTTPException(status_code=403, detail="Request verification failed. Refresh and try again.")


def dummy_password_hash() -> str:
    return _DUMMY_PASSWORD_HASH
