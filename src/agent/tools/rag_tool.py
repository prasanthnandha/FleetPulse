"""
FleetPulse — RAG Tool
======================
Agent tool wrapper for the RAG retriever.
Retrieves device repair info (part numbers, procedures, costs).
"""

from src.rag.retriever import FleetPulseRetriever


class RAGTool:
    """Wraps FleetPulseRetriever as an agent tool."""

    def __init__(self, retriever: FleetPulseRetriever | None = None, **kwargs):
        self.retriever = retriever or FleetPulseRetriever(**kwargs)

    def execute(self, arguments: dict) -> dict:
        """
        Execute RAG lookup.

        Args:
            arguments: Tool call arguments:
                - device_model (str): Device model name
                - predicted_failure_component (str): Component type

        Returns:
            Retriever result dict with part info, repair procedure, and confidence.
        """
        device_model = arguments.get("device_model", "")
        component = arguments.get("predicted_failure_component", "")

        if not device_model or not component:
            return {
                "found": False,
                "confidence": 0.0,
                "message": "Both device_model and predicted_failure_component are required.",
            }

        result = self.retriever.get_device_repair_info(device_model, component)
        return result
