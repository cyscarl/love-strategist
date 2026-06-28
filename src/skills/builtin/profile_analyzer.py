"""画像分析 Skill —— 基于 ex-skill 多层人格模型。

从聊天记录中蒸馏出 6 层人格特征：
  第1层：核心行为模式（说话风格、主动性、幽默感）
  第2层：身份特征（MBTI推断、依恋类型）
  第3层：表达方式（用词习惯、表情偏好、句式特征）
  第4层：情感行为（情绪波动、压力反应、亲密度）
  第5层：冲突模式（矛盾处理方式、边界意识）
  第6层：关系信号（兴趣指标、排斥信号、好感度趋势）

参考：ex-skill (GitHub 5.5k stars)、Anthropic Emotion Vectors 论文
"""

import json
from src.skills.base import BaseSkill
from src.services.llm_service import chat_completion

_ANALYZE_PROMPT = """你是一位顶尖的人际关系分析师。请基于聊天记录，按照以下六层模型分析"对方"的人格特征。

所有输出必须是纯中文，禁止任何英文单词。返回严格的JSON格式：

{
  "basic_info": {"年龄": "推测", "职业": "推测", "城市": "推测"},
  "personality": {
    "traits": ["外向", "细心"],
    "mbti_guess": "根据对话风格推断的MBTI类型（如ENFP/ISTJ等，不确定则留空）",
    "attachment_style": "安全型或焦虑型或回避型或混乱型（不确定则留空）"
  },
  "hobbies": ["从对话中提取的兴趣爱好"],
  "expression": {
    "说话风格": "简短直接或详细温柔或幽默调侃或理性分析",
    "常用词": ["高频词汇1", "高频词汇2"],
    "表情偏好": "爱用表情包或文字为主或emoji党",
    "句式特征": "反问多或陈述多或感叹多或省略多"
  },
  "emotion_patterns": {
    "情绪稳定性": "稳定或波动或敏感",
    "压力反应": "沉默或倾诉或转移话题或理性分析",
    "亲密度信号": "主动分享私事或保持距离或逐步开放"
  },
  "conflict_style": {
    "矛盾处理": "直接沟通或回避或妥协或冷战",
    "边界意识": "强或中等或弱"
  },
  "relationship_signals": {
    "好感度趋势": "上升中或稳定或下降中或数据不足",
    "兴趣指标": ["对话中表现出的兴趣信号"],
    "排斥信号": ["对话中表现出的排斥或疏远信号"],
    "关系阶段": "破冰期或了解期或深入期或亲密期"
  },
  "affinity_score": 0,
  "summary": "200字以内的纯中文关系总结与行动建议"
}

分析原则：
- affinity_score: -100到100。综合所有六层信号判断。对方主动、回复详细、情绪积极、分享私事、接受邀约均为正面信号
- 信息不足的字段返回空数组、空字符串或"数据不足"
- 基于对话内容推断，不做无依据的猜测
- MBTI仅在与对话风格明显吻合时填写"""


class ProfileAnalyzer(BaseSkill):
    name = "ProfileAnalyzer"
    description = "六层人格分析（基于 ex-skill 模型）"
    version = "2.0.0"

    def execute(self, context: dict) -> dict:
        error = self.validate_context(context, ["contact_name", "conversation_text"])
        if error:
            return {"error": error}

        name = context["contact_name"]
        conversation = context["conversation_text"]
        existing = context.get("existing_profile", {})

        existing_context = ""
        if existing:
            existing_context = f"当前画像参考：{json.dumps(existing, ensure_ascii=False, indent=2)}\n\n"

        user_prompt = (
            f"{existing_context}"
            f"联系人名称：{name}\n\n"
            f"对话记录：\n{conversation}\n\n"
            f"请基于上述六层模型进行全面分析并返回JSON。"
        )

        try:
            response, usage = chat_completion(
                messages=[
                    {"role": "system", "content": _ANALYZE_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            data = self._parse_json(response)
            return {
                "basic_info": data.get("basic_info", {}),
                "personality": data.get("personality", {}),
                "hobbies": data.get("hobbies", []),
                "expression": data.get("expression", {}),
                "emotion_patterns": data.get("emotion_patterns", {}),
                "conflict_style": data.get("conflict_style", {}),
                "relationship_signals": data.get("relationship_signals", {}),
                "affinity_score": data.get("affinity_score", 0),
                "summary": data.get("summary", ""),
                "token_usage": usage,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_prompt(self) -> str:
        return _ANALYZE_PROMPT

    @staticmethod
    def _parse_json(text: str) -> dict:
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
            return {}
