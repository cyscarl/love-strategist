"""GitHub 更新检查服务。

从 GitHub Releases API 获取最新版本、下载并解压更新。
"""

import re
import os
import sys
import zipfile
import shutil
import tempfile
import requests
from loguru import logger


def _parse_version(v: str) -> tuple:
    v = v.strip().lstrip("vV")
    try:
        return tuple(int(x) for x in v.split(".")[:3])
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _version_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def check_github_update(repo_url: str, current_version: str) -> dict | None:
    """查询 GitHub Releases 最新版本。"""
    if not repo_url:
        return None

    m = re.search(r'github\.com/([^/]+)/([^/]+?)(?:\.git)?$', repo_url.rstrip("/"))
    if not m:
        logger.warning(f"无法解析 GitHub 仓库 URL: {repo_url}")
        return None

    owner, repo = m.group(1), m.group(2)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

    try:
        resp = requests.get(api_url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "LoveStrategist",
        }, timeout=8)

        if resp.status_code != 200:
            logger.warning(f"GitHub API 返回 {resp.status_code}: {resp.text[:100]}")
            return None

        data = resp.json()
        latest_tag = data.get("tag_name", "")
        if not latest_tag:
            return None

        if not _version_newer(latest_tag, current_version):
            return None

        # 获取 zip 下载链接
        zip_url = data.get("zipball_url", "")
        if not zip_url:
            # 查找 assets 中的 zip 文件
            for asset in data.get("assets", []):
                if asset.get("name", "").endswith(".zip"):
                    zip_url = asset.get("browser_download_url", "")
                    break

        return {
            "latest": latest_tag,
            "url": data.get("html_url", repo_url + "/releases/latest"),
            "zip_url": zip_url,
            "body": (data.get("body", "") or "")[:200],
        }

    except requests.exceptions.Timeout:
        logger.warning("GitHub API 超时")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("GitHub API 连接失败")
        return None
    except Exception as e:
        logger.warning(f"检查更新失败: {e}")
        return None


def download_and_update(zip_url: str, callback=None) -> tuple[bool, str]:
    """下载 zip 并准备更新。

    流程：下载 → 解压到临时目录 → 创建替换脚本 → 提示用户重启。
    返回 (成功, 消息)。
    """
    if not zip_url:
        return False, "没有可下载的更新包"

    try:
        # 确定应用目录
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 下载 zip
        tmp_dir = tempfile.mkdtemp(prefix="love_update_")
        zip_path = os.path.join(tmp_dir, "update.zip")

        if callback:
            callback("下载中...")

        resp = requests.get(zip_url, headers={"User-Agent": "LoveStrategist"}, timeout=120, stream=True)
        if resp.status_code != 200:
            return False, f"下载失败 (HTTP {resp.status_code})"

        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if callback and total:
                    pct = min(99, int(downloaded / total * 100))
                    callback(f"下载中... {pct}%")

        if callback:
            callback("解压中...")

        # 解压
        extract_dir = os.path.join(tmp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # GitHub zip 解压后有一层目录（owner-repo-hash），取第一个子目录
        items = os.listdir(extract_dir)
        if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
            source_dir = os.path.join(extract_dir, items[0])
        else:
            source_dir = extract_dir

        # 新版本目录
        new_dir = app_dir + "_new"

        # 如果已有旧的新版本目录，删除
        if os.path.exists(new_dir):
            shutil.rmtree(new_dir)

        # 复制文件到新目录
        shutil.copytree(source_dir, new_dir)

        # 创建更新批处理脚本
        bat_path = os.path.join(os.path.dirname(app_dir), "_update.bat")
        app_name = os.path.basename(app_dir)
        with open(bat_path, "w", encoding="gbk") as f:
            f.write("@echo off\n")
            f.write("echo Updating Love Strategist...\n")
            f.write("timeout /t 2 /nobreak >nul\n")
            f.write(f'rmdir /s /q "{app_dir}"\n')
            f.write(f'rename "{new_dir}" "{app_name}"\n')
            f.write(f'start "" "{os.path.join(app_dir, app_name + ".exe")}"\n')
            f.write("del \"%~f0\"\n")

        # 清理临时文件
        shutil.rmtree(tmp_dir)

        if callback:
            callback("准备完成")

        return True, "更新已就绪，请重启应用完成更新"
    except Exception as e:
        logger.error(f"更新失败: {e}")
        return False, f"更新失败: {e}"