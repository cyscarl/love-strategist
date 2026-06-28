"""GitHub 更新检查服务。

从 GitHub Releases API 获取最新版本，与本地版本比较。
"""

import re
import requests
from loguru import logger


def _parse_version(v: str) -> tuple:
    """解析版本字符串为可比较的元组。如 'v0.2.0' → (0, 2, 0)。"""
    v = v.strip().lstrip("vV")
    try:
        return tuple(int(x) for x in v.split(".")[:3])
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _version_newer(latest: str, current: str) -> bool:
    """latest 是否比 current 更新。"""
    return _parse_version(latest) > _parse_version(current)


def check_github_update(repo_url: str, current_version: str) -> dict | None:
    """查询 GitHub Releases 最新版本。

    Args:
        repo_url: GitHub 仓库 URL，如 https://github.com/owner/repo
        current_version: 当前本地版本号

    Returns:
        {"latest": "v0.2.0", "url": "...", "body": "更新内容"} 或 None
    """
    if not repo_url:
        return None

    # 从 repo_url 提取 owner/repo
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
            return None  # 已是最新，不需要更新

        return {
            "latest": latest_tag,
            "url": data.get("html_url", repo_url + "/releases/latest"),
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