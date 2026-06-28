"""配置管理模块

加载/保存 config/config.yaml，首次启动自动从模板创建。
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger


def _get_project_root() -> str:
    """获取项目根目录（code/ 的父目录）。

    开发环境：从 code/src/utils/config.py 向上三级到 code/，再向上一级到项目根。
    打包环境：返回 exe 所在目录。
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # __file__ = code/src/utils/config.py
    # 向上 3 级到 code/，再向上 1 级到项目根
    return os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
        )
    )


def _get_code_dir() -> str:
    """获取 code/ 目录。"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )


# 路径常量
PROJECT_ROOT = _get_project_root()
CODE_DIR = _get_code_dir()
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.yaml")
# 模板在 _internal/ 内（打包）或 code/config/ 内（开发）
if getattr(sys, 'frozen', False):
    TEMPLATE_PATH = os.path.join(sys._MEIPASS, "config", "config.yaml.template")
else:
    TEMPLATE_PATH = os.path.join(CODE_DIR, "config", "config.yaml.template")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "love_strategist.db")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
TEMP_DIR = os.path.join(PROJECT_ROOT, "temp")


def _load_config() -> dict:
    """加载用户配置，若不存在则从模板创建。"""
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.exists(TEMPLATE_PATH):
            shutil.copy(TEMPLATE_PATH, CONFIG_PATH)
            logger.info(f"首次启动：已从模板创建配置文件 -> {CONFIG_PATH}")
        else:
            logger.warning(f"配置模板不存在: {TEMPLATE_PATH}，创建空白配置")
            return _default_config()

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _default_config() -> dict:
    """返回默认配置（极度保守）。"""
    return {
        "llm": {
            "api_key": "",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4",
            "timeout": 30,
            "max_tokens": 2048,
            "temperature": 0.8,
        },
        "ui": {
            "theme": "light",
            "language": "zh-CN",
            "window_width": 1000,
            "window_height": 700,
        },
        "skill": {
            "recent_window": 30,
            "summary_max_chars": 300,
            "default_mode": "silent",
            "enabled_skills": [
                "ReplyGenerator",
                "ProfileAnalyzer",
                "SentimentAnalyzer",
                "TopicSuggester",
                "AffinityEstimator",
            ],
        },
        "update": {
            "repo_url": "",
            "auto_check": False,
        },
    }


# 模块加载时读取配置
_config: Optional[dict] = None


def load_config() -> dict:
    """获取配置（懒加载，缓存读取结果）。"""
    global _config
    if _config is None:
        _config = _load_config()
    return _config


def save_config(config: dict) -> None:
    """保存用户配置到 config.yaml。"""
    global _config
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    _config = config
    logger.info("配置已保存")


def reload_config() -> dict:
    """强制重新加载配置（用于配置变更后刷新）。"""
    global _config
    _config = _load_config()
    return _config


def get_llm_config() -> dict:
    """获取 LLM 相关配置。"""
    return load_config().get("llm", {})


def get_ui_config() -> dict:
    """获取 UI 相关配置。"""
    return load_config().get("ui", {})


def get_skill_config() -> dict:
    """获取 Skill 相关配置。"""
    return load_config().get("skill", {})


def get_self_contact_id() -> int:
    """获取'自己'联系人 id。"""
    return load_config().get("self_contact_id", 0)


def set_self_contact_id(contact_id: int) -> None:
    """设置'自己'联系人 id。"""
    config = load_config()
    config["self_contact_id"] = contact_id
    save_config(config)


def ensure_directories() -> None:
    """确保运行时目录存在。"""
    for d in [DATA_DIR, LOG_DIR, TEMP_DIR]:
        os.makedirs(d, exist_ok=True)
