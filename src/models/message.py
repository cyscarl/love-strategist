"""消息数据模型（不含时间戳）。"""

from dataclasses import dataclass
from typing import Optional

from .enums import SenderType, ContentType


@dataclass
class Message:
    """聊天消息"""
    id: Optional[int] = None
    contact_id: int = 0
    sender_type: SenderType = SenderType.USER
    content: str = ""
    content_type: ContentType = ContentType.TEXT
    is_edited: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "contact_id": self.contact_id,
            "sender_type": self.sender_type.value,
            "content": self.content,
            "content_type": self.content_type.value,
            "is_edited": self.is_edited,
        }

    @classmethod
    def from_row(cls, row: tuple) -> "Message":
        return cls(
            id=row[0],
            contact_id=row[1],
            sender_type=SenderType(row[2]),
            content=row[3],
            content_type=ContentType(row[4]),
            is_edited=bool(row[5]) if len(row) > 5 else False,
        )
