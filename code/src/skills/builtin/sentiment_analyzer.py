"""情感分析 Skill v2.0 —— 基于 Anthropic 情感向量研究。

检测维度：情感极性、情绪标签、强度、触发因素、心理机制。
参考：Anthropic Emotion Vectors Paper (2026)
"""

import json
from src.skills.base import BaseSkill
from src.services.llm_service import chat_completion

_ANALYZE_PROMPT = """你是一位情感分析专家。请分析对话中"对方"最新消息的情感状态。

所有输出必须为纯中文。返回严格的JSON格式：
{
  "sentiment": "正面或中性或负面",
  "score": 0.0,
  "emotion": "具体情绪标签",
  "intensity": "低或中或高",
  "trigger": "可能的情感触发因素（从对话上下文推断）",
  "mechanism": "可能的心理机制（如：投射、防御、寻求关注、情感压抑、真实表达等）",
  "advice": "针对当前情绪状态的30字以内的应对建议"
}

分析原则：
- score: 0.0到1.0，表示情感置信度
- emotion: 从以下选择最匹配的：开心、兴奋、平静、好奇、困惑、失望、难过、生气、焦虑、冷漠、尴尬、感动
- 基于语言线索分析，不做过度解读
- 避免将对方正常的简短回复误判为负面情绪"""


class SentimentAnalyzer(BaseSkill):
    name = "SentimentAnalyzer"
    description = "情感分析 v2.0（EIP情感向量+心理机制）"
    version = "2.0.0"

    def execute(self, context: dict) -> dict:
        error = self.validate_context(context, ["message_text"])
        if error:
            return {"error": error}

        msg = context["message_text"]
        recent = context.get("recent_context", "")

        user_prompt = f"待分析的消息（对方）：\n{msg}"
        if recent:
            user_prompt += f"\n\n上下文：\n{recent}"
        user_prompt += "\n\n请分析情感状态并返回JSON。"

        try:
            response, usage = chat_completion(
                messages=[
                    {"role": "system", "content": _ANALYZE_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=300,
            )
            data = self._parse_json(response)
            return {
                "sentiment": data.get("sentiment", "中性"),
                "score": data.get("score", 0.5),
                "emotion": data.get("emotion", ""),
                "intensity": data.get("intensity", "低"),
                "trigger": data.get("trigger", ""),
                "mechanism": data.get("mechanism", ""),
                "advice": data.get("advice", ""),
                "token_usage": usage,
            }
        except Exception as e:
            return {"error": str(e), "sentiment": "中性", "score": 0.0}

    def get_prompt(self) -> str:
        return _ANALYZE_PROMPT

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        if "```json" in text:
            s = text.find("```json") + 7
            e = text.find("```", s)
            if e > s: text = text[s:e]
        if not text.startswith("{"):
            s = text.find("{"); e = text.rfind("}")
            if s >= 0 and e > s: text = text[s:e+1]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"sentiment": "中性", "score": 0.0}
