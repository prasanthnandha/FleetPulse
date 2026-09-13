"""
Unit tests for PII scrubbing and Anti-Hallucination Guardrails.
"""

from src.agent.agent import FleetPulseAgent
from src.agent.guardrails import sanitize_pii, validate_anti_hallucination
from src.agent.llm_adapter import BaseLLMAdapter, LLMMessage, LLMResponse


class MockLLM(BaseLLMAdapter):
    def __init__(self, response: LLMResponse):
        self.response = response

    def chat(self, messages: list[LLMMessage], tools=None, **kwargs):
        return self.response

    def stream_chat(self, messages: list[LLMMessage], tools=None, **kwargs):
        yield self.response.content or ""


class TestGuardrails:
    def test_pii_sanitization_email_and_phone(self):
        """Verify emails and phone numbers are scrubbed from text."""
        raw_text = (
            "Contact technician John at john.doe@enterprise.com or call +1 (555) 234-5678 "
            "regarding device DEV-1029."
        )
        sanitized = sanitize_pii(raw_text)

        assert "john.doe@enterprise.com" not in sanitized
        assert "[EMAIL_REDACTED]" in sanitized
        assert "+1 (555) 234-5678" not in sanitized
        assert "[PHONE_REDACTED]" in sanitized
        # Ensure device identifier is preserved
        assert "DEV-1029" in sanitized

    def test_pii_sanitization_tokens_and_financial(self):
        """Verify Databricks tokens, API keys, and credit cards are scrubbed."""
        # NOTE: token-like strings below are intentionally fake test fixtures
        # and do NOT represent real credentials.
        fake_token = "dapi" + "XXXX_FAKE_TEST_TOKEN_NOT_REAL_XXXX"
        secret_text = (
            f"Here is the token: {fake_token} and key sk-1234567890abcdef1234567890. "
            "Card number is 4111 2222 3333 4444 and SSN is 123-45-6789."
        )
        sanitized = sanitize_pii(secret_text)

        assert fake_token not in sanitized
        assert "[DATABRICKS_TOKEN_REDACTED]" in sanitized
        assert "sk-1234567890abcdef1234567890" not in sanitized
        assert "[API_KEY_REDACTED]" in sanitized
        assert "4111 2222 3333 4444" not in sanitized
        assert "[FINANCIAL_PII_REDACTED]" in sanitized
        assert "123-45-6789" not in sanitized
        assert "[SSN_REDACTED]" in sanitized

    def test_anti_hallucination_intercepts_fabricated_part(self):
        """
        Verify that if the LLM invents a part number not returned by the RAG tool,
        the guardrail intercepts and redacts it.
        """
        model_hallucination = (
            "I recommend replacing the screen using part SAM-DSP-FAB999 from supplier Acme."
        )
        tool_results = [
            {
                "found": True,
                "part_info": {
                    "part_number": "SAM-DSP-A1B2C3",
                    "supplier": "Samsung Display",
                }
            }
        ]

        is_valid, corrected = validate_anti_hallucination(model_hallucination, tool_results)

        assert is_valid is False
        assert "SAM-DSP-FAB999" not in corrected
        assert "[Unverified Part" in corrected
        assert "Safety Guardrail" in corrected

    def test_anti_hallucination_permits_verified_part(self):
        """
        Verify that legitimate part numbers verified by tool execution pass through safely.
        """
        model_valid_text = (
            "Order replacement battery part APL-BAT-998877 from LG Chem."
        )
        tool_results = [
            {
                "found": True,
                "part_info": {
                    "part_number": "APL-BAT-998877",
                    "supplier": "LG Chem",
                }
            }
        ]

        is_valid, text = validate_anti_hallucination(model_valid_text, tool_results)

        assert is_valid is True
        assert "APL-BAT-998877" in text

    def test_agent_chat_scrubs_incoming_user_pii(self):
        """
        Verify agent automatically scrubs user PII from prompts before
        adding to the internal LLM conversation memory.
        """
        mock_response = LLMResponse(content="Device DEV-102 checked. Health is nominal.")
        mock_llm = MockLLM(mock_response)
        agent = FleetPulseAgent(llm=mock_llm)

        user_prompt_with_pii = "Check the phone for user bob@example.com, phone 555-123-4567, device DEV-102."
        agent.chat(user_prompt_with_pii)

        # Inspect history: the user message stored in LLM context MUST be sanitized
        user_history_entry = agent._conversation_history[1]
        assert user_history_entry.role == "user"
        assert "bob@example.com" not in user_history_entry.content
        assert "[EMAIL_REDACTED]" in user_history_entry.content
        assert "555-123-4567" not in user_history_entry.content
        assert "[PHONE_REDACTED]" in user_history_entry.content
        assert "DEV-102" in user_history_entry.content
