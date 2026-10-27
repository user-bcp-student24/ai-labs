import base64
import hashlib
import hmac
import time


def make_token(
    username: str = "student",
    role: str = "STUDENT",
    expires_at: int | None = None,
    secret: str = "test-only-token-secret",
) -> str:
    expiry = expires_at if expires_at is not None else int(time.time()) + 3600
    payload = base64.b64encode(f"{username}|{role}|{expiry}".encode()).decode()
    signature = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{payload}.{signature}"
