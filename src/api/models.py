"""
FleetPulse — Pydantic Request/Response Models
===============================================
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ==============================================================================
# Chat
# ==============================================================================


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str = Field(..., min_length=1, max_length=2000, description="User message text")
    session_id: str | None = Field(None, description="Session ID for conversation continuity")


class ToolCallInfo(BaseModel):
    """Info about a tool call made during the response."""

    tool: str
    arguments: dict[str, Any] = {}
    round: int = 1


class ToolResultInfo(BaseModel):
    """Info about a tool result."""

    tool: str
    result: dict[str, Any] = {}
    round: int = 1


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""

    response: str
    session_id: str
    tool_calls: list[ToolCallInfo] = []
    tool_results: list[ToolResultInfo] = []
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ChatStreamEvent(BaseModel):
    """SSE event during streaming chat."""

    type: str  # "text", "tool_call", "tool_result", "done", "error"
    content: str | None = None
    tool: str | None = None
    arguments: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    full_response: str | None = None


class ChatHistoryItem(BaseModel):
    """A single message in chat history."""

    role: str
    content: str
    timestamp: str | None = None


# ==============================================================================
# Fleet / Device
# ==============================================================================


class DeviceHealth(BaseModel):
    """Device health summary."""

    device_id: str
    device_model: str
    fleet_name: str
    risk_tier: str  # "healthy", "watch", "warning", "critical"
    overall_risk_score: float
    battery_health_score: float | None = None
    compliance_score: float | None = None
    remaining_useful_life_days: float | None = None
    days_to_non_compliance: float | None = None
    capacity_fade_pct: float | None = None
    cycle_count: int | None = None
    days_since_last_patch: int | None = None
    driving_factors: list[str] = []


class FleetOverview(BaseModel):
    """Fleet-level risk overview."""

    total_devices: int
    risk_distribution: dict[str, int]  # {"critical": 3, "warning": 5, ...}
    avg_risk_score: float
    avg_battery_health: float
    avg_compliance_score: float
    devices_needing_attention: int  # Devices with RUL < 30 days
    top_risk_devices: list[DeviceHealth] = []


class FleetTrendPoint(BaseModel):
    """Single data point in a fleet trend time series."""

    date: str
    avg_risk_score: float
    critical_count: int
    warning_count: int
    total_devices: int


class FleetTrendResponse(BaseModel):
    """Fleet risk trend over time."""

    fleet_name: str | None = None
    trend_data: list[FleetTrendPoint] = []


# ==============================================================================
# Ticket
# ==============================================================================


class TicketDraft(BaseModel):
    """Drafted remediation ticket."""

    ticket_id: str
    status: str = "Draft"
    priority: str
    type: str
    device_id: str
    device_model: str | None = None
    fleet: str | None = None
    failing_component: str | None = None
    issue_summary: str
    remaining_useful_life_days: float | None = None
    part_number: str | None = None
    supplier: str | None = None
    estimated_repair_time_hours: float | None = None
    estimated_cost_usd: float | None = None
    actions: list[str] = []
    formatted_summary: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
