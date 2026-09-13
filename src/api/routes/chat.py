"""
FleetPulse — Chat API Routes
==============================
Handles chat messages via the FleetPulse agent.
Supports both synchronous and streaming (SSE) responses.
"""

import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from src.api.models import ChatHistoryItem, ChatRequest, ChatResponse, ChatStreamEvent

router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory session storage (would be Redis/DB in production)
_sessions: dict[str, dict] = {}


def _get_or_create_agent(session_id: str):
    """Get or create an agent for a session."""
    if session_id not in _sessions:
        from src.agent.agent import FleetPulseAgent
        _sessions[session_id] = {
            "agent": FleetPulseAgent(),
            "history": [],
        }
    return _sessions[session_id]


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message and get a complete response.
    Use this for non-streaming clients.
    """
    session_id = request.session_id or str(uuid.uuid4())
    session = _get_or_create_agent(session_id)
    agent = session["agent"]

    # Process message through agent
    result = agent.chat(request.message)

    # Store in history
    session["history"].append({"role": "user", "content": request.message})
    session["history"].append({"role": "assistant", "content": result["response"]})

    return ChatResponse(
        response=result["response"],
        session_id=session_id,
        tool_calls=[
            {"tool": tc["tool"], "arguments": tc["arguments"], "round": tc["round"]}
            for tc in result.get("tool_calls", [])
        ],
        tool_results=[
            {"tool": tr["tool"], "result": tr["result"], "round": tr["round"]}
            for tr in result.get("tool_results", [])
        ],
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Send a message and stream the response via Server-Sent Events (SSE).
    Each event contains a ChatStreamEvent JSON payload.
    """
    session_id = request.session_id or str(uuid.uuid4())
    session = _get_or_create_agent(session_id)
    agent = session["agent"]

    async def event_generator() -> AsyncGenerator[dict, None]:
        # Send session ID first
        yield {
            "event": "session",
            "data": json.dumps({"session_id": session_id}),
        }

        try:
            for event in agent.stream_chat(request.message):
                event_type = event.get("type", "text")

                if event_type == "text":
                    yield {
                        "event": "text",
                        "data": json.dumps({"content": event.get("content", "")}),
                    }
                elif event_type == "tool_call":
                    yield {
                        "event": "tool_call",
                        "data": json.dumps({
                            "tool": event.get("tool", ""),
                            "arguments": event.get("arguments", {}),
                        }, default=str),
                    }
                elif event_type == "tool_result":
                    yield {
                        "event": "tool_result",
                        "data": json.dumps({
                            "tool": event.get("tool", ""),
                            "result": event.get("result", {}),
                        }, default=str),
                    }
                elif event_type == "done":
                    full_response = event.get("full_response", "")
                    session["history"].append({"role": "user", "content": request.message})
                    session["history"].append({"role": "assistant", "content": full_response})
                    yield {
                        "event": "done",
                        "data": json.dumps({"full_response": full_response}),
                    }

        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_generator())


@router.get("/history", response_model=list[ChatHistoryItem])
async def chat_history(session_id: str):
    """Get conversation history for a session."""
    session = _sessions.get(session_id)
    if not session:
        return []

    return [
        ChatHistoryItem(role=msg["role"], content=msg["content"])
        for msg in session.get("history", [])
    ]


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a chat session and reset the agent."""
    if session_id in _sessions:
        del _sessions[session_id]
    return {"status": "cleared", "session_id": session_id}
