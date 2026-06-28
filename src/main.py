"""Love Strategist - 聊天辅助工具

应用入口：依赖注入、Skill 注册、数据库初始化、启动 PyQt5 主窗口。

Phase 6 依赖注入链：
  SkillManager → ChatController → MainWindow
"""

import sys
import os

# 确保 src/ 在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from src.utils.logger import setup_logger, logger
from src.utils.config import load_config, ensure_directories
from src.storage.database import init_db
from src.skills.manager import skill_manager
from src.skills.builtin import BUILTIN_SKILLS
from src.controllers.chat_controller import ChatController
from src.ui.main_window import MainWindow


def _register_skills() -> None:
    """注册所有内置 Skill 到全局 SkillManager。"""
    existing = set(skill_manager.list_names())
    for cls in BUILTIN_SKILLS:
        if cls.name not in existing:
            skill_manager.register(cls())
    logger.info(f"已注册 {len(skill_manager.list_names())} 个 Skill")


def main() -> None:
    """应用主入口。"""
    # 1. 初始化日志
    setup_logger()
    logger.info("=" * 50)
    logger.info("Love Strategist 启动中...")

    # 2. 确保运行时目录
    ensure_directories()

    # 3. 加载配置
    config = load_config()
    logger.info(f"配置已加载，LLM 模型: {config.get('llm', {}).get('model', 'N/A')}")

    # 4. 初始化数据库
    init_db()

    # 5. 注册 Skill
    _register_skills()

    # 6. 启动 PyQt5
    app = QApplication(sys.argv)
    app.setApplicationName("Love Strategist")
    app.setOrganizationName("LoveStrategist")
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 7. 依赖注入：Controller → MainWindow
    controller = ChatController()
    window = MainWindow(controller=controller)
    window.show()

    logger.info("主窗口已显示")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
