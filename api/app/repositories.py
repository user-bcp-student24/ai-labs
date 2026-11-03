from __future__ import annotations

import sqlite3
from typing import Any

from app.schemas import TaskCreate

TASK_COLUMNS = "id, title, description, status, owner, priority, created_at"
SEED_TASKS = (
    ("Refactor login", "Separar responsabilidades en frontend", "TODO", "student", "HIGH"),
    ("Review API", "Revisar seguridad de endpoints", "IN_PROGRESS", "student", "MEDIUM"),
    ("Trainer notes", "Preparar retrospectiva", "TODO", "trainer", "LOW"),
)


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS tasks ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, "
        "description TEXT NOT NULL, status TEXT NOT NULL, owner TEXT NOT NULL, "
        "priority TEXT NOT NULL, created_at TEXT NOT NULL)"
    )
    task_count = connection.execute("SELECT COUNT(*) AS total FROM tasks").fetchone()["total"]
    if task_count == 0:
        connection.executemany(
            "INSERT INTO tasks(title, description, status, owner, priority, created_at) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'))",
            SEED_TASKS,
        )
    connection.commit()


class TaskRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_by_owner(self, owner: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            f"SELECT {TASK_COLUMNS} FROM tasks WHERE owner = ? ORDER BY id",
            (owner,),
        ).fetchall()
        return [dict(row) for row in rows]

    def create(self, task: TaskCreate, owner: str) -> dict[str, Any]:
        cursor = self._connection.execute(
            "INSERT INTO tasks(title, description, status, owner, priority, created_at) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (task.title, task.description, task.status, owner, task.priority),
        )
        self._connection.commit()
        row = self._connection.execute(
            f"SELECT {TASK_COLUMNS} FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)

    def summary_rows(self, owner: str) -> list[sqlite3.Row]:
        return self._connection.execute(
            "SELECT status, priority FROM tasks WHERE owner = ?",
            (owner,),
        ).fetchall()