"""BaseSkill 抽象基类 —— 所有 Skill 必须继承此类。"""

from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """Skill 基类。

    子类必须定义:
        name: str        — 唯一标识符
        description: str — 功能描述
        version: str     — 版本号

    子类必须实现:
        execute(context) -> dict
        get_prompt() -> str
    """

    name: str = ""
    description: str = ""
    version: str = "1.0.0"

    @abstractmethod
    def execute(self, context: dict) -> dict:
        """执行 Skill。

        Args:
            context: 输入上下文字典，各 Skill 自行定义所需字段

        Returns:
            结果字典，结构由各 Skill 定义
        """
        ...

    @abstractmethod
    def get_prompt(self) -> str:
        """返回此 Skill 的系统提示词（注入 LLM 请求的 system message）。"""
        ...

    def validate_context(self, context: dict, required: list[str]) -> str | None:
        """校验 context 是否包含必需字段。

        Returns:
            错误信息字符串，校验通过返回 None
        """
        missing = [k for k in required if k not in context]
        if missing:
            return f"[{self.name}] 缺少必需字段: {', '.join(missing)}"
        return None
