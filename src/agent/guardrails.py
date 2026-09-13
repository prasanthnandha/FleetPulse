"""
FleetPulse — Guardrails & Safety Sanitizer
============================================
Programmatic guardrails to:
1. Scrub and redact Personally Identifiable Information (PII) and credentials.
2. Prevent and detect model hallucinations (verifying part numbers and facts against tool outputs).
"""

import re
from typing import Any


# ==============================================================================
# PII Patterns
# ==============================================================================

PATTERNS = {
    # Email addresses
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),
    # Phone numbers (international and US formats)
    "phone": re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    # Social Security Numbers / National IDs
    "ssn": re.compile(r"\b\d{3}[-]?\d{2}[-]?\d{4}\b"),
    # Credit Card / Debit Card Numbers
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    # Databricks Tokens (dapi...)
    "databricks_token": re.compile(r"\bdapi[a-f0-9]{32}(?:-[0-9]+)?\b", re.IGNORECASE),
    # OpenAI / Anthropic API Keys (sk-...)
    "api_key": re.compile(r"\b(?:sk-[a-zA-Z0-9]{20,60}|sk-ant-[a-zA-Z0-9]{20,60})\b"),
    # IMEI numbers (15 digits)
    "imei": re.compile(r"\bIMEI[:\s]+[0-9]{15}\b", re.IGNORECASE),
    # IP Addresses (IPv4)
    "ipv4": re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"),
}


def sanitize_pii(text: str) -> str:
    """
    Sanitizes and redacts PII and sensitive credentials from text.

    Args:
        text: Input string to scan.

    Returns:
        Sanitized string with sensitive data replaced by redaction markers.
    """
    if not text or not isinstance(text, str):
        return text

    sanitized = text

    # Redact tokens & API keys first
    sanitized = PATTERNS["databricks_token"].sub("[DATABRICKS_TOKEN_REDACTED]", sanitized)
    sanitized = PATTERNS["api_key"].sub("[API_KEY_REDACTED]", sanitized)

    # Redact personal identification & financial PII
    sanitized = PATTERNS["credit_card"].sub("[FINANCIAL_PII_REDACTED]", sanitized)
    sanitized = PATTERNS["ssn"].sub("[SSN_REDACTED]", sanitized)
    sanitized = PATTERNS["email"].sub("[EMAIL_REDACTED]", sanitized)
    sanitized = PATTERNS["phone"].sub("[PHONE_REDACTED]", sanitized)
    sanitized = PATTERNS["imei"].sub("IMEI: [REDACTED]", sanitized)

    # Redact private IP addresses (ignoring localhost / 0.0.0.0 / 127.0.0.1)
    def _sanitize_ip(match):
        ip = match.group(0)
        if ip in ("127.0.0.1", "0.0.0.0", "255.255.255.255"):
            return ip
        # Check private ranges (10.x, 192.168.x, 172.16-31.x)
        if ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172."):
            return "[INTERNAL_IP_REDACTED]"
        return "[IP_REDACTED]"

    sanitized = PATTERNS["ipv4"].sub(_sanitize_ip, sanitized)

    return sanitized


# ==============================================================================
# Anti-Hallucination Grounding Validator
# ==============================================================================

PART_NUMBER_PATTERN = re.compile(r"\b([A-Z]{3}-[A-Z]{3}-[A-F0-9]{6})\b")


def validate_anti_hallucination(response_text: str, tool_results: list[dict]) -> tuple[bool, str]:
    """
    Validates that any specific part numbers or critical hardware claims in the
    response actually originated from verified tool results.

    If the model hallucinates a part number when retrieval failed or was not called,
    the hallucinated code is intercepted.

    Args:
        response_text: Generated assistant message.
        tool_results: List of tool execution result dictionaries.

    Returns:
        (is_valid: bool, corrected_or_original_text: str)
    """
    if not response_text or not isinstance(response_text, str):
        return True, response_text

    # Extract all verified part numbers from tool results
    verified_part_numbers = set()
    for res in tool_results:
        if not isinstance(res, dict):
            continue
        # From RAG tool
        part_info = res.get("part_info")
        if isinstance(part_info, dict) and part_info.get("part_number"):
            verified_part_numbers.add(part_info["part_number"].upper())
        if res.get("part_number"):
            verified_part_numbers.add(str(res.get("part_number")).upper())

        # From ticket tool
        repair_details = res.get("repair_details")
        if isinstance(repair_details, dict) and repair_details.get("part_number"):
            verified_part_numbers.add(repair_details["part_number"].upper())

    # Find part numbers in generated text
    found_parts_in_text = PART_NUMBER_PATTERN.findall(response_text)

    hallucinations = []
    corrected_text = response_text

    for part in found_parts_in_text:
        part_upper = part.upper()
        if part_upper not in verified_part_numbers:
            hallucinations.append(part)
            # Replace hallucinated part number with escalation notice
            corrected_text = corrected_text.replace(
                part,
                "[Unverified Part — Escalate to IT Hardware Support]"
            )

    if hallucinations:
        # Append anti-hallucination disclosure if fabricated part was detected
        corrected_text += (
            "\n\n> ⚠️ **FleetPulse Safety Guardrail**: An unverified part number "
            "was intercepted and redacted to avoid hardware replacement errors. "
            "Please confirm with the IT hardware team."
        )
        return False, corrected_text

    return True, corrected_text
