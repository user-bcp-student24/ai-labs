from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

import urllib3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.repositories import TaskRepository, initialize_database
from app.routes import create_api_router
from app.services import TaskService

logger = logging.getLogger(__name__)


def create_app(db_path: str | None = None, upload_dir: str | None = None) -> FastAPI:
    selected_db = db_path or os.getenv("WORKSHOP_DB_PATH", "./data/workshop.db")
    selected_uploads = upload_dir or os.getenv("WORKSHOP_UPLOAD_DIR", "./uploads")
    Path(selected_db).parent.mkdir(parents=True, exist_ok=True)
    Path(selected_uploads).mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(selected_db, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    initialize_database(connection)
    task_repository = TaskRepository(connection)
    task_service = TaskService(task_repository)

    app = FastAPI(title="Workshop Requirements API", version="0.1.0")
    app.state.connection = connection
    app.state.upload_dir = selected_uploads
    app.state.task_service = task_service
    app.include_router(create_api_router(task_service, Path(selected_uploads)))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("shutdown")
    def close_connection() -> None:
        connection.close()

    return app


app = create_app()
