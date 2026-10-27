import base64
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from token_factory import make_token

UPLOAD_SIZE_LIMIT_BYTES = 5 * 1024 * 1024


def token(username: str = "student", role: str = "STUDENT") -> str:
    return make_token(username, role)


def headers(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role)}"}


def test_lists_seeded_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert {"id", "title", "description", "status", "owner", "priority", "createdAt"} == set(response.json()[0])


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
    assert summary.json()["owner"] == "student"
    assert summary.json()["total"] == 3


def test_rejects_owner_overrides_from_authenticated_user(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        listed = client.get("/api/tasks", headers=headers(), params={"owner": "trainer"})
        summarized = client.get("/api/summary", headers=headers(), params={"owner": "trainer"})
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Unauthorized owner", "description": "Must stay private", "owner": "trainer"},
        )
    assert [listed.status_code, summarized.status_code, created.status_code] == [403, 403, 403]
    assert listed.json() == {"detail": "Not authorized to access this owner"}
    assert summarized.json() == {"detail": "Not authorized to access this owner"}
    assert created.json() == {"detail": "Not authorized to access this owner"}


def test_allows_owner_matching_authenticated_user(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        listed = client.get("/api/tasks", headers=headers(), params={"owner": "student"})
        summarized = client.get("/api/summary", headers=headers(), params={"owner": "student"})
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Owned task", "description": "Matches identity", "owner": "student"},
        )
    assert listed.status_code == 200
    assert summarized.status_code == 200
    assert summarized.json()["owner"] == "student"
    assert created.status_code == 201
    assert created.json()["owner"] == "student"


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
    assert response.json() == {
        "owner": "student",
        "fileName": "requirements.txt",
        "storedAt": str(upload_dir / "requirements.txt"),
        "size": len(b"Login must be accessible"),
    }
    assert (upload_dir / "requirements.txt").read_bytes() == b"Login must be accessible"


def test_uploads_markdown_requirement(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.md", b"# Requirements", "text/markdown")},
        )
    assert response.status_code == 201
    assert (upload_dir / "requirements.md").read_bytes() == b"# Requirements"


def test_normalizes_uploaded_filename_into_upload_directory(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("../outside.txt", b"Local test content", "text/plain")},
        )
    assert response.status_code == 201
    assert response.json()["fileName"] == "outside.txt"
    assert (upload_dir / "outside.txt").read_bytes() == b"Local test content"
    assert not (tmp_path / "outside.txt").exists()


def test_rejects_upload_with_unsupported_extension(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.exe", b"Local test content", "application/octet-stream")},
        )
    assert response.status_code == 415
    assert not (upload_dir / "requirements.exe").exists()


def test_rejects_upload_over_size_limit(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    oversized_content = b"x" * (UPLOAD_SIZE_LIMIT_BYTES + 1)
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("large.txt", oversized_content, "text/plain")},
        )
    assert response.status_code == 413
    assert not (upload_dir / "large.txt").exists()


@pytest.mark.parametrize(
    ("method", "path", "request_kwargs"),
    [
        ("get", "/api/tasks", {}),
        ("post", "/api/tasks", {"json": {}}),
        ("get", "/api/summary", {}),
        ("post", "/api/requirements", {"files": {"file": ("requirements.txt", b"x", "text/plain")}}),
        ("get", "/api/backend-health", {}),
    ],
    ids=["list-tasks", "create-task", "summary", "upload", "backend-health"],
)
def test_rejects_invalid_token_for_each_endpoint(
    tmp_path: Path,
    method: str,
    path: str,
    request_kwargs: dict[str, object],
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        request = getattr(client, method)
        response = request(path, headers={"Authorization": "Bearer invalid"}, **request_kwargs)
    assert response.status_code == 401
    assert response.json()["detail"].startswith("Invalid token:")


@pytest.mark.parametrize(
    "raw_token",
    [
        f"student|STUDENT|{int(time.time()) - 1}|WORKSHOP_SECRET_2026",
        "student|STUDENT",
    ],
    ids=["expired", "wrong-token-shape"],
)
def test_rejects_expired_or_malformed_token(tmp_path: Path, raw_token: str) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    encoded = base64.b64encode(raw_token.encode()).decode()
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": f"Bearer {encoded}"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token: invalid token"}


def test_empty_owner_filters_default_to_authenticated_user_and_empty_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    app.state.connection.execute("DELETE FROM tasks")
    app.state.connection.commit()
    with TestClient(app) as client:
        listed = client.get("/api/tasks?owner=", headers=headers())
        summary = client.get("/api/summary?owner=", headers=headers())
    assert listed.status_code == 200
    assert listed.json() == []
    assert summary.status_code == 200
    assert summary.json() == {
        "owner": "student",
        "total": 0,
        "byStatus": {},
        "highPriorityOpen": 0,
    }


