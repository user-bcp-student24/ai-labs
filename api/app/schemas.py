from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    title: str = ""
    description: str = ""
    status: str = "TODO"
    priority: str = "MEDIUM"
    owner: str | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    title: str
    description: str
    status: str
    owner: str
    priority: str
    created_at: str = Field(alias="createdAt")


class TaskSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    owner: str
    total: int
    by_status: dict[str, int] = Field(alias="byStatus")
    high_priority_open: int = Field(alias="highPriorityOpen")