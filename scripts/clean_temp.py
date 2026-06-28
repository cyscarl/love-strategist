#!/usr/bin/env python3
"""清理临时文件脚本。

移除 temp/ 目录下的所有内容（保留目录结构）。
清理项目根目录下的 Python 缓存和临时文件。
"""

import os
import sys
import shutil
from pathlib import Path


def get_project_root() -> str:
    """获取项目根目录（code/ 的父目录）。"""
    code_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.dirname(code_dir)


def clean_temp_dir(project_root: str) -> int:
    """清空 temp/ 目录，保留子目录结构。"""
    temp_dir = os.path.join(project_root, "temp")
    if not os.path.exists(temp_dir):
        print(f"[SKIP] temp/ 目录不存在: {temp_dir}")
        return 0

    count = 0
    for root, dirs, files in os.walk(temp_dir, topdown=False):
        for f in files:
            path = os.path.join(root, f)
            try:
                os.remove(path)
                count += 1
            except OSError as e:
                print(f"[WARN] 无法删除: {path} ({e})")
        # 不删除子目录，只清空文件

    print(f"[OK] temp/ 已清理: 删除 {count} 个文件")
    return count


def clean_pycache(project_root: str) -> int:
    """清理 __pycache__ 目录。"""
    count = 0
    code_dir = os.path.join(project_root, "code")
    if not os.path.exists(code_dir):
        return 0
    for root, dirs, files in os.walk(code_dir):
        if "__pycache__" in dirs:
            path = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(path)
                count += 1
            except OSError as e:
                print(f"[WARN] 无法删除: {path} ({e})")
    if count:
        print(f"[OK] __pycache__ 已清理: {count} 个目录")
    return count


def clean_pytest_cache(project_root: str) -> int:
    """清理 .pytest_cache 目录。"""
    paths = [
        os.path.join(project_root, "code", ".pytest_cache"),
        os.path.join(project_root, ".pytest_cache"),
    ]
    count = 0
    for p in paths:
        if os.path.exists(p):
            try:
                shutil.rmtree(p)
                count += 1
                print(f"[OK] 已删除: {p}")
            except OSError as e:
                print(f"[WARN] 无法删除: {p} ({e})")
    return count


def clean_empty_dirs(project_root: str) -> None:
    """清理 temp/ 下的空子目录。"""
    temp_dir = os.path.join(project_root, "temp")
    if not os.path.exists(temp_dir):
        return
    for root, dirs, files in os.walk(temp_dir, topdown=False):
        if root != temp_dir and not os.listdir(root):
            try:
                os.rmdir(root)
                print(f"[OK] 已删除空目录: {root}")
            except OSError as e:
                print(f"[WARN] 无法删除: {root} ({e})")


def main() -> None:
    project_root = get_project_root()
    print(f"清理项目: {project_root}")
    print("-" * 40)

    files = clean_temp_dir(project_root)
    pycache = clean_pycache(project_root)
    pytest_cache = clean_pytest_cache(project_root)
    clean_empty_dirs(project_root)

    print("-" * 40)
    print(f"清理完成: 文件={files}, pycache={pycache}, pytest_cache={pytest_cache}")


if __name__ == "__main__":
    main()
