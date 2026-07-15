from dataclasses import dataclass, field
from enum import Enum
from datetime import date, datetime
from typing import Optional


class TaskStatus(str, Enum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"


@dataclass
class Task:
    id: Optional[int] = None
    user_id: str = "default"
    category: str = ""
    description: str = ""
    estimated_minutes: int = 0
    calibrated_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    status: str = "todo"
    created_date: str = ""
    completed_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    sort_order: int = 0
    expansion_ratio: float = 1.0
    scheduled_start: Optional[str] = None
    scheduled_end: Optional[str] = None
    notes: str = ""

    @classmethod
    def from_row(cls, row: dict) -> "Task":
        return cls(
            id=row.get("id"),
            user_id=row.get("user_id", "default"),
            category=row.get("category", ""),
            description=row.get("description", ""),
            estimated_minutes=row.get("estimated_minutes", 0),
            calibrated_minutes=row.get("calibrated_minutes"),
            actual_minutes=row.get("actual_minutes"),
            status=row.get("status", "todo"),
            created_date=row.get("created_date", ""),
            completed_date=row.get("completed_date"),
            start_time=row.get("start_time"),
            end_time=row.get("end_time"),
            sort_order=row.get("sort_order", 0),
            scheduled_start=row.get("scheduled_start"),
            notes=row.get("notes", ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category": self.category,
            "description": self.description,
            "estimated_minutes": self.estimated_minutes,
            "calibrated_minutes": self.calibrated_minutes,
            "actual_minutes": self.actual_minutes,
            "status": self.status,
            "created_date": self.created_date,
            "completed_date": self.completed_date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "sort_order": self.sort_order,
            "expansion_ratio": self.expansion_ratio,
            "scheduled_start": self.scheduled_start,
            "scheduled_end": self.scheduled_end,
            "notes": self.notes,
        }