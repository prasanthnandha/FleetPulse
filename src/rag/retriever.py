"""
FleetPulse — RAG Retriever
============================
Query interface for retrieving device repair info from Vector Search
or local embeddings. Includes confidence threshold guardrail.

Usage:
    from src.rag.retriever import FleetPulseRetriever

    retriever = FleetPulseRetriever()
    result = retriever.get_device_repair_info("iPhone 13", "battery")
"""

import json
import os
from pathlib import Path

import numpy as np


class FleetPulseRetriever:
    """
    Retrieves device repair information from the Vector Search index
    or local document chunks.

    Implements a confidence threshold guardrail: only returns results if
    similarity score exceeds the threshold, otherwise responds with an
    escalation message.
    """

    ESCALATION_MESSAGE = (
        "No confident match found for this device/component combination. "
        "Escalate to IT hardware team for manual lookup."
    )

    def __init__(
        self,
        confidence_threshold: float = 0.75,
        use_databricks: bool = False,
        index_name: str | None = None,
        endpoint_name: str | None = None,
        local_chunks_path: str | None = None,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        """
        Args:
            confidence_threshold: Minimum similarity score to return results (0-1).
            use_databricks: If True, query Databricks Vector Search. If False, use local search.
            index_name: Databricks Vector Search index name.
            endpoint_name: Databricks Vector Search endpoint name.
            local_chunks_path: Path to local chunks.json for local search.
            embedding_model_name: Model for embedding queries.
        """
        self.confidence_threshold = confidence_threshold
        self.use_databricks = use_databricks
        self.index_name = index_name or os.getenv("VECTOR_SEARCH_INDEX", "fleetpulse.rag.document_chunks_index")
        self.endpoint_name = endpoint_name or os.getenv("VECTOR_SEARCH_ENDPOINT", "fleetpulse-vs-endpoint")
        self.embedding_model_name = embedding_model_name

        # Local search state
        self._local_chunks = None
        self._local_embeddings = None
        self._embedding_model = None

        if not use_databricks:
            self._local_chunks_path = local_chunks_path or "data/processed/document_chunks/chunks.json"
            self._load_local_chunks()

    # ══════════════════════════════════════════════════════════════════════
    # Public API
    # ══════════════════════════════════════════════════════════════════════

    def get_device_repair_info(
        self,
        device_model: str,
        predicted_failure_component: str,
        top_k: int = 5,
    ) -> dict:
        """
        Retrieve repair/part info for a specific device and failing component.

        Args:
            device_model: Device model name (e.g., "iPhone 13")
            predicted_failure_component: Component type (e.g., "battery", "display")
            top_k: Number of results to retrieve before filtering

        Returns:
            Dict with:
                - "found": bool — whether a confident match was found
                - "confidence": float — highest similarity score
                - "part_info": dict | None — part number, supplier, cost, etc.
                - "repair_procedure": str | None — step-by-step repair instructions
                - "estimated_repair_time_hours": float | None
                - "message": str — human-readable summary or escalation message
        """
        query = (
            f"Repair procedure and replacement part for "
            f"{predicted_failure_component.replace('_', ' ')} "
            f"on {device_model}"
        )

        if self.use_databricks:
            results = self._search_databricks(query, device_model, predicted_failure_component, top_k)
        else:
            results = self._search_local(query, device_model, predicted_failure_component, top_k)

        return self._process_results(results, device_model, predicted_failure_component)

    def search(self, query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
        """
        General-purpose search across all documents.

        Args:
            query: Natural language search query
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of search results with scores
        """
        if self.use_databricks:
            return self._search_databricks(query, filters=filters, top_k=top_k)
        else:
            return self._search_local(query, top_k=top_k, filters=filters)

    # ══════════════════════════════════════════════════════════════════════
    # Databricks Vector Search
    # ══════════════════════════════════════════════════════════════════════

    def _search_databricks(
        self,
        query: str,
        device_model: str | None = None,
        component_type: str | None = None,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[dict]:
        """Search using Databricks Vector Search."""
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()

        # Build filter string
        filter_conditions = []
        if device_model:
            filter_conditions.append(f"device_model = '{device_model}'")
        if component_type:
            filter_conditions.append(f"component_type = '{component_type}'")
        if filters:
            for k, v in filters.items():
                filter_conditions.append(f"{k} = '{v}'")

        filter_str = " AND ".join(filter_conditions) if filter_conditions else None

        try:
            response = w.vector_search_indexes.query_index(
                index_name=self.index_name,
                columns=["chunk_id", "chunk_text", "document_type", "device_model", "component_type", "metadata_json"],
                query_text=query,
                num_results=top_k,
                filters_json=filter_str,
            )

            results = []
            if response.result and response.result.data_array:
                columns = [c.name for c in response.manifest.columns]
                for row in response.result.data_array:
                    result = dict(zip(columns, row))
                    result["score"] = result.get("score", 0.0)
                    results.append(result)

            return results

        except Exception as e:
            print(f"Vector Search query error: {e}")
            return []

    # ══════════════════════════════════════════════════════════════════════
    # Local Search (for development)
    # ══════════════════════════════════════════════════════════════════════

    def _load_local_chunks(self):
        """Load chunks from local JSON file."""
        path = Path(self._local_chunks_path)
        if not path.exists():
            print(f"Local chunks not found at {path}. Retriever will return empty results.")
            self._local_chunks = []
            self._local_embeddings = None
            return

        with open(path) as f:
            self._local_chunks = json.load(f)

        # Extract embeddings into numpy array
        embeddings = []
        valid_chunks = []
        for chunk in self._local_chunks:
            if chunk.get("embedding"):
                embeddings.append(chunk["embedding"])
                valid_chunks.append(chunk)

        if embeddings:
            self._local_embeddings = np.array(embeddings, dtype=np.float32)
            self._local_chunks = valid_chunks
            print(f"Loaded {len(valid_chunks)} chunks with embeddings")
        else:
            self._local_embeddings = None
            print("No embeddings found in local chunks")

    def _get_embedding_model(self):
        """Lazy-load the embedding model."""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            self._embedding_model = SentenceTransformer(self.embedding_model_name)
        return self._embedding_model

    def _search_local(
        self,
        query: str,
        device_model: str | None = None,
        component_type: str | None = None,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[dict]:
        """Search using local embeddings with cosine similarity."""
        if not self._local_chunks or self._local_embeddings is None:
            return []

        # Pre-filter by device_model and component_type if specified
        mask = np.ones(len(self._local_chunks), dtype=bool)
        for i, chunk in enumerate(self._local_chunks):
            if device_model and chunk.get("device_model"):
                if device_model.lower() not in chunk["device_model"].lower():
                    mask[i] = False
            if component_type and chunk.get("component_type"):
                if component_type.lower() != chunk["component_type"].lower():
                    mask[i] = False
            if filters:
                for k, v in filters.items():
                    if str(chunk.get(k, "")).lower() != str(v).lower():
                        mask[i] = False

        if not mask.any():
            # Relax filter — search all chunks
            mask = np.ones(len(self._local_chunks), dtype=bool)

        # Embed query
        model = self._get_embedding_model()
        query_embedding = model.encode([query], normalize_embeddings=True).astype(np.float32)

        # Cosine similarity (embeddings are already normalized)
        filtered_embeddings = self._local_embeddings[mask]
        similarities = np.dot(filtered_embeddings, query_embedding.T).flatten()

        # Get top-k indices
        filtered_indices = np.where(mask)[0]
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            chunk_idx = filtered_indices[idx]
            chunk = self._local_chunks[chunk_idx]
            results.append(
                {
                    **chunk,
                    "score": float(similarities[idx]),
                }
            )

        return results

    # ══════════════════════════════════════════════════════════════════════
    # Result Processing
    # ══════════════════════════════════════════════════════════════════════

    def _process_results(
        self,
        results: list[dict],
        device_model: str,
        component_type: str,
    ) -> dict:
        """
        Process search results and apply confidence threshold guardrail.
        """
        if not results:
            return {
                "found": False,
                "confidence": 0.0,
                "part_info": None,
                "repair_procedure": None,
                "estimated_repair_time_hours": None,
                "message": self.ESCALATION_MESSAGE,
            }

        # Find best result above threshold
        best_result = results[0]
        best_score = best_result.get("score", 0.0)

        # ── Guardrail: confidence threshold ──────────────────────────────
        if best_score < self.confidence_threshold:
            return {
                "found": False,
                "confidence": round(best_score, 4),
                "part_info": None,
                "repair_procedure": None,
                "estimated_repair_time_hours": None,
                "message": (
                    f"{self.ESCALATION_MESSAGE} "
                    f"(Best match confidence: {best_score:.2f}, "
                    f"threshold: {self.confidence_threshold})"
                ),
            }

        # ── Extract structured info ──────────────────────────────────────
        part_info = None
        repair_procedure = None
        repair_time = None

        # Look for catalog entry (structured part info)
        catalog_results = [r for r in results if r.get("document_type") == "parts_catalog"]
        manual_results = [r for r in results if r.get("document_type") == "service_manual"]

        if catalog_results:
            cat = catalog_results[0]
            try:
                metadata = json.loads(cat.get("metadata_json", "{}"))
                part_info = {
                    "part_number": metadata.get("part_number"),
                    "supplier": metadata.get("supplier"),
                    "cost_usd": metadata.get("cost_usd"),
                    "availability": metadata.get("availability"),
                    "manufacturer": metadata.get("manufacturer"),
                }
                repair_time = metadata.get("repair_time_hours")
            except (json.JSONDecodeError, TypeError):
                pass

        if manual_results:
            repair_procedure = manual_results[0].get("chunk_text", "")

        # Build human-readable message
        message_parts = [f"Found repair information for {device_model} {component_type.replace('_', ' ')}:"]
        if part_info and part_info.get("part_number"):
            message_parts.append(f"  Part Number: {part_info['part_number']}")
            message_parts.append(f"  Supplier: {part_info.get('supplier', 'N/A')}")
            message_parts.append(f"  Cost: ${part_info.get('cost_usd', 'N/A')}")
            message_parts.append(f"  Availability: {part_info.get('availability', 'N/A')}")
        if repair_time:
            message_parts.append(f"  Estimated Repair Time: {repair_time} hours")

        return {
            "found": True,
            "confidence": round(best_score, 4),
            "part_info": part_info,
            "repair_procedure": repair_procedure,
            "estimated_repair_time_hours": repair_time,
            "message": "\n".join(message_parts),
        }
