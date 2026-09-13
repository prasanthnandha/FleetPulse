"""
Unit tests for Agent tools and tool-calling orchestration.
"""

import pytest
from src.agent.llm_adapter import BaseLLMAdapter, LLMMessage, LLMResponse
from src.agent.tools.ticket_tool import TicketTool
from src.agent.tools.prediction_tool import PredictionTool
from src.agent.tools.rag_tool import RAGTool
from src.agent.agent import FleetPulseAgent


class MockLLMAdapter(BaseLLMAdapter):
    """Mock LLM adapter for deterministic agent tests."""

    def __init__(self, responses: list[LLMResponse]):
        self.responses = responses
        self.call_count = 0

    def chat(self, messages: list[LLMMessage], tools: list[dict] | None = None, **kwargs) -> LLMResponse:
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp

    def stream_chat(self, messages: list[LLMMessage], tools: list[dict] | None = None, **kwargs):
        yield "Mock streaming response"


class TestAgentTools:
    def test_ticket_tool_generation(self):
        """Verify ticket tool produces correctly structured remediation ticket."""
        tool = TicketTool()
        args = {
            "device_id": "DEV-APP-042",
            "device_model": "iPhone 13",
            "issue_summary": "Battery capacity dropped below 75%",
            "predicted_failure_component": "battery",
            "remaining_useful_life_days": 12.0,
            "part_number": "APL-BAT-A1B2C3",
            "supplier": "LG Chem",
            "estimated_repair_time_hours": 1.5,
            "cost_usd": 65.0,
            "assigned_fleet": "Field Sales",
        }

        ticket = tool.execute(args)

        assert ticket["ticket_id"].startswith("FP-")
        assert ticket["priority"] == "P2"  # RUL <= 14 -> P2
        assert ticket["status"] == "Draft"
        assert ticket["device"]["device_id"] == "DEV-APP-042"
        assert ticket["repair_details"]["part_number"] == "APL-BAT-A1B2C3"
        assert len(ticket["actions"]) == 6
        assert "LG Chem" in ticket["formatted_summary"]

    def test_ticket_tool_priority_escalation(self):
        """Verify priority P1 assigned when RUL <= 7 days."""
        tool = TicketTool()
        args = {
            "device_id": "DEV-CRIT-001",
            "device_model": "Galaxy S24",
            "issue_summary": "Imminent battery failure",
            "predicted_failure_component": "battery",
            "remaining_useful_life_days": 4.0,
        }
        ticket = tool.execute(args)
        assert ticket["priority"] == "P1"
        assert "Critical" in ticket["prediction"]["urgency"]

    def test_prediction_tool_execution(self):
        """Verify prediction tool returns fleet prediction list."""
        tool = PredictionTool()
        result = tool.execute({"fleet_name": "Executive", "time_horizon_days": 30})

        assert "devices" in result
        assert "total_count" in result
        assert "summary" in result
        assert isinstance(result["devices"], list)

    def test_rag_tool_parameter_validation(self):
        """Verify RAG tool requires both device_model and component."""
        tool = RAGTool()
        res_missing = tool.execute({"device_model": "iPhone 13"})
        assert res_missing["found"] is False
        assert "required" in res_missing["message"].lower()

    def test_agent_orchestration_loop(self):
        """Test agent invokes tools and synthesizes final answer."""
        # Step 1: LLM decides to call draft_remediation_ticket tool
        call_tool_resp = LLMResponse(
            content=None,
            tool_calls=[
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {
                        "name": "draft_remediation_ticket",
                        "arguments": '{"device_id": "DEV-TEST-99", "predicted_failure_component": "battery"}',
                    },
                }
            ],
            finish_reason="tool_use",
        )

        # Step 2: After tool result, LLM produces final answer
        final_resp = LLMResponse(
            content="I have drafted remediation ticket FP-TEST for device DEV-TEST-99.",
            tool_calls=[],
            finish_reason="stop",
        )

        mock_llm = MockLLMAdapter([call_tool_resp, final_resp])
        agent = FleetPulseAgent(llm=mock_llm)

        result = agent.chat("Draft a ticket for device DEV-TEST-99")

        assert "FP-TEST" in result["response"]
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["tool"] == "draft_remediation_ticket"

    def test_databricks_llm_adapter_factory(self):
        """Verify create_llm_adapter instantiates Databricks Foundation Model adapter."""
        from src.agent.llm_adapter import create_llm_adapter, OpenAIAdapter
        adapter = create_llm_adapter(
            provider="databricks",
            host="https://adb-123456789.cloud.databricks.com",
            token="dapi-test-token",
            model="databricks-meta-llama-3-1-70b-instruct",
        )
        assert isinstance(adapter, OpenAIAdapter)
        assert adapter.model == "databricks-meta-llama-3-1-70b-instruct"
        assert "serving-endpoints" in str(adapter.base_url)

