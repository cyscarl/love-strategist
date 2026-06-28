"""上下文摘要服务 —— 将历史聊天记录压缩为简短摘要。

用于三层 Token 优化策略中的"历史摘要"层：
将 30 条之前的对话压缩为 300 字以内的摘要，随滑动窗口更新。
"""

from loguru import logger

from src.services.llm_service import chat_completion
from src.storage.message_dao import get_before, get_recent
from src.storage.profile_dao import get_profile

# 系统提示词（摘要专用）
_SUMMARIZE_SYSTEM = """你是一个对话摘要助手。请将聊天记录压缩为一段 300 字以内的纯中文简短摘要。

要求：
1. 只保留关键信息：重要话题、双方态度变化、关系进展
2. 不要记录日常寒暄和琐碎内容
3. 使用自然的中文叙述，像前情提要
4. 突出转折点
5. 禁止使用任何英文单词，字数严格控制在 300 字以内"""


def summarize_history(contact_id: int, before_id: int = 0) -> str:
    """为指定联系人生成历史对话摘要。

    摘要涵盖指定 id 之前的对话。如果不指定 before_id，
    则摘要最近 N 条（窗口外）的所有对话。

    Args:
        contact_id: 联系人 id
        before_id: 分界消息 id，0 表示自动选择

    Returns:
        摘要文本（300 字以内），无历史消息时返回空字符串
    """
    from src.utils.config import get_skill_config
    config = get_skill_config()
    window = config.get("recent_window", 30)
    max_chars = config.get("summary_max_chars", 300)

    # 确定分界点：取第 window 条消息的 id
    if before_id == 0:
        recent = get_recent(contact_id, limit=window)
        if len(recent) <= window:
            return ""
        before_id = recent[0].id or 0

    # 获取历史消息（分界点之前）
    old_messages = get_before(contact_id, before_id, limit=200)

    if not old_messages:
        return ""

    # 构建消息文本
    lines = []
    for m in old_messages:
        role = "用户" if m.sender_type.value == "user" else "对方"
        lines.append(f"[{role}] {m.content}")

    conversation = "\n".join(lines)

    # 检查是否有旧摘要（增量更新）
    profile = get_profile(contact_id)
    old_summary = profile.summary if profile else ""

    if old_summary:
        user_prompt = (
            f"之前的摘要：\n{old_summary}\n\n"
            f"新增对话：\n{conversation}\n\n"
            f"请将上述内容合并更新为一段 {max_chars} 字以内的新摘要。"
        )
    else:
        user_prompt = (
            f"聊天记录：\n{conversation}\n\n"
            f"请将以上对话压缩为一段 {max_chars} 字以内的摘要。"
        )

    try:
        response, usage = chat_completion(
            messages=[
                {"role": "system", "content": _SUMMARIZE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,  # 摘要需要稳定
            max_tokens=max_chars,  # 300 字 ≈ 600 token 上限
        )

        # 截断确保不超过字数限制
        if len(response) > max_chars:
            response = response[:max_chars]

        logger.info(
            f"上下文摘要完成: contact={contact_id}, "
            f"messages={len(old_messages)}, "
            f"summary_len={len(response)}, "
            f"tokens={usage['total_tokens']}"
        )
        return response

    except Exception as e:
        logger.error(f"上下文摘要失败: contact={contact_id}, error={e}")
        return old_summary  # 失败时返回旧摘要
