"""枚举定义"""

from enum import Enum


class SenderType(str, Enum):
    """消息发送者类型"""
    USER = "user"
    TARGET = "target"


class ContentType(str, Enum):
    """消息内容类型"""
    TEXT = "text"
    IMAGE = "image"
    EMOJI = "emoji"


class SkillMode(str, Enum):
    """智能体工作模式"""
    SILENT = "silent"    # 静默模式：仅在召唤时生成建议
    ACTIVE = "active"    # 常开模式：后台持续监控并主动提醒
