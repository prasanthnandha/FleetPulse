"""
FleetPulse — Document Chunking & Embedding Pipeline
=====================================================
Chunks service manuals and parts catalog using recursive text splitting,
embeds with sentence-transformers, and prepares for Vector Search indexing.

Usage:
    python -m src.rag.chunk_and_embed \
        --catalog-path data/synthetic/parts_catalog.json \
        --manuals-dir data/synthetic/service_manuals/ \
        --output-path data/processed/document_chunks/
"""

import argparse
import hashlib
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


# ==============================================================================
# Text Chunking
# ==============================================================================

class RecursiveTextSplitter:
    """
    Splits text into chunks using a hierarchy of separators,
    attempting to keep semantically related content together.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: list[str] | None = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n## ", "\n### ", "\n\n", "\n", ". ", " "]

    def split_text(self, text: str) -> list[str]:
        """Split text into chunks using recursive separator hierarchy."""
        chunks = self._split_recursive(text, self.separators)
        return [c.strip() for c in chunks if c.strip()]

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]

        if not separators:
            # Last resort: split by character count
            return self._split_by_size(text)

        separator = separators[0]
        remaining_separators = separators[1:]

        parts = text.split(separator)
        if len(parts) == 1:
            # Separator not found — try next one
            return self._split_recursive(text, remaining_separators)

        chunks = []
        current_chunk = ""

        for part in parts:
            candidate = current_chunk + separator + part if current_chunk else part

            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(part) > self.chunk_size:
                    # Part itself is too large — recurse with next separator
                    sub_chunks = self._split_recursive(part, remaining_separators)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)

        # Add overlap
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks)

        return chunks

    def _split_by_size(self, text: str) -> list[str]:
        """Fallback: split by character count with overlap."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start = end - self.chunk_overlap
        return chunks

    def _add_overlap(self, chunks: list[str]) -> list[str]:
        """Add overlap from previous chunk's end to current chunk's start."""
        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_end = chunks[i - 1][-self.chunk_overlap:]
            result.append(prev_end + " " + chunks[i])
        return result


# ==============================================================================
# Embedding
# ==============================================================================

