"""人物画像服务 v2.0 —— 六层人格模型（ex-skill风格）。"""

import json
from typing import Optional
from loguru import logger
from src.services.llm_service import chat_completion
from src.storage.message_dao import get_recent, get_message_count
from src.storage.profile_dao import get_profile, create_or_update_profile
from src.storage.contact_dao import get_contact_by_id


_PROFILE_ANALYZE_SYSTEM = """你是一位人际关系分析专家。请根据聊天记录分析对方特征，所有值为纯中文，返回JSON。"""


def update_profile(contact_id: int, force: bool = False) -> Optional[dict]:
    contact = get_contact_by_id(contact_id)
    if contact is None: return None

    messages = get_recent(contact_id, limit=50)
    if len(messages) < 5 and not force:
        logger.debug(f"画像更新跳过: contact={contact_id}, 消息不足 ({len(messages)})")
        return None

    lines = []
    for m in messages:
        role = "用户" if m.sender_type.value == "user" else "对方"
        lines.append(f"[{role}] {m.content}")
    conversation = "\n".join(lines)

    existing = get_profile(contact_id)
    existing_context = ""
    if existing and existing.summary:
        existing_context = f"当前画像摘要：{existing.summary}\n\n"

    user_prompt = (
        f"{existing_context}联系人名称：{contact.name}\n\n"
        f"最近对话：\n{conversation}\n\n请分析以上对话并返回JSON。"
    )

    try:
        response, usage = chat_completion(
            messages=[
                {"role": "system", "content": _PROFILE_ANALYZE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        data = _parse_profile_json(response)
        if data is None: return None

        profile = create_or_update_profile(
            contact_id=contact_id,
            basic_info=data.get("basic_info"),
            personality=data.get("personality"),
            hobbies=data.get("hobbies"),
            behavior_patterns=data.get("behavior_patterns"),
            affinity_score=data.get("affinity_score", 0),
            summary=data.get("summary", ""),
        )

        logger.info(
            f"画像更新完成: contact={contact_id}, affinity={profile.affinity_score}, "
            f"tokens={usage['total_tokens']}"
        )
        return {
            "affinity_score": profile.affinity_score,
            "basic_info": profile.basic_info,
            "personality": profile.personality,
            "hobbies": profile.hobbies,
            "behavior_patterns": profile.behavior_patterns,
            "summary": profile.summary,
        }
    except Exception as e:
        logger.error(f"画像更新失败: contact={contact_id}, error={e}")
        return None


def get_profile_summary(contact_id: int) -> str:
    """六层模型摘要：基本信息 + 性格MBTI + 依恋 + 关系阶段 + 好感度"""
    contact = get_contact_by_id(contact_id)
    profile = get_profile(contact_id)
    if contact is None: return ""
    name = contact.name
    if profile is None: return f"{name}，暂无画像信息。"

    parts = [name]
    bi = profile.basic_info
    if bi:
        items = []
        for k in ("年龄", "职业", "城市"):
            if bi.get(k): items.append(bi[k])
        if items: parts.append("，".join(items))

    per = profile.personality
    if per.get("traits"): parts.append("性格" + "、".join(per["traits"][:5]))
    if per.get("mbti_guess"): parts.append(f"似{per['mbti_guess']}")
    if per.get("attachment_style"): parts.append(f"依恋{per['attachment_style']}")

    if profile.hobbies: parts.append("爱好" + "、".join(profile.hobbies[:5]))

    bp = profile.behavior_patterns
    if isinstance(bp, dict):
        sig = bp.get("关系阶段", bp.get("relationship_signals", {}))
        if isinstance(sig, dict) and sig.get("关系阶段"): parts.append(sig["关系阶段"])
        elif isinstance(sig, str) and sig: parts.append(sig)

    parts.append(f"好感度{profile.affinity_score}")
    result = "，".join(parts) + "。"
    if profile.summary: result += f" {profile.summary}"
    return result


def estimate_affinity(contact_id: int) -> int:
    msg_count = get_message_count(contact_id)
    profile = get_profile(contact_id)
    current = profile.affinity_score if profile else 0
    if msg_count > 100: new_score = min(100, current + min(5, (msg_count - 100) // 20))
    elif msg_count < 10: new_score = current
    else: new_score = current
    if new_score != current: create_or_update_profile(contact_id, affinity_score=new_score)
    return new_score


def _parse_profile_json(text: str) -> Optional[dict]:
    if not text: return None
    if "```json" in text:
        s = text.find("```json") + 7; e = text.find("```", s)
        if e > s: text = text[s:e]
    elif "```" in text:
        s = text.find("```") + 3; e = text.find("```", s)
        if e > s: text = text[s:e]
    text = text.strip()
    if not text.startswith("{"):
        s = text.find("{"); e = text.rfind("}")
        if s >= 0 and e > s: text = text[s:e+1]
    try: return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {e}")
        return None
