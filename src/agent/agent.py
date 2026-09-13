"""
FleetPulse — Agent Orchestrator
=================================
Tool-calling LLM agent that coordinates prediction, RAG, and ticketing
tools to answer IT operations queries about device fleet health.
"""

import json
import uuid
from typing import Any, Generator

from src.agent.guardrails import sanitize_pii, validate_anti_hallucination
from src.agent.llm_adapter import BaseLLMAdapter, LLMMessage, LLMResponse, create_llm_adapter
from src.agent.prompts import SYSTEM_PROMPT, TOOL_DEFINITIONS
from src.agent.tools.prediction_tool import PredictionTool
from src.agent.tools.rag_tool import RAGTool
from src.agent.tools.ticket_tool import TicketTool


class FleetPulseAgent:
    """
    Agentic orchestrator for FleetPulse.

    Maintains conversation history, routes user queries through tool calling,
    and synthesizes responses from prediction, RAG, and ticketing tools.
    """

    MAX_TOOL_ROUNDS = 5  # Maximum tool-calling rounds per user message

    def __init__(
        self,
        llm: BaseLLMAdapter | None = None,
        prediction_tool: PredictionTool | None = None,
        rag_tool: RAGTool | None = None,
        ticket_tool: TicketTool | None = None,
        llm_provider: str | None = None,
        llm_kwargs: dict | None = None,
    ):
        """
        Args:
            llm: Pre-configured LLM adapter. If None, creates one from provider/env.
            prediction_tool: Prediction tool instance. If None, creates default.
            rag_tool: RAG tool instance. If None, creates default.
            ticket_tool: Ticket tool instance. If None, creates default.
            llm_provider: LLM provider name (used if llm is None).
            llm_kwargs: Additional kwargs for LLM creation.
        """
        self.llm = llm or create_llm_adapter(provider=llm_provider, **(llm_kwargs or {}))
        self.prediction_tool = prediction_tool or PredictionTool()
        self.rag_tool = rag_tool or RAGTool()
        self.ticket_tool = ticket_tool or TicketTool()

        self._tools = {
            "get_fleet_prediction": self.prediction_tool,
            "get_device_repair_info": self.rag_tool,
            "draft_remediation_ticket": self.ticket_tool,
        }

        self._conversation_history: list[LLMMessage] = [
            LLMMessage(role="system", content=SYSTEM_PROMPT),
        ]

    @property
    def conversation_history(self) -> list[dict]:
        """Return conversation history as list of dicts."""
        return [msg.to_dict() for msg in self._conversation_history if msg.role != "system"]

    def reset(self):
        """Reset conversation history."""
        self._conversation_history = [
            LLMMessage(role="system", content=SYSTEM_PROMPT),
        ]

    def chat(self, user_message: str) -> dict:
        """
        Process a user message through the agent loop.

        Args:
            user_message: The user's input text.

        Returns:
            Dict with:
                - "response": str — The agent's final text response
                - "tool_calls": list — Tools that were called
                - "tool_results": list — Results from tool calls
        """
        # Scrub PII from incoming prompt
        sanitized_user_message = sanitize_pii(user_message)
        self._conversation_history.append(
            LLMMessage(role="user", content=sanitized_user_message)
        )

        all_tool_calls = []
        all_tool_results = []

        # Agent loop: LLM may call tools multiple times
        for round_num in range(self.MAX_TOOL_ROUNDS):
            # Call LLM
            response = self.llm.chat(
                messages=self._conversation_history,
                tools=TOOL_DEFINITIONS,
            )

            if not response.has_tool_calls:
                # Validate anti-hallucination against gathered tool results
                raw_text = response.content or ""
                _, grounded_text = validate_anti_hallucination(raw_text, all_tool_results)
                final_text = sanitize_pii(grounded_text)

                self._conversation_history.append(
                    LLMMessage(role="assistant", content=final_text)
                )
                return {
                    "response": final_text,
                    "tool_calls": all_tool_calls,
                    "tool_results": all_tool_results,
                }

            # Process tool calls
            # Add assistant message with tool calls to history
            self._conversation_history.append(
                LLMMessage(
                    role="assistant",
                    content=response.content or "",
                    tool_calls=response.tool_calls,
                )
            )

            for tc in response.tool_calls:
                tool_name = tc["function"]["name"]
                tool_args_str = tc["function"]["arguments"]
                tool_call_id = tc["id"]

                try:
                    tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                except json.JSONDecodeError:
                    tool_args = {}

                all_tool_calls.append({
                    "tool": tool_name,
                    "arguments": tool_args,
                    "round": round_num + 1,
                })

                # Execute tool
                tool_result = self._execute_tool(tool_name, tool_args)
                tool_result_str = json.dumps(tool_result, indent=2, default=str)

                all_tool_results.append({
                    "tool": tool_name,
                    "result": tool_result,
                    "round": round_num + 1,
                })

                # Add tool result to history
                self._conversation_history.append(
                    LLMMessage(
                        role="tool",
                        content=tool_result_str,
                        tool_call_id=tool_call_id,
                    )
                )

        # If we exhausted tool rounds, force a final response
        final_response = self.llm.chat(
            messages=self._conversation_history,
            tools=None,  # No tools = force text response
        )

        self._conversation_history.append(
            LLMMessage(role="assistant", content=final_response.content or "")
        )

        return {
            "response": final_response.content or "",
            "tool_calls": all_tool_calls,
            "tool_results": all_tool_results,
        }

    def stream_chat(self, user_message: str) -> Generator[dict, None, None]:
        """
        Stream a response for a user message.
        Yields events as they occur (text chunks, tool calls, tool results).

        Yields dicts with:
            - {"type": "text", "content": "..."}
            - {"type": "tool_call", "tool": "...", "arguments": {...}}
            - {"type": "tool_result", "tool": "...", "result": {...}}
            - {"type": "done", "full_response": "..."}
        """
        # Scrub PII from incoming prompt
        sanitized_user_message = sanitize_pii(user_message)
        self._conversation_history.append(
            LLMMessage(role="user", content=sanitized_user_message)
        )

        full_response = ""
        executed_tool_results = []

        for round_num in range(self.MAX_TOOL_ROUNDS):
            # First, check for tool calls
            response = self.llm.chat(
                messages=self._conversation_history,
                tools=TOOL_DEFINITIONS,
            )

            if not response.has_tool_calls:
                # Apply anti-hallucination and PII sanitization guardrail
                raw_text = response.content or ""
                _, grounded_text = validate_anti_hallucination(raw_text, executed_tool_results)
                final_text = sanitize_pii(grounded_text)

                self._conversation_history.append(
                    LLMMessage(role="assistant", content=final_text)
                )

                # Stream the sanitized response text chunk by chunk
                chunk_size = 20
                for i in range(0, len(final_text), chunk_size):
                    yield {"type": "text", "content": final_text[i:i + chunk_size]}
                full_response = final_text

                yield {"type": "done", "full_response": full_response}
                return

            # Tool calls detected
            self._conversation_history.append(
                LLMMessage(
                    role="assistant",
                    content=response.content or "",
                    tool_calls=response.tool_calls,
                )
            )

            if response.content:
                yield {"type": "text", "content": response.content}
                full_response += response.content

            for tc in response.tool_calls:
                tool_name = tc["function"]["name"]
                tool_args_str = tc["function"]["arguments"]
                tool_call_id = tc["id"]

                try:
                    tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                except json.JSONDecodeError:
                    tool_args = {}

                yield {"type": "tool_call", "tool": tool_name, "arguments": tool_args}

                # Execute
                tool_result = self._execute_tool(tool_name, tool_args)
                executed_tool_results.append(tool_result)

                yield {"type": "tool_result", "tool": tool_name, "result": tool_result}

                self._conversation_history.append(
                    LLMMessage(
                        role="tool",
                        content=json.dumps(tool_result, indent=2, default=str),
                        tool_call_id=tool_call_id,
                    )
                )

        # Force final response
        final = self.llm.chat(messages=self._conversation_history, tools=None)
        self._conversation_history.append(
            LLMMessage(role="assistant", content=final.content or "")
        )
        text = final.content or ""
        chunk_size = 20
        for i in range(0, len(text), chunk_size):
            yield {"type": "text", "content": text[i:i + chunk_size]}
        full_response += text
        yield {"type": "done", "full_response": full_response}

    def _execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool by name with given arguments."""
        tool = self._tools.get(tool_name)
        if tool is None:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            return tool.execute(arguments)
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
