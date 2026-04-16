# -*- coding: utf-8 -*-
"""
app.core.llm
==============

此模块实现统一的 LLM 抽象，面向 **OpenAI 兼容的 VLLM（NVIDIA NIM）**
以及 **Anthropic**（备用）。

主要特性
--------
- 通过 **OpenAI 1.x SDK** (`openai.OpenAI`) 创建兼容 VLLM 的客户端。
- 支持 **动态 `max_tokens`**（依据提示长度自动估算，防止响应被截断）。
- **自动重试**：最多 3 次，每次间隔 5 s，失败时返回统一占位字符串。
- **统一日志**：配置打印、调用耗时、错误信息全走 `logging`（`app.core.logger`）。
- **全局单例** `llm`，便于在项目其他模块直接 `from app.core.llm import llm` 使用。
- 安全的 **超时**（默认 30 秒，可在构造函数中覆盖）。

使用方式
----------
```python
from app.core.llm import llm

# 简单文本
result = llm.chat("请返回 JSON {\"text\":\"hello\"}")

# 直接使用 VLLM（兼容旧接口）
result = llm.chat_vllm_direct([{"role":"user","content":"请返回 JSON {\"text\":\"hello\"}"}])
```
"""

import os
import time
import json

# Optional provider imports – they may be missing in the execution environment.
try:
    import openai  # type: ignore
except Exception:  # pragma: no cover
    openai = None  # type: ignore

try:
    from anthropic import Anthropic  # type: ignore
except Exception:  # pragma: no cover
    Anthropic = None  # type: ignore

from .config import get_settings
from ..core.logger import get_logger

_logger = get_logger(__name__)


