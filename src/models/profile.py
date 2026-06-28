"""人物画像数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Profile:
    """联系人画像（从聊天记录中提炼的结构化特征）"""
    contact_id: int = 0
    basic_info: dict = field(default_factory=dict)        # {"age": 25, "occupation": "...", "city": "..."}
    personality: dict = field(default_factory=dict)        # {"traits": [...], "tags": [...]}
    hobbies: list = field(default_factory=list)            # ["摄影", "旅行", ...]
    behavior_patterns: dict = field(default_factory=dict)  # {"回复风格": "慢"}
    affinity_score: int = 0                                # -100 ~ 100
    summary: str = ""                                      # 精简摘要（供 LLM 使用）
    last_updated: Optional[datetime] = None

    def to_dict(self) -> dict:
        import json
        return {
            "contact_id": self.contact_id,
            "basic_info": json.dumps(self.basic_info, ensure_ascii=False),
            "personality": json.dumps(self.personality, ensure_ascii=False),
            "hobbies": json.dumps(self.hobbies, ensure_ascii=False),
            "behavior_patterns": json.dumps(self.behavior_patterns, ensure_ascii=False),
            "affinity_score": self.affinity_score,
            "summary": self.summary,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    @classmethod
    def from_row(cls, row: tuple) -> "Profile":
        """从数据库行创建 Profile 实例"""
        import json
        return cls(
            contact_id=row[0],
            basic_info=json.loads(row[1]) if row[1] else {},
            personality=json.loads(row[2]) if row[2] else {},
            hobbies=json.loads(row[3]) if row[3] else [],
            behavior_patterns=json.loads(row[4]) if row[4] else {},
            affinity_score=row[5] if row[5] is not None else 0,
            summary=row[6] or "",
            last_updated=datetime.fromisoformat(row[7]) if row[7] else None,
        )