def test_summary_excludes_done_and_archived_high_priority_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    for task_status in ("DONE", "ARCHIVED", "IN_PROGRESS"):
        app.state.connection.execute(
            "INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES (?,?,?,?,?,datetime('now'))",
            (f"High priority {task_status}", "Coverage case", task_status, "student", "HIGH"),
        )
    app.state.connection.commit()
    with TestClient(app) as client:
        response = client.get("/api/summary", headers=headers())
    assert response.status_code == 200
    assert response.json()["highPriorityOpen"] == 2
    assert response.json()["byStatus"] == {
        "TODO": 1,
        "IN_PROGRESS": 2,
        "DONE": 1,
        "ARCHIVED": 1,
    }


def test_creates_task_with_empty_object_defaults(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json={})
    assert response.status_code == 201
    assert response.json()["title"] == ""
    assert response.json()["description"] == ""
    assert response.json()["status"] == "TODO"
    assert response.json()["priority"] == "MEDIUM"
    assert response.json()["owner"] == "student"


@pytest.mark.parametrize(
    ("include_body", "payload"),
    [(False, None), (True, [])],
    ids=["missing-body", "non-object-body"],
)
def test_rejects_missing_or_non_object_task_body(
    tmp_path: Path,
    include_body: bool,
    payload: object,
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        request_kwargs = {"json": payload} if include_body else {}
        response = client.post("/api/tasks", headers=headers(), **request_kwargs)
    assert response.status_code == 422
    assert response.json()["detail"]


def test_database_errors_return_internal_server_error_for_task_routes(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    app.state.connection.close()
    with TestClient(app, raise_server_exceptions=False) as client:
        listed = client.get("/api/tasks", headers=headers())
        created = client.post("/api/tasks", headers=headers(), json={"title": "Broken DB"})
        summary = client.get("/api/summary", headers=headers())
    assert [listed.status_code, created.status_code, summary.status_code] == [500, 500, 500]
    assert [listed.text, created.text, summary.text] == [
        "Internal Server Error",
        "Internal Server Error",
        "Internal Server Error",
    ]


def test_upload_accepts_empty_file_and_case_insensitive_extension(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("empty.TXT", b"", "application/octet-stream")},
        )
    assert response.status_code == 201
    assert response.json()["fileName"] == "empty.TXT"
    assert response.json()["size"] == 0
    assert (upload_dir / "empty.TXT").read_bytes() == b""


def test_upload_accepts_file_at_exact_size_limit(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    content = b"x" * UPLOAD_SIZE_LIMIT_BYTES
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("limit.txt", content, "text/plain")},
        )
    assert response.status_code == 201
    assert response.json()["size"] == UPLOAD_SIZE_LIMIT_BYTES
    assert (upload_dir / "limit.txt").read_bytes() == content


def test_upload_rejects_filename_without_extension(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements", b"x", "text/plain")},
        )
    assert response.status_code == 415
    assert response.json() == {"detail": "Unsupported file type"}


def test_upload_rejects_empty_normalized_filename(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": (".", b"x", "text/plain")},
        )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid filename"}


def test_upload_rejects_path_resolving_outside_upload_directory(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    original_resolve = Path.resolve

    def resolve_with_escape(path: Path, *args: object, **kwargs: object) -> Path:
        if path.name == "escape.txt" and path.parent == upload_dir:
            return tmp_path / "escape.txt"
        return original_resolve(path, *args, **kwargs)

    with patch("app.main.Path.resolve", new=resolve_with_escape):
        with TestClient(app) as client:
            response = client.post(
                "/api/requirements",
                headers=headers(),
                files={"file": ("escape.txt", b"x", "text/plain")},
            )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid filename"}


def test_upload_requires_file_field(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/requirements", headers=headers())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_upload_write_error_returns_internal_server_error(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with patch("pathlib.Path.write_bytes", side_effect=OSError("test filesystem failure")):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/requirements",
                headers=headers(),
                files={"file": ("requirements.txt", b"requirement", "text/plain")},
            )
    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_backend_health_returns_upstream_status_and_body(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with patch("app.main.urllib3.PoolManager") as pool:
        pool.return_value.request.return_value.status = 200
        pool.return_value.request.return_value.data = b'{"healthy":true}'
        with TestClient(app) as client:
            response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 200,
        "body": '{"healthy":true}',
    }


def test_backend_health_reports_upstream_error_without_changing_api_status(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with patch("app.main.urllib3.PoolManager") as pool:
        pool.return_value.request.return_value.status = 503
        pool.return_value.request.return_value.data = b"Service Unavailable"
        with TestClient(app) as client:
            response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 503,
        "body": "Service Unavailable",
    }


def test_backend_health_reports_upstream_exception_without_leaking_as_http_error(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with patch("app.main.urllib3.PoolManager") as pool:
        pool.return_value.request.side_effect = TimeoutError("local timeout")
        with TestClient(app) as client:
            response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 0,
        "body": "local timeout",
    }