class LLM:
    """Unified LLM abstraction supporting VLLM (OpenAI‑compatible) and Anthropic.

    *VLLM* 使用 OpenAI 1.x SDK 的 `OpenAI` 客户端，
    通过 ``base_url`` 指向 NVIDIA NIM 端点。
    """

    def _parse_response(self, json_resp: str) -> dict:
        """Parse a JSON string response from the LLM.

        Returns the parsed dictionary, or an empty dict on failure.
        """
        try:
            return json.loads(json_resp)
        except Exception as e:
            _logger.warning(
                f"LLM JSON parse failed: {e}. Raw response: {json_resp[:200]}"
            )
            return {}

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ):
        """Create an LLM helper.

        Parameters
        ----------
        endpoint: VLLM 服务的 ``base_url``（默认取自 ``.env`` 中的 ``VLLM_ENDPOINT``）。
        api_key:  对应的 API Key（默认取自 ``VLLM_API_KEY``）。
        model:    完整模型名称，例如 ``qwen/qwen3.5-397b-a17b``（默认取 ``DEFAULT_LLM_MODEL``）。
        timeout:  客户端请求超时时间（秒），默认 30 s。
        """
        settings = get_settings()
        self.endpoint = endpoint or getattr(settings, "VLLM_ENDPOINT", None)
        self.api_key = api_key or getattr(settings, "VLLM_API_KEY", None)
        self.model = model or getattr(settings, "DEFAULT_LLM_MODEL", "gpt-4o")
        self.timeout = (
            timeout or 120
        )  # seconds – extended default to accommodate slower VLLM responses
        self._config_logged = False
        # 首次使用时会打印配置（掩码处理）
        self._print_config()

    # ---------------------------------------------------------------------
    def _print_config(self) -> None:
        """Print VLLM configuration once (masked key to avoid泄露)."""
        if self._config_logged:
            return
        masked = (
            ("*" * (len(self.api_key) - 4) + self.api_key[-4:])
            if self.api_key
            else None
        )
        _logger.info(
            f"[VLLM CONFIG] endpoint={self.endpoint}, key={masked}, model={self.model}"
        )
        self._config_logged = True

    # ---------------------------------------------------------------------
    def _vllm_request(
        self,
        prompt: str,
        max_tokens: int = 200,
        temperature: float = 0.0,
        stop: list[str] | None = None,
    ) -> str:
        """Perform a VLLM call with up to 3 attempts.

        Returns the *content* string of the first choice.  If **all** attempts
        fail a placeholder ``"[LLM-<model>] request failed"`` is returned so the
        caller never receives an exception.
        """
        if not (self.endpoint and self.api_key):
            _logger.error("VLLM endpoint or API key not configured")
            return f"[LLM-{self.model}] request failed"

        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                if openai is not None and hasattr(openai, "OpenAI"):
                    client = openai.OpenAI(
                        api_key=self.api_key,
                        base_url=self.endpoint.rstrip("/"),
                        timeout=self.timeout,
                    )
                else:
                    # Fallback to raw HTTP request using requests
                    import json, requests

                    payload = {
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    }
                    if stop:
                        payload["stop"] = stop
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    }
                    # Log the fallback HTTP request payload for debugging
                    _logger.info(f"VLLM fallback HTTP payload: {payload}")
                    response = requests.post(
                        f"{self.endpoint.rstrip('/')}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=self.timeout,
                    )
                    response.raise_for_status()
                    res = response.json()

                    # Mimic OpenAI response shape
                    class _Obj:
                        pass

                    res_obj = _Obj()
                    res_obj.choices = [_Obj()]
                    res_obj.choices[0].message = _Obj()
                    res_obj.choices[0].message.content = (
                        res.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    # Return the mimicked object
                    client = None
                _logger.info(f"[VLLM] 第 {attempt} 次尝试调用模型 {self.model}")
                if client is not None:
                    # OpenAI SDK path
                    # Log the parameters passed to the OpenAI/VLLM SDK (DEBUG)
                    _logger.debug(
                        f"VLLM/OpenAI SDK call with params: model={self.model}, max_tokens={max_tokens}, temperature={temperature}, stop={stop}"
                    )
                    # Log request parameters (INFO level) for full traceability
                    _logger.info(
                        f"VLLM request parameters: model={self.model}, max_tokens={max_tokens}, temperature={temperature}, stop={stop}"
                    )
                    # Perform the SDK call
                    res = client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=temperature,
                        stop=stop,
                    )
                else:
                    # Fallback already performed; ``res`` holds the JSON response
                    # Convert it to an object mimicking the SDK shape for uniform handling
                    class _Obj:
                        pass

                    res_obj = _Obj()
                    res_obj.choices = [_Obj()]
                    res_obj.choices[0].message = _Obj()
                    res_obj.choices[0].message.content = (
                        res.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    res = res_obj
                # Success – extract content and return
                return res.choices[0].message.content
            except Exception as exc:
                _logger.error(f"[VLLM] 第 {attempt} 次调用失败: {exc}")
                if attempt == attempts:
                    return f"[LLM-{self.model}] request failed"
                time.sleep(5)  # simple back‑off

    # ---------------------------------------------------------------------
    def chat(
        self, prompt: str, max_tokens: int | None = None, stop: list[str] | None = None
    ) -> str:
        """Send a prompt to the LLM and obtain the model response.

        Parameters
        ----------
        max_tokens: Optional max token count for the model output. If ``None``
            an estimate based on prompt length (≈1 token per 4 characters) is
            used, capped by the ``LLM_MAX_OUTPUT_TOKENS`` setting.
        stop: Optional list of stop sequences. The model will cease generation
            when any of these strings appears (e.g. ``"END_OF_JSON"``).
        """
        start = time.time()
        # 动态估算 max_tokens，防止大文本被截断（约 1 token ≈ 4 字符）
        max_output = getattr(get_settings(), "LLM_MAX_OUTPUT_TOKENS", 4000)
        est_tokens = max(
            200,
            min(max_output, (len(prompt) // 4) if max_tokens is None else max_tokens),
        )
        result = self._vllm_request(prompt=prompt, max_tokens=est_tokens, stop=stop)
        duration = time.time() - start
        _logger.info(f"LLM 调用耗时 {duration:.2f}s（模型 {self.model}）")
        return result

    # ---------------------------------------------------------------------
    def chat_vllm_direct(self, messages: list) -> str:
        """Compatibility wrapper: accept a list of ``{"role":..., "content":...}``.

        The method concatenates the messages into a single prompt (joining the
        ``content`` fields) and forwards it to :meth:`_vllm_request`.
        """
        # Simple concatenation – most callers already send a single message.
        prompt = "\n".join(m.get("content", "") for m in messages)
        start = time.time()
        # Allow a larger output token budget for KG extraction (configurable via env)
        max_output = getattr(get_settings(), "LLM_MAX_OUTPUT_TOKENS", 4000)
        est_tokens = max(200, min(max_output, len(prompt) // 4))
        result = self._vllm_request(prompt=prompt, max_tokens=est_tokens)
        duration = time.time() - start
        _logger.info(f"Direct VLLM 调用耗时 {duration:.2f}s（模型 {self.model}）")
        return result


# ---------------------------------------------------------------------
# Global singleton for convenient import across the project
# ---------------------------------------------------------------------
llm = LLM()
