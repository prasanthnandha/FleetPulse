"""
FleetPulse — Vector Search Index Management
=============================================
Creates and syncs a Databricks Vector Search index from the document_chunks
Delta table. Supports both managed embeddings and pre-computed embedding columns.

Usage (Databricks):
    python -m src.rag.index_vector_search \
        --source-table fleetpulse.rag.document_chunks \
        --index-name fleetpulse.rag.document_chunks_index \
        --endpoint-name fleetpulse-vs-endpoint
"""

import argparse
import time

from databricks.sdk import WorkspaceClient


def create_or_update_index(
    source_table: str,
    index_name: str,
    endpoint_name: str,
    embedding_column: str = "embedding",
    embedding_dimension: int = 384,
    primary_key: str = "chunk_id",
    text_column: str = "chunk_text",
    use_managed_embeddings: bool = False,
    embedding_model: str = "databricks-bge-large-en",
):
    """
    Create or sync a Databricks Vector Search index.

    Args:
        source_table: Delta table containing the chunks (e.g., "fleetpulse.rag.document_chunks")
        index_name: Name for the vector search index
        endpoint_name: Vector Search endpoint name
        embedding_column: Column containing pre-computed embeddings (if not using managed)
        embedding_dimension: Dimension of the embedding vectors
        primary_key: Primary key column in the source table
        text_column: Column containing the text to search
        use_managed_embeddings: If True, use Databricks-managed embeddings
        embedding_model: Model name for managed embeddings
    """
    w = WorkspaceClient()

    # ── Ensure endpoint exists ───────────────────────────────────────────
    print(f"Checking Vector Search endpoint '{endpoint_name}'...")
    try:
        endpoint = w.vector_search_endpoints.get_endpoint(endpoint_name)
        print(f"  Endpoint exists: {endpoint.name} (status: {endpoint.endpoint_status})")
    except Exception:
        print(f"  Creating endpoint '{endpoint_name}'...")
        w.vector_search_endpoints.create_endpoint(
            name=endpoint_name,
            endpoint_type="STANDARD",
        )
        # Wait for endpoint to be ready
        for _ in range(60):
            endpoint = w.vector_search_endpoints.get_endpoint(endpoint_name)
            if endpoint.endpoint_status and endpoint.endpoint_status.state == "ONLINE":
                break
            print(f"  Waiting for endpoint... (status: {endpoint.endpoint_status})")
            time.sleep(10)
        print("  Endpoint created and online.")

    # ── Create or sync index ─────────────────────────────────────────────
    print(f"Setting up index '{index_name}'...")

    try:
        # Check if index exists
        w.vector_search_indexes.get_index(index_name)
        print("  Index exists. Syncing...")
        w.vector_search_indexes.sync_index(index_name)
        print("  Sync initiated.")
        return

    except Exception:
        pass  # Index doesn't exist — create it

    # Create index
    if use_managed_embeddings:
        print(f"  Creating managed embedding index with model '{embedding_model}'...")
        w.vector_search_indexes.create_index(
            name=index_name,
            endpoint_name=endpoint_name,
            primary_key=primary_key,
            index_type="DELTA_SYNC",
            delta_sync_index_spec={
                "source_table": source_table,
                "embedding_source_columns": [
                    {
                        "name": text_column,
                        "embedding_model_endpoint_name": embedding_model,
                    }
                ],
                "pipeline_type": "TRIGGERED",
            },
        )
    else:
        print(f"  Creating pre-computed embedding index (dim={embedding_dimension})...")
        w.vector_search_indexes.create_index(
            name=index_name,
            endpoint_name=endpoint_name,
            primary_key=primary_key,
            index_type="DELTA_SYNC",
            delta_sync_index_spec={
                "source_table": source_table,
                "embedding_vector_columns": [
                    {
                        "name": embedding_column,
                        "embedding_dimension": embedding_dimension,
                    }
                ],
                "pipeline_type": "TRIGGERED",
            },
        )

    print(f"  Index '{index_name}' created. Initial sync will begin automatically.")

    # Wait for initial sync
    print("  Waiting for initial sync to complete...")
    for _ in range(120):
        try:
            idx = w.vector_search_indexes.get_index(index_name)
            status = idx.status
            if status and status.ready:
                print(f"  Index is ready! Indexed {status.indexed_row_count} rows.")
                return
            print(f"  Sync in progress... ({status.indexed_row_count if status else '?'} rows)")
        except Exception as e:
            print(f"  Checking status... ({e})")
        time.sleep(15)

    print("  WARNING: Index sync did not complete within timeout. Check Databricks UI.")


def upload_chunks_to_delta(
    chunks_parquet_path: str,
    target_table: str,
):
    """
    Upload local chunks Parquet file to a Delta table via Spark.
    Run this on Databricks or with a local Spark session configured for Delta.
    """
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.appName("FleetPulse-VectorSearchUpload")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )

    print(f"Reading chunks from {chunks_parquet_path}...")
    df = spark.read.parquet(chunks_parquet_path)

    print(f"Writing {df.count()} chunks to {target_table}...")
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(target_table)

    print(f"Chunks uploaded to {target_table}")


# ==============================================================================
# CLI
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FleetPulse Vector Search Index Management")
    parser.add_argument("--source-table", default="fleetpulse.rag.document_chunks")
    parser.add_argument("--index-name", default="fleetpulse.rag.document_chunks_index")
    parser.add_argument("--endpoint-name", default="fleetpulse-vs-endpoint")
    parser.add_argument("--upload-chunks", default=None, help="Path to chunks.parquet to upload first")
    parser.add_argument("--managed-embeddings", action="store_true")
    args = parser.parse_args()

    if args.upload_chunks:
        upload_chunks_to_delta(args.upload_chunks, args.source_table)

    create_or_update_index(
        source_table=args.source_table,
        index_name=args.index_name,
        endpoint_name=args.endpoint_name,
        use_managed_embeddings=args.managed_embeddings,
    )
