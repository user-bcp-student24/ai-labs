from __future__ import annotations

from app.repositories import TaskRepository
from app.schemas import TaskCreate


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def list_tasks(self, owner: str) -> list[dict[str, object]]:
        return self._repository.list_by_owner(owner)

    def create_task(self, task: TaskCreate, owner: str) -> dict[str, object]:
        return self._repository.create(task, owner)

    def summarize(self, owner: str) -> dict[str, object]:
        summary: dict[str, object] = {
            "owner": owner,
            "total": 0,
            "byStatus": {},
            "highPriorityOpen": 0,
        }
        by_status: dict[str, int] = summary["byStatus"]
        for row in self._repository.summary_rows(owner):
            status = row["status"]
            by_status[status] = by_status.get(status, 0) + 1
            summary["total"] = summary["total"] + 1
            if row["priority"] == "HIGH" and status not in {"DONE", "ARCHIVED"}:
                summary["highPriorityOpen"] = summary["highPriorityOpen"] + 1
        return summary