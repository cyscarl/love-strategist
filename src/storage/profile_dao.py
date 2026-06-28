"""人物画像 DAO —— 画像 CRUD 操作。

JSON 字段（basic_info / personality / hobbies / behavior_patterns）
在 DAO 层自动完成 dict ↔ JSON 字符串的序列化/反序列化。
上层代码只操作 Python 对象。
"""

import json
from datetime import datetime
from typing import Optional

from loguru import logger

from src.models.profile import Profile
from .database import execute_query, execute_write


def get_profile(contact_id: int) -> Optional[Profile]:
    """获取联系人的画像。

    Returns:
        Profile 对象，不存在则返回 None
    """
    rows = execute_query(
        """SELECT contact_id, basic_info, personality, hobbies,
                  behavior_patterns, affinity_score, summary, last_updated
           FROM profiles WHERE contact_id = ?""",
        (contact_id,)
    )
    if not rows:
        return None
    return Profile.from_row(rows[0])


def create_or_update_profile(
    contact_id: int,
    basic_info: Optional[dict] = None,
    personality: Optional[dict] = None,
    hobbies: Optional[list] = None,
    behavior_patterns: Optional[dict] = None,
    affinity_score: Optional[int] = None,
    summary: Optional[str] = None,
) -> Profile:
    """创建或更新人物画像。只更新传入的非 None 字段。

    若画像不存在则创建新记录（初始 affinity_score=0），
    已存在则合并更新。
    """
    existing = get_profile(contact_id)
    now = datetime.now().isoformat()

    if existing is None:
        # 新建画像
        bi = json.dumps(basic_info or {}, ensure_ascii=False)
        per = json.dumps(personality or {}, ensure_ascii=False)
        hob = json.dumps(hobbies or [], ensure_ascii=False)
        bp = json.dumps(behavior_patterns or {}, ensure_ascii=False)
        aff = affinity_score if affinity_score is not None else 0
        summ = summary or ""

        execute_write(
            """INSERT INTO profiles
               (contact_id, basic_info, personality, hobbies,
                behavior_patterns, affinity_score, summary, last_updated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (contact_id, bi, per, hob, bp, aff, summ, now)
        )
        logger.info(f"创建画像: contact_id={contact_id}, affinity={aff}")
    else:
        # 合并更新
        bi = json.dumps(basic_info, ensure_ascii=False) if basic_info is not None else None
        per = json.dumps(personality, ensure_ascii=False) if personality is not None else None
        hob = json.dumps(hobbies, ensure_ascii=False) if hobbies is not None else None
        bp = json.dumps(behavior_patterns, ensure_ascii=False) if behavior_patterns is not None else None
        aff = affinity_score
        summ = summary

        # 构建 SET 子句（只更新传入的字段）
        set_parts = []
        params = []

        if bi is not None:
            set_parts.append("basic_info = ?")
            params.append(bi)
        if per is not None:
            set_parts.append("personality = ?")
            params.append(per)
        if hob is not None:
            set_parts.append("hobbies = ?")
            params.append(hob)
        if bp is not None:
            set_parts.append("behavior_patterns = ?")
            params.append(bp)
        if aff is not None:
            set_parts.append("affinity_score = ?")
            params.append(aff)
        if summ is not None:
            set_parts.append("summary = ?")
            params.append(summ)

        set_parts.append("last_updated = ?")
        params.append(now)
        params.append(contact_id)

        if set_parts:
            sql = f"UPDATE profiles SET {', '.join(set_parts)} WHERE contact_id = ?"
            execute_write(sql, tuple(params))

        logger.debug(f"更新画像: contact_id={contact_id}")

    return get_profile(contact_id)


def delete_profile(contact_id: int) -> bool:
    """删除联系人的画像。

    Returns:
        True 表示删除成功，False 表示画像不存在
    """
    existing = get_profile(contact_id)
    if existing is None:
        return False
    execute_write("DELETE FROM profiles WHERE contact_id = ?", (contact_id,))
    logger.info(f"删除画像: contact_id={contact_id}")
    return True


def get_all_profiles() -> list[Profile]:
    """获取所有画像（用于批量操作或调试）。"""
    rows = execute_query(
        """SELECT contact_id, basic_info, personality, hobbies,
                  behavior_patterns, affinity_score, summary, last_updated
           FROM profiles"""
    )
    return [Profile.from_row(r) for r in rows]
