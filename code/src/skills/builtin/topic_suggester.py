"""话题推荐 Skill —— 根据关系阶段和现有话题推荐新话题。

三个阶段：
1. 破冰期：初期相互了解，消除隔阂
2. 延续期：已有一定了解，延续互动
3. 深入期：关系进展，深入交流
"""

import json
from src.skills.base import BaseSkill
from src.services.llm_service import chat_completion

_SUGGEST_PROMPT = """你是一个社交话题顾问。请根据用户与对方的当前关系状态，推荐合适的话题。

严格按照以下 JSON 格式返回（不要包含 markdown 代码块标记，只返回纯 JSON）：

{
  "topics": [
    {"topic": "话题1", "stage": "破冰", "opener": "可以用这句话开启"},
    {"topic": "话题2", "stage": "延续", "opener": "可以用这句话延续"},
    {"topic": "话题3", "stage": "深入", "opener": "可以用这句话深入"}
  ],
  "stage": "破冰",
  "advice": "50字以内的策略建议"
}

话题推荐原则：
- icebreak（破冰）：轻松、无压力的话题，如日常趣事、共同环境、流行文化
- continue（延续）：基于已知信息的话题延伸，如对方兴趣爱好相关的讨论
- deepen（深入）：适度推进关系的话题，如价值观、未来规划、情感分享
- 话题应自然、不刻意，避免查户口式提问
- 根据对话节奏，不要急于推进"""


class TopicSuggester(BaseSkill):
    name = "TopicSuggester"
    description = "话题推荐（破冰/延续/深入）"
    version = "1.0.0"

    def execute(self, context: dict) -> dict:
        """生成话题推荐。

        context 可选字段:
            profile_summary: str      — 人物画像摘要
            relationship_stage: str  — 关系阶段（icebreak/continue/deepen）
            recent_topics: list[str] — 最近已聊过的话题
            extra_instruction: str   — 用户额外指令
        """
        profile = context.get("profile_summary", "暂无对方信息")
        stage = context.get("relationship_stage", "icebreak")
        recent = context.get("recent_topics", [])
        extra = context.get("extra_instruction", "")

        recent_str = "、".join(recent) if recent else "无记录"

        system_msg = _SUGGEST_PROMPT

        user_prompt = (
            f"对方画像：{profile}\n"
            f"当前关系阶段：{stage}\n"
            f"最近聊过的话题：{recent_str}\n"
        )
        if extra:
            user_prompt += f"用户特别说明：{extra}\n"
        user_prompt += "\n请推荐 3 个合适的话题并返回 JSON。"

        try:
            response, usage = chat_completion(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,
                max_tokens=300,
            )

            data = self._parse_json(response)
            return {
                "topics": data.get("topics", []),
                "stage": data.get("stage", stage),
                "advice": data.get("advice", ""),
                "token_usage": usage,
            }

        except Exception as e:
            return {"error": str(e), "topics": [], "stage": stage, "advice": ""}

    def get_prompt(self) -> str:
        return _SUGGEST_PROMPT

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                text = text[start:end]
        elif not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start:end + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}
