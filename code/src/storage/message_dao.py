"""消息 DAO（无时间戳 —— 只考虑消息内容和顺序）。

约定：
- 消息按 id 升序（旧在上，新在下），id 自增保证插入顺序
- 分页查询用 id 而非时间戳
"""

from typing import Optional

from loguru import logger

from src.models.message import Message
from src.models.enums import SenderType, ContentType
from .database import execute_query, execute_write, execute_insert


# ============================================================
# 写入
# ============================================================

def create_message(
    contact_id: int,
    sender_type: SenderType,
    content: str,
    content_type: ContentType = ContentType.TEXT,
) -> Message:
    msg_id = execute_insert(
        "INSERT INTO messages (contact_id, sender_type, content, content_type, is_edited) VALUES (?, ?, ?, ?, 0)",
        (contact_id, sender_type.value, content, content_type.value)
    )
    logger.debug(f"创建消息: id={msg_id}, contact={contact_id}, sender={sender_type.value}")
    return Message(
        id=msg_id, contact_id=contact_id, sender_type=sender_type,
        content=content, content_type=content_type, is_edited=False,
    )


def update_message(message_id: int, content: str) -> Optional[Message]:
    existing = get_message_by_id(message_id)
    if existing is None:
        logger.warning(f"更新消息失败: id={message_id} 不存在")
        return None
    execute_write("UPDATE messages SET content = ?, is_edited = 1 WHERE id = ?", (content, message_id))
    logger.debug(f"编辑消息: id={message_id}")
    return get_message_by_id(message_id)


def delete_message(message_id: int) -> bool:
    existing = get_message_by_id(message_id)
    if existing is None:
        return False
    execute_write("DELETE FROM messages WHERE id = ?", (message_id,))
    logger.debug(f"删除消息: id={message_id}")
    return True


def delete_messages_by_contact(contact_id: int) -> int:
    count = get_message_count(contact_id)
    execute_write("DELETE FROM messages WHERE contact_id = ?", (contact_id,))
    logger.info(f"批量删除消息: contact={contact_id}, count={count}")
    return count


# ============================================================
# 查询
# ============================================================

def get_message_by_id(message_id: int) -> Optional[Message]:
    rows = execute_query(
        "SELECT id, contact_id, sender_type, content, content_type, is_edited FROM messages WHERE id = ?",
        (message_id,)
    )
    if not rows:
        return None
    return Message.from_row(rows[0])


def get_recent(contact_id: int, limit: int = 50) -> list[Message]:
    """获取最近 N 条消息，按 id 升序（旧在上，新在下）。"""
    rows = execute_query(
        "SELECT id, contact_id, sender_type, content, content_type, is_edited FROM messages "
        "WHERE contact_id = ? ORDER BY id DESC LIMIT ?",
        (contact_id, limit)
    )
    messages = [Message.from_row(r) for r in rows]
    messages.reverse()
    return messages


def get_before(contact_id: int, before_id: int, limit: int = 50) -> list[Message]:
    """获取指定 id 之前的 N 条消息，按 id 升序。"""
    rows = execute_query(
        "SELECT id, contact_id, sender_type, content, content_type, is_edited FROM messages "
        "WHERE contact_id = ? AND id < ? ORDER BY id DESC LIMIT ?",
        (contact_id, before_id, limit)
    )
    messages = [Message.from_row(r) for r in rows]
    messages.reverse()
    return messages


def get_message_count(contact_id: int) -> int:
    rows = execute_query("SELECT COUNT(*) FROM messages WHERE contact_id = ?", (contact_id,))
    return rows[0][0] if rows else 0


def get_last_message(contact_id: int) -> Optional[Message]:
    rows = execute_query(
        "SELECT id, contact_id, sender_type, content, content_type, is_edited FROM messages "
        "WHERE contact_id = ? ORDER BY id DESC LIMIT 1",
        (contact_id,)
    )
    if not rows:
        return None
    return Message.from_row(rows[0])
