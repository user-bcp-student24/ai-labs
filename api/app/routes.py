from __future__ import annotations

import logging
import os
from pathlib import Path

import urllib3
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.schemas import TaskCreate, TaskResponse, TaskSummaryResponse
from app.security import verified_identity
from app.services import TaskService
from app.storage import store_requirement

logger = logging.getLogger(__name__)


def create_api_router(task_service: TaskService, upload_dir: Path) -> APIRouter:
    router = APIRouter()

    def require_identity_owner(requested_owner: str | None, username: str) -> str:
        if requested_owner and requested_owner != username:
            raise HTTPException(status_code=403, detail="Not authorized for this owner")
        return username

    @router.get("/api/tasks", response_model=list[TaskResponse])
    def list_tasks(
        owner: str | None = Query(default=None),
        identity: dict[str, str] = Depends(verified_identity),
    ) -> list[dict[str, object]]:
        authenticated_owner = require_identity_owner(owner, identity["username"])
        return task_service.list_tasks(authenticated_owner)

    @router.post("/api/tasks", status_code=201, response_model=TaskResponse)
    def create_task(
        payload: TaskCreate,
        identity: dict[str, str] = Depends(verified_identity),
    ) -> dict[str, object]:
        authenticated_owner = require_identity_owner(payload.owner, identity["username"])
        return task_service.create_task(payload, authenticated_owner)

    @router.get("/api/summary", response_model=TaskSummaryResponse)
    def summary(
        owner: str | None = Query(default=None),
        identity: dict[str, str] = Depends(verified_identity),
    ) -> dict[str, object]:
        authenticated_owner = require_identity_owner(owner, identity["username"])
        return task_service.summarize(authenticated_owner)

    @router.post("/api/requirements", status_code=201)
    async def upload_requirement(
        file: UploadFile = File(...),
        identity: dict[str, str] = Depends(verified_identity),
    ) -> dict[str, str | int]:
        stored_file = await store_requirement(file, upload_dir)
        return {"owner": identity["username"], **stored_file}

    @router.get("/api/backend-health")
    def backend_health(identity: dict[str, str] = Depends(verified_identity)) -> dict[str, str | int]:
        url = os.getenv("AUTH_HEALTH_URL", "http://localhost:8080/q/health")
        try:
            response = urllib3.PoolManager().request("GET", url, timeout=3.0)
            body = response.data.decode("utf-8")
            return {"requestedBy": identity["username"], "status": response.status, "body": body}
        except (urllib3.exceptions.HTTPError, TimeoutError, UnicodeDecodeError):
            logger.warning("Backend health request failed", exc_info=True)
            return {
                "requestedBy": identity["username"],
                "status": 0,
                "body": "Backend health check failed",
            }

    return router