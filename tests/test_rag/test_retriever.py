"""
Unit tests for RAG Retriever and Confidence Threshold Guardrail.
"""

import json
from pathlib import Path

import pytest

from src.rag.retriever import FleetPulseRetriever


class TestRAGRetriever:
    def test_guardrail_rejection_below_threshold(self):
        """
        Guardrail test: verify that if search results score below confidence threshold,
        retriever returns escalation message and found=False, preventing hallucination.
        """
        retriever = FleetPulseRetriever(
            confidence_threshold=0.85,
            use_databricks=False,
            local_chunks_path="non_existent_path.json",
        )

        # Mock results below threshold
        mock_low_score_results = [
            {
                "chunk_id": "chunk-123",
                "document_type": "parts_catalog",
                "score": 0.62,
                "metadata_json": json.dumps({"part_number": "MOCK-123"}),
            }
        ]

        processed = retriever._process_results(
            results=mock_low_score_results,
            device_model="Exotic NonExistent Device 9000",
            component_type="flux_capacitor",
        )

        assert processed["found"] is False
        assert processed["confidence"] == 0.62
        assert "Escalate to IT" in processed["message"]
        assert processed["part_info"] is None

    def test_guardrail_acceptance_above_threshold(self):
        """
        Guardrail test: verify that when confidence exceeds threshold,
        structured part information and procedure are extracted and returned.
        """
        retriever = FleetPulseRetriever(
            confidence_threshold=0.75,
            use_databricks=False,
            local_chunks_path="non_existent_path.json",
        )

        mock_high_score_results = [
            {
                "chunk_id": "chunk-cat-01",
                "document_type": "parts_catalog",
                "score": 0.92,
                "metadata_json": json.dumps({
                    "part_number": "APL-BAT-998877",
                    "supplier": "LG Chem",
                    "cost_usd": 65.0,
                    "availability": "in_stock",
                    "repair_time_hours": 1.5,
                }),
            },
            {
                "chunk_id": "chunk-man-01",
                "document_type": "service_manual",
                "score": 0.88,
                "chunk_text": "Step 1: Unscrew pentalobe screws. Step 2: Use suction cup.",
            }
        ]

        processed = retriever._process_results(
            results=mock_high_score_results,
            device_model="iPhone 13",
            component_type="battery",
        )

        assert processed["found"] is True
        assert processed["confidence"] == 0.92
        assert processed["part_info"]["part_number"] == "APL-BAT-998877"
        assert processed["part_info"]["supplier"] == "LG Chem"
        assert processed["estimated_repair_time_hours"] == 1.5
        assert "Step 1: Unscrew pentalobe screws" in processed["repair_procedure"]

    def test_synthetic_parts_catalog_file(self):
        """Verify generated synthetic parts catalog exists and has valid schema."""
        catalog_path = Path("data/synthetic/parts_catalog.json")
        if not catalog_path.exists():
            pytest.skip("Synthetic catalog not generated yet.")

        with open(catalog_path, encoding="utf-8") as f:
            catalog = json.load(f)

        assert len(catalog) > 0
        first_item = catalog[0]
        assert "device_model" in first_item
        assert "component_type" in first_item
        assert "part_number" in first_item
        assert "supplier" in first_item
        assert "cost_usd" in first_item
