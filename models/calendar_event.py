from dataclasses import dataclass
from typing import Optional


@dataclass
class CalendarEvent:
    id: Optional[int] = None
    user_id: str = "default"
    source: str = "manual"
    title: str = ""
    start_time: str = ""
    end_time: str = ""
    is_busy: bool = True
    external_id: Optional[str] = None

    @classmethod
    def from_row(cls, row: dict) -> "CalendarEvent":
        return cls(
            id=row.get("id"),
            user_id=row.get("user_id", "default"),
            source=row.get("source", "manual"),
            title=row.get("title", ""),
            start_time=row.get("start_time", ""),
            end_time=row.get("end_time", ""),
            is_busy=bool(row.get("is_busy", 1)),
            external_id=row.get("external_id"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "source": self.source,
            "title": self.title,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "is_busy": self.is_busy,
            "external_id": self.external_id,
        }