from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any

import urllib3
from fastapi import Body, Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from .security import verify_token

TOKEN_SECRET_ENV = "WORKSHOP_TOKEN_SECRET"
ALLOWED_UPLOAD_EXTENSIONS = frozenset({".txt", ".md"})
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024


def legacy_identity(request: Request, authorization: str = Header(default="")) -> dict[str, str]:
    try:
        token = authorization.replace("Bearer ", "")
        return verify_token(token, request.app.state.token_secret, int(time.time()))
    except Exception as error:
        raise HTTPException(status_code=401, detail="Invalid token: " + str(error)) from error


def authorized_owner(requested_owner: str | None, identity: dict[str, str]) -> str:
    authenticated_owner = identity["username"]
    if requested_owner is not None and requested_owner != authenticated_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this owner",
        )
    return authenticated_owner


def safe_upload_target(upload_dir: str, original_filename: str | None) -> tuple[str, Path]:
    normalized_filename = Path((original_filename or "").replace("\\", "/")).name
    if not normalized_filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")
    if Path(normalized_filename).suffix.casefold() not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported file type")

    upload_root = Path(upload_dir).resolve()
    target = Path(upload_dir) / normalized_filename
    if not target.resolve().is_relative_to(upload_root):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")
    return normalized_filename, target


def create_app(db_path: str | None = None, upload_dir: str | None = None) -> FastAPI:
    token_secret = os.getenv(TOKEN_SECRET_ENV)
    if not token_secret:
        raise RuntimeError(f"{TOKEN_SECRET_ENV} is required")
    selected_db = db_path or os.getenv("WORKSHOP_DB_PATH", "./data/workshop.db")
    selected_uploads = upload_dir or os.getenv("WORKSHOP_UPLOAD_DIR", "./uploads")
    Path(selected_db).parent.mkdir(parents=True, exist_ok=True)
    Path(selected_uploads).mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(selected_db, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL, owner TEXT NOT NULL, priority TEXT NOT NULL, created_at TEXT NOT NULL)")
    count = connection.execute("SELECT COUNT(*) AS total FROM tasks").fetchone()["total"]
    if count == 0:
        connection.execute("INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Refactor login','Separar responsabilidades en frontend','TODO','student','HIGH',datetime('now'))")
        connection.execute("INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Review API','Revisar seguridad de endpoints','IN_PROGRESS','student','MEDIUM',datetime('now'))")
        connection.execute("INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Trainer notes','Preparar retrospectiva','TODO','trainer','LOW',datetime('now'))")
        connection.commit()

    app = FastAPI(title="Workshop Requirements API", version="0.1.0")
    app.state.connection = connection
    app.state.upload_dir = selected_uploads
    app.state.token_secret = token_secret
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def as_task(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "status": row["status"],
            "owner": row["owner"],
            "priority": row["priority"],
            "createdAt": row["created_at"],
        }

    @app.get("/api/tasks")
    def list_tasks(owner: str | None = Query(default=None), identity: dict[str, str] = Depends(legacy_identity)) -> list[dict[str, Any]]:
        requested_owner = authorized_owner(owner or None, identity)
        sql = "SELECT id,title,description,status,owner,priority,created_at FROM tasks WHERE owner='" + requested_owner + "' ORDER BY id"
        rows = connection.execute(sql).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            result.append(as_task(row))
        return result

    @app.post("/api/tasks", status_code=201)
    def create_task(payload: dict[str, Any] = Body(...), identity: dict[str, str] = Depends(legacy_identity)) -> dict[str, Any]:
        title = str(payload.get("title", ""))
        description = str(payload.get("description", ""))
        status = str(payload.get("status", "TODO"))
        priority = str(payload.get("priority", "MEDIUM"))
        requested_owner = payload.get("owner")
        owner = authorized_owner(str(requested_owner) if requested_owner is not None else None, identity)
        sql = "INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('" + title + "','" + description + "','" + status + "','" + owner + "','" + priority + "',datetime('now'))"
        cursor = connection.execute(sql)
        connection.commit()
        row = connection.execute("SELECT id,title,description,status,owner,priority,created_at FROM tasks WHERE id=" + str(cursor.lastrowid)).fetchone()
        return as_task(row)

    @app.get("/api/summary")
    def summary(owner: str | None = Query(default=None), identity: dict[str, str] = Depends(legacy_identity)) -> dict[str, Any]:
        requested_owner = authorized_owner(owner or None, identity)
        rows = connection.execute("SELECT status,priority FROM tasks WHERE owner='" + requested_owner + "'").fetchall()
        response: dict[str, Any] = {"owner": requested_owner, "total": 0, "byStatus": {}, "highPriorityOpen": 0}
        for row in rows:
            response["total"] = response["total"] + 1
            if row["status"] in response["byStatus"]:
                response["byStatus"][row["status"]] = response["byStatus"][row["status"]] + 1
            else:
                response["byStatus"][row["status"]] = 1
            if row["priority"] == "HIGH":
                if row["status"] != "DONE":
                    if row["status"] != "ARCHIVED":
                        response["highPriorityOpen"] = response["highPriorityOpen"] + 1
        return response

    @app.post("/api/requirements", status_code=201)
    async def upload_requirement(file: UploadFile = File(...), identity: dict[str, str] = Depends(legacy_identity)) -> dict[str, Any]:
        filename, target = safe_upload_target(selected_uploads, file.filename)
        content = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="File exceeds maximum allowed size",
            )
        target.write_bytes(content)
        return {"owner": identity["username"], "fileName": filename, "storedAt": str(target), "size": len(content)}

    @app.get("/api/backend-health")
    def backend_health(identity: dict[str, str] = Depends(legacy_identity)) -> dict[str, Any]:
        url = os.getenv("AUTH_HEALTH_URL", "http://localhost:8080/q/health")
        try:
            response = urllib3.PoolManager().request("GET", url, timeout=3.0)
            return {"requestedBy": identity["username"], "status": response.status, "body": response.data.decode("utf-8")}
        except Exception as error:
            return {"requestedBy": identity["username"], "status": 0, "body": str(error)}

    @app.on_event("shutdown")
    def close_connection() -> None:
        connection.close()

    return app


app = create_app()
