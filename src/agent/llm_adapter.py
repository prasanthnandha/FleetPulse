"""
FleetPulse — LLM Provider Adapter
===================================
Provider-agnostic LLM interface supporting tool calling.
Supports: Anthropic Claude, OpenAI-compatible APIs, Databricks Foundation Models.
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Generator


class LLMMessage:
    """Standardized message format across providers."""

    def __init__(self, role: str, content: str, tool_calls: list[dict] | None = None, tool_call_id: str | None = None):
        self.role = role  # "system", "user", "assistant", "tool"
        self.content = content
        self.tool_calls = tool_calls  # For assistant messages requesting tool calls
        self.tool_call_id = tool_call_id  # For tool result messages

    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


class LLMResponse:
    """Standardized response from any LLM provider."""

    def __init__(
        self,
        content: str | None = None,
        tool_calls: list[dict] | None = None,
        finish_reason: str = "stop",
        usage: dict | None = None,
    ):
        self.content = content
        self.tool_calls = tool_calls or []
        self.finish_reason = finish_reason  # "stop", "tool_use", "length"
        self.usage = usage or {}

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class BaseLLMAdapter(ABC):
    """Abstract base for LLM provider adapters."""

    @abstractmethod
    def chat(self, messages: list[LLMMessage], tools: list[dict] | None = None, **kwargs) -> LLMResponse:
        """Send a chat completion request."""
        ...

    @abstractmethod
    def stream_chat(self, messages: list[LLMMessage], tools: list[dict] | None = None, **kwargs) -> Generator[str, None, None]:
        """Stream a chat completion response (yields text chunks)."""
        ...


# ==============================================================================
# Anthropic Adapter
# ==============================================================================

class AnthropicAdapter(BaseLLMAdapter):
    """Adapter for Anthropic Claude API with tool calling support."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = model

    def _convert_tools(self, tools: list[dict] | None) -> list[dict] | None:
        """Convert standardized tool schema to Anthropic format."""
        if not tools:
            return None
        anthropic_tools = []
        for tool in tools:
            anthropic_tools.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool.get("parameters", {}),
            })
        return anthropic_tools

    def _convert_messages(self, messages: list[LLMMessage]) -> tuple[str | None, list[dict]]:
        """Convert messages, extracting system message for Anthropic API."""
        system_msg = None
        api_messages = []

        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
                continue

            if msg.role == "tool":
                api_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content,
                    }],
                })
            elif msg.role == "assistant" and msg.tool_calls:
                content = []
                if msg.content:
                    content.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"],
                    })
                api_messages.append({"role": "assistant", "content": content})
            else:
                api_messages.append({"role": msg.role, "content": msg.content})

        return system_msg, api_messages

    def chat(self, messages: list[LLMMessage], tools: list[dict] | None = None, **kwargs) -> LLMResponse:
        system_msg, api_messages = self._convert_messages(messages)
        anthropic_tools = self._convert_tools(tools)

        params = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": api_messages,
        }
        if system_msg:
            params["system"] = system_msg
        if anthropic_tools:
            params["tools"] = anthropic_tools

        response = self.client.messages.create(**params)

        # Parse response
        content = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    },
                })

        finish_reason = "tool_use" if response.stop_reason == "tool_use" else "stop"

        return LLMResponse(
            content=content or None,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

    def stream_chat(self, messages: list[LLMMessage], tools: list[dict] | None = None, **kwargs) -> Generator[str, None, None]:
        system_msg, api_messages = self._convert_messages(messages)
        anthropic_tools = self._convert_tools(tools)

        params = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": api_messages,
        }
        if system_msg:
            params["system"] = system_msg
        if anthropic_tools:
            params["tools"] = anthropic_tools

        with self.client.messages.stream(**params) as stream:
            for text in stream.text_stream:
                yield text


# ==============================================================================
# OpenAI-compatible Adapter
# ==============================================================================

class OpenAIAdapter(BaseLLMAdapter):
    """Adapter for OpenAI and OpenAI-compatible APIs."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        base_url: str | None = None,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url
        self.model = model
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key or "dummy-key",
                base_url=base_url,
            )
        except ImportError:
            self.client = None


    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        api_messages = []
        for msg in messages:
            d = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                d["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                d["tool_call_id"] = msg.tool_call_id
            api_messages.append(d)
        return api_messages

    def _convert_tools(self, tools: list[dict] | None) -> list[dict] | None:
        if not tools:
            return None
        return [{"type": "function", "function": tool} for tool in tools]

    def chat(self, messages: list[LLMMessage], tools: list[dict] | None = None, **kwargs) -> LLMResponse:
        api_messages = self._convert_messages(messages)
        openai_tools = self._convert_tools(tools)

        params = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        if openai_tools:
            params["tools"] = openai_tools

        response = self.client.chat.completions.create(**params)
        choice = response.choices[0]

        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                })

        return LLMResponse(
            content=choice.message.content,
            tool_calls=tool_calls,
            finish_reason="tool_use" if choice.finish_reason == "tool_calls" else choice.finish_reason,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            } if response.usage else {},
        )

    def stream_chat(self, messages: list[LLMMessage], tools: list[dict] | None = None, **kwargs) -> Generator[str, None, None]:
        api_messages = self._convert_messages(messages)

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# ==============================================================================
# Factory
# ==============================================================================

def create_llm_adapter(
    provider: str | None = None,
    **kwargs,
) -> BaseLLMAdapter:
    """
    Factory function to create an LLM adapter.

    Args:
        provider: "anthropic", "openai", or "databricks". If None, reads from LLM_PROVIDER env var.
        **kwargs: Provider-specific arguments (api_key, model, base_url, etc.)
    """
    provider = provider or os.getenv("LLM_PROVIDER", "anthropic")

    if provider == "anthropic":
        return AnthropicAdapter(**kwargs)
    elif provider == "openai":
        return OpenAIAdapter(**kwargs)
    elif provider == "databricks":
        # Databricks Foundation Models use OpenAI-compatible API on /serving-endpoints
        host = kwargs.get("host") or os.getenv("DATABRICKS_HOST", "")
        token = kwargs.get("token") or os.getenv("DATABRICKS_TOKEN", "")
        model = kwargs.get("model") or os.getenv("DATABRICKS_MODEL", "databricks-meta-llama-3-1-70b-instruct")

        if not host or not token:
            try:
                from databricks.sdk import WorkspaceClient
                w = WorkspaceClient()
                host = host or (w.config.host if hasattr(w.config, "host") else "")
                token = token or (w.config.token if hasattr(w.config, "token") else "")
            except Exception:
                pass

        base_url = f"{host.rstrip('/')}/serving-endpoints" if host else "http://localhost:8000/mock-endpoints"
        return OpenAIAdapter(
            api_key=token or "databricks-token",
            base_url=base_url,
            model=model,
            **{k: v for k, v in kwargs.items() if k not in ("model", "host", "token")},
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'databricks', 'anthropic', or 'openai'.")
