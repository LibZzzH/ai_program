from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    id: str
    password_hash: str = ""
    name: str = ""
    email: str = ""
    avatar: str = ""
    created_at: str = ""

    @classmethod
    def from_row(cls, row: dict) -> "User":
        return cls(
            id=row.get("id", ""),
            password_hash=row.get("password_hash", ""),
            name=row.get("name", ""),
            email=row.get("email", ""),
            avatar=row.get("avatar", ""),
            created_at=row.get("created_at", ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "avatar": self.avatar,
            "created_at": self.created_at,
        }