"""日志模块（基于 loguru）。

- 开发环境：日志输出到控制台 + 文件
- 打包环境 (console=False)：仅输出到文件
- 启动时自动清理 7 天前的日志
- 全局异常钩子：PyQt 槽函数中的异常不再被静默吞掉，
  而是写入 crash.log + 弹窗提示用户
"""

import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger

from .config import LOG_DIR


def _cleanup_old_logs(log_dir: str, days: int = 7) -> int:
    """删除 N 天前的日志文件。返回删除数量。"""
    if not os.path.exists(log_dir):
        return 0
    cutoff = time.time() - days * 86400
    count = 0
    for f in os.listdir(log_dir):
        path = os.path.join(log_dir, f)
        if os.path.isfile(path) and f.endswith(".log"):
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
                    count += 1
            except OSError:
                pass
    if count:
        logger.info(f"已清理 {count} 个过期日志文件（>{days}天）")
    return count


def _install_excepthook() -> None:
    """安装全局异常钩子，捕获 PyQt 槽函数中未被处理的异常。"""
    original_hook = sys.excepthook

    def _handle_exception(exc_type, exc_value, exc_tb):
        # 记录到日志文件
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.error(f"未捕获的异常:\n{tb_text}")

        # 写入独立的崩溃日志
        crash_dir = os.path.join(LOG_DIR, "crashes")
        os.makedirs(crash_dir, exist_ok=True)
        crash_file = os.path.join(
            crash_dir,
            f"crash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        with open(crash_file, "w", encoding="utf-8") as f:
            f.write(f"崩溃时间: {datetime.now().isoformat()}\n")
            f.write(f"异常类型: {exc_type.__name__}\n")
            f.write(f"异常信息: {exc_value}\n\n")
            f.write("堆栈跟踪:\n")
            f.write(tb_text)

        # 尝试弹窗提示用户
        try:
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("程序异常")
            msg.setText(f"发生了一个错误：\n{exc_value}")
            msg.setDetailedText(tb_text)
            msg.setInformativeText(f"详细日志已保存到:\n{crash_file}")
            msg.exec_()
        except Exception:
            pass

        # 调用原始 hook
        original_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _handle_exception


def export_logs() -> str:
    """导出最近 200 行日志到桌面，返回文件路径。"""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    export_path = os.path.join(
        desktop,
        f"love_strategist_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    log_file = os.path.join(LOG_DIR, "love_strategist.log")

    lines = []
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            lines = all_lines[-200:]  # 最近 200 行

    with open(export_path, "w", encoding="utf-8") as f:
        f.write(f"Love Strategist 日志导出\n")
        f.write(f"导出时间: {datetime.now().isoformat()}\n")
        f.write(f"{'=' * 60}\n\n")
        f.writelines(lines)

    return export_path


def setup_logger() -> None:
    """初始化日志配置。"""
    # 移除默认 handler
    logger.remove()

    # 确保日志目录存在
    os.makedirs(LOG_DIR, exist_ok=True)

    # 清理过期日志
    _cleanup_old_logs(LOG_DIR, days=7)

    # 文件日志（始终开启）
    logger.add(
        os.path.join(LOG_DIR, "love_strategist.log"),
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    )

    # 控制台输出（仅在开发环境或 console=True 时开启）
    if sys.stderr is not None:
        logger.add(
            sys.stderr,
            level="INFO",
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        )

    # 安装全局异常钩子
    _install_excepthook()

    logger.info("日志系统初始化完成")
