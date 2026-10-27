import base64
import hashlib
import hmac


def verify_token(token: str, secret: str, now: int) -> dict[str, str]:
    payload_segment, _, signature = token.partition(".")
    if not payload_segment or not signature:
        raise ValueError("invalid token")
    if not is_valid_signature(payload_segment, signature, secret):
        raise ValueError("invalid token")

    parts = base64.b64decode(payload_segment).decode("utf-8").split("|")
    if len(parts) != 3:
        raise ValueError("invalid token")
    username, role, expiry = parts
    if int(expiry) < now:
        raise ValueError("invalid token")
    return {"username": username, "role": role}


def is_valid_signature(payload_segment: str, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode("utf-8"), payload_segment.encode("utf-8"), hashlib.sha256).digest()
    expected_segment = base64.urlsafe_b64encode(expected).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(signature, expected_segment)
