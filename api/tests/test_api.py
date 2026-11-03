import base64
import time
from pathlib import Path

import jwt
import pytest
import urllib3
from fastapi.testclient import TestClient

from app.main import create_app

TEST_JWT_SECRET = "test-only-key-with-at-least-32-bytes"
TEST_JWT_ISSUER = "https://test-issuer.invalid"
TEST_JWT_AUDIENCE = "test-api"


@pytest.fixture(autouse=True)
def configure_test_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKSHOP_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("WORKSHOP_JWT_ISSUER", TEST_JWT_ISSUER)
    monkeypatch.setenv("WORKSHOP_JWT_AUDIENCE", TEST_JWT_AUDIENCE)


def token(username: str = "student", role: str = "STUDENT") -> str:
    return jwt.encode(
        {
            "sub": username,
            "role": role,
            "iss": TEST_JWT_ISSUER,
            "aud": TEST_JWT_AUDIENCE,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )


def headers(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role)}"}


def test_lists_seeded_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_creates_task_and_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Add tests", "description": "Improve coverage", "status": "TODO", "priority": "HIGH"},
        )
        summary = client.get("/api/summary", headers=headers())
    assert created.status_code == 201
    assert created.json()["owner"] == "student"
    assert summary.json()["total"] == 3


def test_uploads_requirement(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"Login must be accessible", "text/plain")},
        )
    assert response.status_code == 201
    assert (upload_dir / "requirements.txt").exists()


def test_rejects_invalid_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "claim_overrides",
    [
        {"iss": "https://wrong-issuer.invalid"},
        {"aud": "wrong-api"},
        {"exp": int(time.time()) - 1},
        {"sub": ""},
        {"role": ["ADMIN"]},
    ],
)
def test_rejects_jwt_with_invalid_required_claims(
    tmp_path: Path,
    claim_overrides: dict[str, object],
) -> None:
    claims: dict[str, object] = {
        "sub": "student",
        "role": "STUDENT",
        "iss": TEST_JWT_ISSUER,
        "aud": TEST_JWT_AUDIENCE,
        "exp": int(time.time()) + 3600,
    }
    claims.update(claim_overrides)
    signed_token = jwt.encode(claims, TEST_JWT_SECRET, algorithm="HS256")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {signed_token}"},
        )
    assert response.status_code == 401


def test_rejects_legacy_base64_token(tmp_path: Path) -> None:
    legacy_payload = f"student|STUDENT|{int(time.time()) + 3600}|WORKSHOP_SECRET_2026"
    legacy_token = base64.b64encode(legacy_payload.encode()).decode()
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {legacy_token}"},
        )
    assert response.status_code == 401


def test_rejects_jwt_using_unapproved_algorithm(tmp_path: Path) -> None:
    unsigned_token = jwt.encode(
        {
            "sub": "student",
            "iss": TEST_JWT_ISSUER,
            "aud": TEST_JWT_AUDIENCE,
            "exp": int(time.time()) + 3600,
        },
        "",
        algorithm="none",
    )
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {unsigned_token}"},
        )
    assert response.status_code == 401


def test_rejects_jwt_exceeding_token_size_limit(tmp_path: Path) -> None:
    oversized_token = token() + ("x" * 8193)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {oversized_token}"},
        )
    assert response.status_code == 401


def test_reports_missing_jwt_configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKSHOP_JWT_SECRET")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 503
    assert response.json()["detail"] == "Authentication is not configured"


def test_rejects_bearer_token_with_invalid_signature(tmp_path: Path) -> None:
    signed_token = jwt.encode(
        {
            "sub": "student",
            "iss": TEST_JWT_ISSUER,
            "aud": TEST_JWT_AUDIENCE,
            "exp": int(time.time()) + 3600,
        },
        "different-test-key-with-at-least-32-bytes",
        algorithm="HS256",
    )
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {signed_token}"},
        )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_rejects_request_without_bearer_scheme(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Basic abc"})
    assert response.status_code == 401


def test_backend_health_preserves_success_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        status = 200
        data = b'{"status":"UP"}'

    class FakePoolManager:
        def request(self, method: str, url: str, timeout: float) -> FakeResponse:
            assert method == "GET"
            assert url == "http://auth.test/health"
            assert timeout == 3.0
            return FakeResponse()

    monkeypatch.setenv("AUTH_HEALTH_URL", "http://auth.test/health")
    monkeypatch.setattr("app.routes.urllib3.PoolManager", FakePoolManager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 200,
        "body": '{"status":"UP"}',
    }


def test_backend_health_hides_transport_error_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingPoolManager:
        def request(self, method: str, url: str, timeout: float) -> None:
            raise TimeoutError("sensitive connection details")

    monkeypatch.setattr("app.routes.urllib3.PoolManager", FailingPoolManager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 0,
        "body": "Backend health check failed",
    }
    assert "sensitive connection details" not in response.text


def test_rejects_jwt_configuration_with_short_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKSHOP_JWT_SECRET", "too-short")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 503


def test_task_values_with_quotes_are_stored_as_data(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Owner's task", "description": "Keep this literal"},
        )
    assert response.status_code == 201
    assert response.json()["title"] == "Owner's task"


def test_list_and_summary_reject_another_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        tasks = client.get("/api/tasks", params={"owner": "trainer"}, headers=headers())
        summary = client.get("/api/summary", params={"owner": "trainer"}, headers=headers())
    assert tasks.status_code == 403
    assert summary.status_code == 403


def test_create_task_rejects_another_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Assigned elsewhere", "owner": "trainer"},
        )
    assert response.status_code == 403


def test_create_task_rejects_invalid_field_types(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": ["not", "text"]},
        )
    assert response.status_code == 422


def test_upload_rejects_path_traversal_filename(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("../escaped.txt", b"requirement", "text/plain")},
        )
    assert response.status_code == 400
    assert not (tmp_path / "escaped.txt").exists()


def test_upload_rejects_unapproved_extension(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.exe", b"content", "application/octet-stream")},
        )
    assert response.status_code == 400
    assert not (upload_dir / "requirements.exe").exists()


def test_upload_rejects_content_over_size_limit(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    oversized_content = b"x" * (5 * 1024 * 1024 + 1)
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", oversized_content, "text/plain")},
        )
    assert response.status_code == 413
    assert not (upload_dir / "requirements.txt").exists()
