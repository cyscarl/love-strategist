"""SkillManager —— Skill 注册、发现、执行。

单例模式，统一管理所有 Skill 的生命周期。
支持通过配置文件启用/禁用 Skill。
"""

from typing import Optional

from loguru import logger

from src.utils.config import get_skill_config
from .base import BaseSkill


class SkillManager:
    """Skill 管理器（单例）。

    用法:
        mgr = SkillManager()
        mgr.register(ReplyGenerator())
        result = mgr.execute("ReplyGenerator", context)
    """

    _instance: Optional["SkillManager"] = None

    def __new__(cls) -> "SkillManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills: dict[str, BaseSkill] = {}
        return cls._instance

    # ------------------------------------------------------------------
    def register(self, skill: BaseSkill) -> None:
        """注册一个 Skill 实例。"""
        if not skill.name:
            raise ValueError("Skill.name 不能为空")

        if skill.name in self._skills:
            existing = self._skills[skill.name]
            logger.warning(
                f"Skill '{skill.name}' 已注册 (v{existing.version})，"
                f"将被 v{skill.version} 覆盖"
            )

        self._skills[skill.name] = skill
        logger.info(f"注册 Skill: {skill.name} v{skill.version} — {skill.description}")

    def get(self, name: str) -> Optional[BaseSkill]:
        """获取指定 Skill 实例。"""
        return self._skills.get(name)

    def list_all(self) -> list[dict]:
        """列出所有已注册的 Skill。

        Returns:
            [{"name": "ReplyGenerator", "description": "...", "enabled": True}, ...]
        """
        enabled = set(self._get_enabled_skills())
        return [
            {
                "name": s.name,
                "description": s.description,
                "version": s.version,
                "enabled": s.name in enabled,
            }
            for s in self._skills.values()
        ]

    def list_names(self) -> list[str]:
        """列出所有 Skill 名称。"""
        return list(self._skills.keys())

    def execute(self, name: str, context: dict) -> dict:
        """执行指定 Skill。

        Args:
            name: Skill 名称
            context: 输入上下文

        Returns:
            执行结果字典

        Raises:
            ValueError: Skill 未注册或被禁用
        """
        skill = self._skills.get(name)
        if skill is None:
            raise ValueError(f"Skill 未注册: {name}")

        if not self.is_enabled(name):
            raise ValueError(f"Skill 已禁用: {name}")

        logger.info(f"执行 Skill: {name}")
        try:
            result = skill.execute(context)
            logger.debug(f"Skill {name} 完成, keys={list(result.keys())}")
            return result
        except Exception as e:
            logger.error(f"Skill {name} 执行失败: {e}")
            raise

    def is_enabled(self, name: str) -> bool:
        """检查 Skill 是否在配置中启用。"""
        enabled = self._get_enabled_skills()
        # 如果配置为空或不存在，默认全部启用
        if not enabled:
            return True
        return name in enabled

    def _get_enabled_skills(self) -> list[str]:
        """从配置文件读取启用的 Skill 列表。"""
        config = get_skill_config()
        return config.get("enabled_skills", [])


# 全局单例
skill_manager = SkillManager()
