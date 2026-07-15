from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BadgeCategory:
    id: str
    name: str
    desc: str
    color: str

    @classmethod
    def from_dict(cls, d: dict) -> "BadgeCategory":
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            desc=d.get("desc", ""),
            color=d.get("color", ""),
        )


@dataclass
class Achievement:
    id: str
    name: str
    emoji: str
    desc: str
    category: str
    earned: bool = False
    earned_at: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "Achievement":
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            emoji=d.get("emoji", ""),
            desc=d.get("desc", ""),
            category=d.get("category", ""),
            earned=d.get("earned", False),
            earned_at=d.get("earned_at"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "emoji": self.emoji,
            "desc": self.desc,
            "category": self.category,
            "earned": self.earned,
            "earned_at": self.earned_at,
        }


@dataclass
class StreakLog:
    id: Optional[int] = None
    user_id: str = "default"
    task_date: str = ""
    done_count: int = 1
    created_at: str = ""

    @classmethod
    def from_row(cls, row: dict) -> "StreakLog":
        return cls(
            id=row.get("id"),
            user_id=row.get("user_id", "default"),
            task_date=row.get("task_date", ""),
            done_count=row.get("done_count", 1),
            created_at=row.get("created_at", ""),
        )