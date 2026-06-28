"""回复生成 Skill v2.0 —— 多模式策略 + 情感感知。

基于 Anthropic 情感向量研究和 ex-skill 多层人格模型。
支持三大策略模式：
  破冰模式：轻松、好奇、逐步建立信任
  推进模式：分享、共鸣、适度展示价值
  维护模式：情绪支持、深度对话、巩固关系
"""

import json
from src.skills.base import BaseSkill
from src.services.llm_service import chat_completion

_STYLE_PROMPT = """你是一位顶级的情感策略顾问。请基于以下对话分析，生成3条高情商回复建议。

核心原则：
1. 回复风格自然、生活化，接近真实人际对话
2. 杜绝土味情话、油腻表达、查户口式提问
3. 根据关系阶段动态调整策略：
   - 破冰期：轻松话题为主，展示好奇心和幽默感，逐步了解对方
   - 了解期：基于已知信息深入对话，适当分享自己，创造共鸣
   - 深入期：情感交流增多，适度推进关系，提供情绪价值
   - 亲密期：自然流露关心，深度共情，建立独特连接感
4. 敏锐捕捉对方的情绪信号，正面情绪时顺势推进，负面情绪时先安抚再引导
5. 回复应自然融入对话语境，不要像模板
6. 联网感知：如果对话涉及热点事件、网络梗、流行文化、时事新闻，运用你的知识库中相关内容进行回应。当对方提起热门话题时，要能接住梗并顺势展开。如果完全不了解某个话题，诚实表示不太清楚而非强行编造。"""

_GENERATE_PROMPT = """根据以上对话分析和策略，请为"用户"生成3条回复建议。

所有内容必须为纯中文。返回严格的JSON格式：
{
  "suggestions": ["回复1", "回复2", "回复3"],
  "mode": "破冰或推进或维护",
  "reasoning": "30字以内的策略思路"
}

要求：
- 3条建议分别采用不同的策略角度（轻松破冰、深度共鸣、机智幽默）
- 每条15-50字，符合自然对话长度
- 如关系处于敏感期，优先考虑安全策略
- 回复要自然融入对话语境，不突兀
- 如果对话涉及热点话题、网络梗、流行文化，要给出懂梗的回应"""

_GENERATE_PROMPT = """根据以上对话分析和策略，请为"用户"生成3条回复建议。

所有内容必须为纯中文。返回严格的JSON格式：
{
  "suggestions": ["回复1", "回复2", "回复3"],
  "mode": "破冰或推进或维护",
  "reasoning": "30字以内的策略思路"
}

要求：
- 3条建议分别采用不同的策略角度（轻松破冰、深度共鸣、机智幽默）
- 每条15-50字，符合自然对话长度
- 如关系处于敏感期，优先考虑安全策略
- 回复要自然融入对话语境，不突兀"""


class ReplyGenerator(BaseSkill):
    name = "ReplyGenerator"
    description = "生成3条高情商回复（多模式策略 v2.0）"
    version = "2.0.0"

    def execute(self, context: dict) -> dict:
        error = self.validate_context(context, ["recent_messages"])
        if error:
            return {"error": error, "suggestions": []}

        system_parts = [_STYLE_PROMPT]

        profile = context.get("profile_summary", "")
        if profile:
            system_parts.append(f"\n对方六层人格画像：\n{profile}")

        history = context.get("history_summary", "")
        if history:
            system_parts.append(f"\n历史对话摘要：\n{history}")

        extra = context.get("extra_instruction", "")
        if extra:
            system_parts.append(f"\n用户特别指令（最高优先级）：{extra}")

        system_msg = "\n".join(system_parts)

        messages = context["recent_messages"]
        lines = []
        for m in messages:
            role = "用户" if m.get("sender_type", "user") == "user" else "对方"
            lines.append(f"[{role}] {m.get('content', '')}")
        conversation = "\n".join(lines)

        user_prompt = f"近期对话：\n{conversation}\n\n{_GENERATE_PROMPT}"

        try:
            response, usage = chat_completion(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.9,
            )

            data = self._parse_response(response)
            result = {
                "suggestions": data.get("suggestions", []),
                "reasoning": data.get("reasoning", ""),
                "mode": data.get("mode", ""),
                "token_usage": usage,
            }
            while len(result["suggestions"]) < 3:
                result["suggestions"].append("嗯嗯，我理解你的意思～")
            result["suggestions"] = result["suggestions"][:3]
            return result
        except Exception as e:
            return {"error": str(e), "suggestions": []}

    def get_prompt(self) -> str:
        return _STYLE_PROMPT

    @staticmethod
    def _parse_response(text: str) -> dict:
        text = text.strip()
        if "```json" in text:
            s = text.find("```json") + 7
            e = text.find("```", s)
            if e > s: text = text[s:e]
        elif "```" in text:
            s = text.find("```") + 3
            e = text.find("```", s)
            if e > s: text = text[s:e]
        if not text.startswith("{"):
            s = text.find("{"); e = text.rfind("}")
            if s >= 0 and e > s: text = text[s:e+1]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            lines = [l.strip().lstrip("123.）。 ").strip() for l in text.split("\n") if l.strip()]
            lines = [l for l in lines if len(l) >= 2][:3]
            return {"suggestions": lines, "reasoning": "", "mode": ""}
