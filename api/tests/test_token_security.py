import base64
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from token_factory import make_token


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def split_signed(token: str) -> tuple[str, str]:
    payload, signature = token.split(".")
    return payload, signature


def decoded_payload(payload: str) -> str:
    return base64.b64decode(payload).decode()


def encoded_payload(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def test_rejects_token_with_altered_role_under_original_signature(tmp_path: Path) -> None:
    payload, signature = split_signed(make_token("student", "STUDENT"))
    username, _, expiry = decoded_payload(payload).split("|")
    forged = f"{encoded_payload(f'{username}|ADMIN|{expiry}')}.{signature}"
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=auth_header(forged))
    assert response.status_code == 401


def test_rejects_forged_identity_that_would_access_another_owner(tmp_path: Path) -> None:
    payload, signature = split_signed(make_token("student", "STUDENT"))
    _, role, expiry = decoded_payload(payload).split("|")
    forged = f"{encoded_payload(f'trainer|{role}|{expiry}')}.{signature}"
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks?owner=trainer", headers=auth_header(forged))
    assert response.status_code == 401


def test_rejects_token_signed_with_a_different_secret(tmp_path: Path) -> None:
    forged = make_token("trainer", "TRAINER", secret="attacker-secret")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=auth_header(forged))
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token: invalid token"}


def test_rejects_legacy_unsigned_token_with_embedded_secret(tmp_path: Path) -> None:
    legacy = encoded_payload(f"trainer|TRAINER|{int(time.time()) + 3600}|WORKSHOP_SECRET_2026")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=auth_header(legacy))
    assert response.status_code == 401


def test_accepts_correctly_signed_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=auth_header(make_token()))
    assert response.status_code == 200


def test_app_startup_requires_token_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKSHOP_TOKEN_SECRET")
    with pytest.raises(RuntimeError, match="WORKSHOP_TOKEN_SECRET"):
        create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
