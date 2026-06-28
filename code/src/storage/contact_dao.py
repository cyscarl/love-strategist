"""联系人 DAO —— 联系人 CRUD 操作。

所有写操作通过 database.execute_write() 执行，自动加锁。
"""

from datetime import datetime
from typing import Optional

from loguru import logger

from src.models.contact import Contact
from .database import execute_query, execute_write, execute_insert


def create_contact(name: str, avatar: Optional[str] = None) -> Contact:
    """创建新联系人。

    Args:
        name: 联系人名称（必填）
        avatar: 头像路径或 base64（可选）

    Returns:
        新创建的 Contact 对象（含自增 id）
    """
    now = datetime.now().isoformat()
    contact_id = execute_insert(
        "INSERT INTO contacts (name, avatar, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (name, avatar, now, now)
    )
    logger.info(f"创建联系人: id={contact_id}, name={name}")
    return Contact(
        id=contact_id,
        name=name,
        avatar=avatar,
        created_at=datetime.fromisoformat(now),
        updated_at=datetime.fromisoformat(now),
    )


def get_contact_by_id(contact_id: int) -> Optional[Contact]:
    """按 ID 查询联系人。

    Returns:
        Contact 对象，不存在则返回 None
    """
    rows = execute_query(
        "SELECT id, name, avatar, notes, created_at, updated_at FROM contacts WHERE id = ?",
        (contact_id,)
    )
    if not rows:
        return None
    return Contact.from_row(rows[0])


def get_all_contacts() -> list[Contact]:
    """获取所有联系人，按更新时间倒序排列。"""
    rows = execute_query(
        "SELECT id, name, avatar, created_at, updated_at FROM contacts ORDER BY updated_at DESC"
    )
    return [Contact.from_row(r) for r in rows]


def update_contact(
    contact_id: int,
    name: Optional[str] = None,
    avatar: Optional[str] = None,
    notes: Optional[str] = None,
) -> Optional[Contact]:
    """更新联系人信息。只更新传入的非 None 字段。

    Returns:
        更新后的 Contact 对象，不存在则返回 None
    """
    existing = get_contact_by_id(contact_id)
    if existing is None:
        logger.warning(f"更新联系人失败: id={contact_id} 不存在")
        return None

    new_name = name if name is not None else existing.name
    new_avatar = avatar if avatar is not None else existing.avatar
    new_notes = notes if notes is not None else existing.notes
    now = datetime.now().isoformat()

    execute_write(
        "UPDATE contacts SET name = ?, avatar = ?, notes = ?, updated_at = ? WHERE id = ?",
        (new_name, new_avatar, new_notes, now, contact_id)
    )
    logger.info(f"更新联系人: id={contact_id}, name={new_name}")
    return get_contact_by_id(contact_id)


def delete_contact(contact_id: int) -> bool:
    """删除联系人（级联删除关联的消息和画像）。

    Returns:
        True 表示删除成功，False 表示联系人不存在
    """
    existing = get_contact_by_id(contact_id)
    if existing is None:
        logger.warning(f"删除联系人失败: id={contact_id} 不存在")
        return False

    execute_write("DELETE FROM contacts WHERE id = ?", (contact_id,))
    logger.info(f"删除联系人: id={contact_id}, name={existing.name}")
    return True


def contact_exists(contact_id: int) -> bool:
    """检查联系人是否存在。"""
    rows = execute_query("SELECT 1 FROM contacts WHERE id = ?", (contact_id,))
    return len(rows) > 0
