"""LLM API 服务 —— 封装大模型 API 调用。

支持 OpenAI 兼容接口（OpenAI / DeepSeek / 智谱 / 自定义）。
所有调用为同步阻塞，由调用方通过 AsyncWorker 放入 QThread。
"""

# 全局 Token 累计
_total_prompt_tokens = 0
_total_completion_tokens = 0


def get_token_usage() -> dict:
    """获取累计 Token 用量。"""
    return {
        "prompt_tokens": _total_prompt_tokens,
        "completion_tokens": _total_completion_tokens,
        "total_tokens": _total_prompt_tokens + _total_completion_tokens,
    }


def _add_token_usage(usage: dict) -> None:
    global _total_prompt_tokens, _total_completion_tokens
    _total_prompt_tokens += usage.get("prompt_tokens", 0)
    _total_completion_tokens += usage.get("completion_tokens", 0)

import time
from typing import Optional

import requests
from loguru import logger

from src.utils.config import get_llm_config


# ============================================================
# Token 估算（不引入 tiktoken 依赖，使用近似算法）
# ============================================================

def estimate_tokens(text: str) -> int:
    """估算文本的 Token 数量。

    近似规则（适用于中英混合）：
    - 中文字符 ≈ 2 token
    - 英文单词 ≈ 1.3 token
    - 标点/数字 ≈ 1 token
    """
    if not text:
        return 0

    import re
    # 中文字符
    chinese = len(re.findall(r'[一-鿿]', text))
    # 英文单词
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    # 其余字符（标点、数字、空格等）
    rest = len(text) - chinese - sum(len(w) for w in re.findall(r'[a-zA-Z]+', text))

    return int(chinese * 2 + english_words * 1.3 + rest * 0.5)


def estimate_messages_tokens(messages: list[dict]) -> int:
    """估算消息列表的总 Token 数。

    Args:
        messages: [{"role": "user", "content": "..."}, ...]
    """
    total = 0
    for msg in messages:
        total += estimate_tokens(msg.get("content", ""))
        total += 4  # 每条消息的元数据开销
    total += 2  # 回复 priming
    return total


# ============================================================
# API 调用
# ============================================================

def chat_completion(
    messages: list[dict],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> tuple[str, dict]:
    """调用 LLM Chat Completion API。

    Args:
        messages: 消息列表 [{"role": "system"|"user"|"assistant", "content": "..."}]
        temperature: 温度参数，None 则使用配置文件中的值
        max_tokens: 最大输出 token，None 则使用配置文件中的值

    Returns:
        (response_text, token_usage) 元组
        token_usage = {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}

    Raises:
        ValueError: API Key 未配置
        ConnectionError: 网络连接失败
        TimeoutError: 请求超时
        RuntimeError: API 返回错误
    """
    config = get_llm_config()
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "https://api.openai.com/v1")
    model = config.get("model", "gpt-4")
    timeout = config.get("timeout", 30)

    if not api_key or api_key == "your-api-key-here":
        raise ValueError("API Key 未配置，请在 config/config.yaml 中设置 llm.api_key")

    if temperature is None:
        temperature = config.get("temperature", 0.8)
    if max_tokens is None:
        max_tokens = config.get("max_tokens", 2048)

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "LoveStrategist/1.0",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    # 估算输入 token
    input_tokens = estimate_messages_tokens(messages)
    logger.debug(f"LLM 请求: model={model}, messages={len(messages)}, ~{input_tokens} tokens")

    try:
        start = time.perf_counter()
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        elapsed = time.perf_counter() - start

        if resp.status_code != 200:
            error_body = resp.text[:500]
            # 如果返回 HTML 而非 JSON，说明大概率 URL 配错了
            if error_body.strip().startswith("<!") or "<html" in error_body.lower():
                raise RuntimeError(
                    f"API 返回了网页而非 JSON（状态码 {resp.status_code}）。"
                    f"请检查 base_url 是否正确。当前: {base_url}\n"
                    f"提示：DeepSeek API 地址应为 https://api.deepseek.com/v1"
                )
            logger.error(f"LLM API 错误 ({resp.status_code}): {error_body}")
            raise RuntimeError(f"API 返回错误 ({resp.status_code}): {error_body}")

        data = resp.json()
        choice = data["choices"][0]
        content = choice["message"]["content"]
        usage = data.get("usage", {})

        token_usage = {
            "prompt_tokens": usage.get("prompt_tokens", input_tokens),
            "completion_tokens": usage.get("completion_tokens", estimate_tokens(content)),
            "total_tokens": usage.get("total_tokens", input_tokens + estimate_tokens(content)),
        }

        _add_token_usage(token_usage)
        logger.info(
            f"LLM 完成: {elapsed:.1f}s, "
            f"prompt={token_usage['prompt_tokens']}, "
            f"completion={token_usage['completion_tokens']}, "
            f"total={token_usage['total_tokens']}"
        )
        return content, token_usage

    except requests.exceptions.Timeout:
        logger.error(f"LLM 请求超时 ({timeout}s)")
        raise TimeoutError(f"LLM 请求超时 ({timeout} 秒)")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"LLM 连接失败: {e}")
        raise ConnectionError(f"无法连接到 LLM API: {base_url}")
    except (KeyError, IndexError) as e:
        logger.error(f"LLM 响应格式异常: {e}")
        raise RuntimeError(f"LLM 返回了意外的响应格式: {e}")


def test_connection() -> tuple[bool, str]:
    """测试 LLM API 连接。

    Returns:
        (success, message)
    """
    try:
        content, usage = chat_completion(
            messages=[{"role": "user", "content": "请用一句话介绍自己"}],
            max_tokens=50,
        )
        return True, f"连接成功！模型回复: {content[:80]}..."
    except ValueError as e:
        return False, str(e)
    except ConnectionError as e:
        return False, str(e)
    except TimeoutError as e:
        return False, str(e)
    except RuntimeError as e:
        return False, str(e)
    except Exception as e:
        return False, f"未知错误: {e}"


def list_models(base_url: str = "", api_key: str = "") -> tuple[list[str], str]:
    """从 API 获取当前可用模型列表。

    Returns:
        (模型列表, 错误信息) — 成功时错误信息为空字符串
    """
    import requests
    from src.utils.config import get_llm_config

    if not base_url or not api_key:
        config = get_llm_config()
        api_key = api_key or config.get("api_key", "")
        base_url = base_url or config.get("base_url", "").rstrip("/")
    else:
        base_url = base_url.rstrip("/")
    timeout = 15

    if not api_key or api_key == "your-api-key-here":
        return [], "未配置 API Key"

    url = f"{base_url}/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "LoveStrategist/1.0",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 401:
            return [], "认证失败，请检查 API Key 是否正确"
        if resp.status_code == 403:
            return [], "无权限访问模型列表"
        if resp.status_code == 404:
            return [], "该供应商不支持在线获取模型列表"
        if resp.status_code != 200:
            return [], f"请求失败 (HTTP {resp.status_code})"
        data = resp.json()
        models = [m["id"] for m in data.get("data", []) if m.get("id")]
        chat_models = [
            m for m in models
            if not any(x in m for x in ["embed", "audio", "moderation", "dall-e", "tts", "whisper"])
        ]
        logger.info(f"获取到 {len(chat_models)} 个可用模型")
        return chat_models, ""
    except requests.exceptions.Timeout:
        return [], "连接超时，请检查网络或 API 地址是否正确"
    except requests.exceptions.ConnectionError:
        return [], "无法连接，请检查网络或 API 地址"
    except Exception as e:
        return [], f"请求失败: {e}"