class EmbeddingModel:
    """Wrapper for sentence-transformer embedding model."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model: {self.model_name}...")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        """Embed a list of texts, returning (N, D) array of float32."""
        model = self._load_model()
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        return embeddings.astype(np.float32)

    @property
    def dimension(self) -> int:
        """Embedding dimension."""
        model = self._load_model()
        return model.get_sentence_embedding_dimension()


# ==============================================================================
# Chunking Pipeline
# ==============================================================================

def chunk_parts_catalog(catalog_path: str) -> list[dict]:
    """
    Chunk the parts catalog into individual entries.
    Each part becomes one chunk with structured metadata.
    """
    with open(catalog_path) as f:
        catalog = json.load(f)

    chunks = []
    for item in catalog:
        # Create a rich text representation of the part
        text = (
            f"Device: {item['device_model']} ({item['manufacturer']})\n"
            f"Component: {item['component_type'].replace('_', ' ').title()}\n"
            f"Description: {item['component_description']}\n"
            f"Part Number: {item['part_number']}\n"
            f"Supplier: {item['supplier']}\n"
            f"Cost: ${item['cost_usd']:.2f}\n"
            f"Estimated Repair Time: {item['estimated_repair_time_hours']} hours\n"
            f"Availability: {item['availability']}\n"
            f"Warranty: {item['warranty_months']} months"
        )

        chunk_id = hashlib.sha256(f"{item['device_model']}_{item['component_type']}".encode()).hexdigest()[:12]

        chunks.append({
            "chunk_id": f"cat_{chunk_id}",
            "document_id": f"catalog_{item['device_model'].replace(' ', '_')}",
            "document_type": "parts_catalog",
            "device_model": item["device_model"],
            "component_type": item["component_type"],
            "chunk_text": text,
            "chunk_index": 0,
            "metadata_json": json.dumps({
                "part_number": item["part_number"],
                "supplier": item["supplier"],
                "cost_usd": item["cost_usd"],
                "repair_time_hours": item["estimated_repair_time_hours"],
                "availability": item["availability"],
                "manufacturer": item["manufacturer"],
            }),
        })

    return chunks


def chunk_service_manuals(manuals_dir: str) -> list[dict]:
    """
    Chunk service manual Markdown files using recursive text splitting.
    Preserves section context in metadata.
    """
    splitter = RecursiveTextSplitter(chunk_size=512, chunk_overlap=50)
    chunks = []

    manuals_path = Path(manuals_dir)
    if not manuals_path.exists():
        print(f"Manuals directory not found: {manuals_dir}")
        return []

    for md_file in sorted(manuals_path.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        device_model = md_file.stem.replace("_", " ")

        # Split by major sections first
        sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)

        for section in sections:
            if not section.strip():
                continue

            # Extract section title
            section_match = re.match(r"^##\s+(.+?)(?:\n|$)", section)
            section_title = section_match.group(1) if section_match else "General"

            # Extract component type from section title
            component_type = None
            for comp in ["battery", "display", "logic_board", "charging_port",
                         "camera_module", "speaker", "antenna", "storage",
                         "keyboard", "trackpad"]:
                if comp.replace("_", " ") in section_title.lower():
                    component_type = comp
                    break

            # Chunk the section
            section_chunks = splitter.split_text(section)

            for i, chunk_text in enumerate(section_chunks):
                chunk_id = hashlib.sha256(
                    f"{device_model}_{section_title}_{i}".encode()
                ).hexdigest()[:12]

                chunks.append({
                    "chunk_id": f"man_{chunk_id}",
                    "document_id": f"manual_{md_file.stem}",
                    "document_type": "service_manual",
                    "device_model": device_model,
                    "component_type": component_type,
                    "chunk_text": chunk_text,
                    "chunk_index": i,
                    "metadata_json": json.dumps({
                        "section_title": section_title,
                        "source_file": md_file.name,
                    }),
                })

    return chunks


def run_chunking_and_embedding(
    catalog_path: str = "data/synthetic/parts_catalog.json",
    manuals_dir: str = "data/synthetic/service_manuals/",
    output_path: str = "data/processed/document_chunks/",
    embed: bool = True,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
):
    """
    Main pipeline: chunk documents, embed, and save.
    """
    now = datetime.utcnow()

    # ── Chunk documents ──────────────────────────────────────────────────
    print("Chunking parts catalog...")
    catalog_chunks = chunk_parts_catalog(catalog_path)
    print(f"  → {len(catalog_chunks)} catalog chunks")

    print("Chunking service manuals...")
    manual_chunks = chunk_service_manuals(manuals_dir)
    print(f"  → {len(manual_chunks)} manual chunks")

    all_chunks = catalog_chunks + manual_chunks
    print(f"Total chunks: {len(all_chunks)}")

    # ── Embed ────────────────────────────────────────────────────────────
    if embed:
        embedder = EmbeddingModel(model_name)
        texts = [c["chunk_text"] for c in all_chunks]

        print(f"Embedding {len(texts)} chunks...")
        embeddings = embedder.embed(texts)
        print(f"Embedding dimension: {embeddings.shape[1]}")

        for i, chunk in enumerate(all_chunks):
            chunk["embedding"] = embeddings[i].tolist()
    else:
        for chunk in all_chunks:
            chunk["embedding"] = None

    # Add timestamp
    for chunk in all_chunks:
        chunk["created_at"] = now.isoformat()

    # ── Save ─────────────────────────────────────────────────────────────
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save as JSON (for inspection)
    json_path = output_dir / "chunks.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, default=str)
    print(f"Saved JSON to {json_path}")

    # Save as Parquet (for Delta/Spark ingestion)
    df = pd.DataFrame(all_chunks)
    parquet_path = output_dir / "chunks.parquet"
    df.to_parquet(parquet_path, index=False)
    print(f"Saved Parquet to {parquet_path}")

    # Print summary
    print(f"\n── Chunk Summary ──")
    print(f"Catalog chunks:     {len(catalog_chunks)}")
    print(f"Manual chunks:      {len(manual_chunks)}")
    print(f"Total chunks:       {len(all_chunks)}")
    if embed:
        print(f"Embedding dim:      {embeddings.shape[1]}")
    print(f"Output:             {output_dir}")

    return all_chunks


# ==============================================================================
# CLI
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FleetPulse Document Chunking & Embedding")
    parser.add_argument("--catalog-path", default="data/synthetic/parts_catalog.json")
    parser.add_argument("--manuals-dir", default="data/synthetic/service_manuals/")
    parser.add_argument("--output-path", default="data/processed/document_chunks/")
    parser.add_argument("--no-embed", action="store_true", help="Skip embedding step")
    parser.add_argument("--model-name", default="sentence-transformers/all-MiniLM-L6-v2")
    args = parser.parse_args()

    run_chunking_and_embedding(
        catalog_path=args.catalog_path,
        manuals_dir=args.manuals_dir,
        output_path=args.output_path,
        embed=not args.no_embed,
        model_name=args.model_name,
    )
