"""DeepSeek / OpenAI 兼容 API 封装。

职责：纯 HTTP 调用 —— 发请求、处理流式/非流式、重试、超时、错误包装。
禁止：业务逻辑、数据库操作、FastAPI 类型依赖。
"""

from typing import Optional, AsyncGenerator, Any
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

from utils.logger import get_logger

logger = get_logger(__name__)


class AIClient:
    """AI API 客户端 — 封装 AsyncOpenAI，统一流式/非流式/JSON 模式。

    Usage:
        client = AIClient(
            api_key="sk-xxx",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-v4-pro",
            timeout=120,
            max_retries=3,
        )
        text = await client.chat([{"role": "user", "content": "..."}])
        async for chunk in client.chat_stream([...]):
            ...
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-v4-pro",
        timeout: float = 60,
        connect_timeout: float = 10,
        max_retries: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.9,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.max_retries = max_retries

        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    # ── 公开 API ──────────────────────────────────────────

    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        enable_thinking: bool = False,
        thinking_effort: str = "medium",
    ) -> str:
        """非流式调用，返回完整响应文本。"""
        kwargs = self._build_kwargs(
            messages, model, temperature, max_tokens,
            stream=False, enable_thinking=enable_thinking,
            thinking_effort=thinking_effort,
        )
        try:
            response = await self._client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            self._log_usage("非流式", response.usage)
            return content
        except (APITimeoutError, APIError, RateLimitError) as e:
            logger.error(f"[AI] API 错误: {type(e).__name__}: {e}")
            raise

    async def chat_json(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """非流式 + JSON 模式，返回解析后的 dict。

        含 JSON 修复逻辑：AI（尤其是 flash 模型）偶尔输出残缺 JSON，
        尝试截取到最后一个完整闭合的对象再解析。
        """
        kwargs = self._build_kwargs(
            messages, model, temperature, max_tokens,
            stream=False, enable_thinking=False,
        )
        kwargs["response_format"] = {"type": "json_object"}
        try:
            response = await self._client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or "{}"
            self._log_usage("JSON", response.usage)
            import json  # 延迟导入：json 是标准库，仅 JSON 模式需要
            return self._parse_json(content)
        except (APITimeoutError, APIError, RateLimitError) as e:
            logger.error(f"[AI] JSON API 错误: {type(e).__name__}: {e}")
            raise

    @staticmethod
    def _parse_json(content: str) -> dict:
        """解析 AI 返回的 JSON，含修复逻辑。"""
        import json  # 延迟导入：仅 JSON 解析失败修复时需要
        import re as _json_re
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"[AI] JSON 解析失败 (pos={e.pos}): {e.msg}, 尝试修复...")
            # 修复 1: 截取到最后一个完整闭合的 }
            depth = 0
            last_valid = 0
            for i, ch in enumerate(content):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        last_valid = i + 1
            if last_valid > 0 and last_valid < len(content):
                try:
                    repaired = json.loads(content[:last_valid])
                    logger.info(f"[AI] JSON 修复成功 (截断 {len(content) - last_valid} 字符)")
                    return repaired
                except json.JSONDecodeError:
                    pass
            # 修复 2: 找到最后一个 } 并截取
            last_brace = content.rfind('}')
            if last_brace > 0:
                try:
                    repaired = json.loads(content[:last_brace + 1])
                    logger.info(f"[AI] JSON 修复成功 (末尾截断)")
                    return repaired
                except json.JSONDecodeError:
                    pass
            # 修复 3: 丢弃最后一个不完整的数组/对象元素，补全外层结构
            # 策略 A: 找最后一个 }, 或 ], （完整元素的结束），截断并闭合
            best_pos = 0
            for m in _json_re.finditer(r'\}[,\s]*\n?\s*', content):
                best_pos = max(best_pos, m.start() + 1)
            for m in _json_re.finditer(r'\][,\s]*\n?\s*', content):
                best_pos = max(best_pos, m.start() + 1)
            # 策略 B: 如果没有任何 }，去掉最后一个 { 起的不完整对象
            if best_pos == 0:
                last_open = content.rfind('{')
                if last_open > 0:
                    best_pos = last_open

            if best_pos > 0 and best_pos < len(content):
                truncated = content[:best_pos]
                # 用栈追踪开闭顺序（跳过字符串内的括号——近似：不在双引号内的才算）
                stack: list[str] = []
                in_string = False
                for ch in truncated:
                    if ch == '"':
                        in_string = not in_string
                    elif not in_string:
                        if ch == '{':
                            stack.append('}')
                        elif ch == '}':
                            if stack and stack[-1] == '}':
                                stack.pop()
                        elif ch == '[':
                            stack.append(']')
                        elif ch == ']':
                            if stack and stack[-1] == ']':
                                stack.pop()
                repaired = truncated + ''.join(reversed(stack))
                try:
                    result = json.loads(repaired)
                    logger.info(f"[AI] JSON 修复成功 (丢弃 {len(content) - best_pos} 字符不完整元素)")
                    return result
                except json.JSONDecodeError:
                    pass
            logger.error(f"[AI] JSON 修复失败，原始内容前 200 字符: {content[:200]}")
            raise

    async def chat_stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        enable_thinking: bool = False,
        thinking_effort: str = "medium",
    ) -> AsyncGenerator[str, None]:
        """流式调用，逐块 yield 文本。"""
        kwargs = self._build_kwargs(
            messages, model, temperature, max_tokens,
            stream=True, enable_thinking=enable_thinking,
            thinking_effort=thinking_effort,
        )
        kwargs["stream_options"] = {"include_usage": True}
        try:
            response = await self._client.chat.completions.create(**kwargs)
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                if hasattr(chunk, "usage") and chunk.usage:
                    self._log_usage("流式", chunk.usage)
        except (APITimeoutError, APIError, RateLimitError) as e:
            logger.error(f"[AI] 流式 API 错误: {type(e).__name__}: {e}")
            raise

    @staticmethod
    def build_messages(user_prompt: str, system_prompt: Optional[str] = None) -> list[dict]:
        """构建标准 messages 列表。"""
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": user_prompt})
        return msgs

    # ── 内部 ────────────────────────────────────────────

    def _build_kwargs(
        self, messages, model, temperature, max_tokens,
        stream: bool, enable_thinking: bool, thinking_effort: str = "medium",
    ) -> dict:
        kwargs: dict[str, Any] = dict(
            model=model or self.model,
            messages=messages,
            max_tokens=max_tokens or self.max_tokens,
            stream=stream,
        )
        if enable_thinking:
            kwargs["extra_body"] = {
                "thinking": {"type": "enabled", "effort": thinking_effort}
            }
        else:
            kwargs["temperature"] = (
                temperature if temperature is not None else self.temperature
            )
            kwargs["top_p"] = self.top_p
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        return kwargs

    @staticmethod
    def _log_usage(label: str, usage: Any) -> None:
        if usage and hasattr(usage, "prompt_tokens"):
            logger.info(
                f"[AI] [{label}] Token: 输入={usage.prompt_tokens}, "
                f"输出={usage.completion_tokens}, 总计={usage.total_tokens}"
            )
