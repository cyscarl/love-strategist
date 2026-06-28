"""联系人数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Contact:
    """联系人"""
    id: Optional[int] = None
    name: str = ""
    avatar: Optional[str] = None          # 头像路径或 base64
    notes: str = ""                       # 用户自定义备注（不影响 AI 决策）
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "avatar": self.avatar,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_row(cls, row: tuple) -> "Contact":
        """从数据库行创建 Contact 实例。兼容带/不带 notes 列的旧数据。"""
        return cls(
            id=row[0],
            name=row[1],
            avatar=row[2],
            notes=row[3] if len(row) > 3 else "",
            created_at=datetime.fromisoformat(row[4]) if len(row) > 4 and row[4] else None,
            updated_at=datetime.fromisoformat(row[5]) if len(row) > 5 and row[5] else None,
        )
