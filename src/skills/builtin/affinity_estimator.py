"""好感度估算 Skill —— 综合分析对话，估算对方当前好感度。

评估维度：
1. 回复热情度（回复长度、使用表情、语气词）
2. 主动程度（主动开启话题、主动关心用户）
3. 话题参与度（对用户话题的投入程度）
4. 互动频率（消息数量）
5. 情感指标（正面/负面情感比例）
"""

import json
from src.skills.base import BaseSkill
from src.services.llm_service import chat_completion

_ESTIMATE_PROMPT = """你是一个人际关系分析师。请根据聊天记录估算对方的当前好感度。

好感度定义（-100 到 100）：
- -100 ~ -30：明显反感，回避或冷漠
- -30 ~ 0：略冷淡，但仍有基本礼貌
- 0 ~ 30：友好但保持距离，正常社交
- 30 ~ 60：有一定好感，愿意互动
- 60 ~ 80：明显好感，主动互动
- 80 ~ 100：非常强烈的兴趣和好感

评估信号：
- 正面信号：主动开启话题、回复详细、使用表情/语气词、关心用户、分享个人生活
- 负面信号：回复简短（1-2字）、长时间不回复、话题逃避、语气冷淡、不使用任何表情

严格按照以下 JSON 格式返回（不要包含 markdown 代码块标记，只返回纯 JSON）：

{
  "affinity": 35,
  "trend": "上升",
  "confidence": 0.7,
  "reasoning": "50字以内的分析理由"
}"""


class AffinityEstimator(BaseSkill):
    name = "AffinityEstimator"
    description = "好感度估算（结合情感和互动频率）"
    version = "1.0.0"

    def execute(self, context: dict) -> dict:
        """估算好感度。

        context 必需字段:
            recent_messages: list[dict] — 最近消息列表
        context 可选字段:
            current_affinity: int     — 当前好感度值
            message_count: int        — 总消息数
        """
        error = self.validate_context(context, ["recent_messages"])
        if error:
            return {"error": error}

        messages = context["recent_messages"]
        current = context.get("current_affinity", 0)
        msg_count = context.get("message_count", len(messages))

        # 构建对话文本
        lines = []
        for m in messages[-20:]:  # 只取最近 20 条
            role = "用户" if m.get("sender_type", "user") == "user" else "对方"
            lines.append(f"[{role}] {m.get('content', '')}")
        conversation = "\n".join(lines)

        user_prompt = (
            f"当前好感度参考值：{current}\n"
            f"总消息数：{msg_count}\n\n"
            f"最近对话：\n{conversation}\n\n"
            f"请分析对方的最新好感度并返回 JSON。"
        )

        try:
            response, usage = chat_completion(
                messages=[
                    {"role": "system", "content": _ESTIMATE_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=200,
            )

            data = self._parse_json(response)
            return {
                "affinity": data.get("affinity", current),
                "trend": data.get("trend", "持平"),
                "confidence": data.get("confidence", 0.5),
                "reasoning": data.get("reasoning", ""),
                "token_usage": usage,
            }

        except Exception as e:
            return {"error": str(e), "affinity": current, "trend": "持平", "confidence": 0.0}

    def get_prompt(self) -> str:
        return _ESTIMATE_PROMPT

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
