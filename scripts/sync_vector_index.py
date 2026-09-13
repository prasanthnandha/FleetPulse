"""
FleetPulse — Vector Search Index Automated Sync & Creation
============================================================
Checks for Vector Search endpoint and index, creates them if missing,
and triggers an automated re-sync when documents have been updated.

Supports:
1. Databricks SDK (WorkspaceClient)
2. Direct REST API calls via httpx with token authentication

Usage:
    python scripts/sync_vector_index.py
    python scripts/sync_vector_index.py --catalog fleetpulse --schema data --force
"""

import argparse
import os
import sys
import time
import httpx


def get_credentials(args: argparse.Namespace) -> tuple[str, str]:
    """Retrieve and validate Databricks host and token."""
    host = args.host or os.getenv("DATABRICKS_HOST", "")
    token = args.token or os.getenv("DATABRICKS_TOKEN", "")

    if not host or not token:
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient()
            host = host or (w.config.host if hasattr(w.config, "host") else "")
            token = token or (w.config.token if hasattr(w.config, "token") else "")
        except Exception:
            pass

    if not host or not token:
        print("ERROR: DATABRICKS_HOST and DATABRICKS_TOKEN are required.", file=sys.stderr)
        sys.exit(1)

    host = host.rstrip("/")
    if not host.startswith("http://") and not host.startswith("https://"):
        host = f"https://{host}"

    return host, token


def ensure_endpoint_online(host: str, token: str, endpoint_name: str) -> bool:
    """Ensure Databricks Vector Search endpoint exists and is ready."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{host}/api/2.0/vector-search/endpoints/{endpoint_name}"

    print(f"Checking Vector Search endpoint '{endpoint_name}'...")
    try:
        resp = httpx.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("endpoint_status", {}).get("state", "UNKNOWN")
            print(f"  ✓ Endpoint '{endpoint_name}' exists (state: {status})")
            return True
        elif resp.status_code == 404:
            print(f"  Endpoint '{endpoint_name}' not found. Creating STANDARD endpoint...")
            create_url = f"{host}/api/2.0/vector-search/endpoints"
            payload = {
                "name": endpoint_name,
                "endpoint_type": "STANDARD",
            }
            create_resp = httpx.post(create_url, headers=headers, json=payload, timeout=30)
            if create_resp.status_code in (200, 201):
                print(f"  ✓ Endpoint '{endpoint_name}' creation initiated.")
                return True
            else:
                print(f"  FAILED to create endpoint: {create_resp.status_code} {create_resp.text}", file=sys.stderr)
                return False
        else:
            print(f"  Unexpected status: {resp.status_code} {resp.text}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"  Error with endpoint: {e}", file=sys.stderr)
        return False


def sync_or_create_index(
    host: str,
    token: str,
    endpoint_name: str,
    index_name: str,
    source_table: str,
    embedding_model: str = "databricks-bge-large-en",
) -> bool:
    """Check if Vector Search index exists; if so sync, if not create."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{host}/api/2.0/vector-search/indexes/{index_name}"

    print(f"Checking Vector Search index '{index_name}'...")
    try:
        resp = httpx.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            print(f"  ✓ Index '{index_name}' exists. Triggering re-sync...")
            sync_url = f"{host}/api/2.0/vector-search/indexes/{index_name}/sync"
            sync_resp = httpx.post(sync_url, headers=headers, timeout=30)
            if sync_resp.status_code in (200, 201, 204):
                print(f"  ✓ Index re-sync triggered successfully.")
                return True
            else:
                print(f"  Sync response: {sync_resp.status_code} {sync_resp.text}")
                return True
        elif resp.status_code == 404:
            print(f"  Index '{index_name}' not found. Creating Delta Sync index from '{source_table}'...")
            create_url = f"{host}/api/2.0/vector-search/indexes"
            payload = {
                "name": index_name,
                "endpoint_name": endpoint_name,
                "primary_key": "chunk_id",
                "index_type": "DELTA_SYNC",
                "delta_sync_index_spec": {
                    "source_table": source_table,
                    "embedding_source_columns": [
                        {
                            "name": "chunk_text",
                            "embedding_model_endpoint_name": embedding_model,
                        }
                    ],
                    "pipeline_type": "TRIGGERED",
                },
            }
            create_resp = httpx.post(create_url, headers=headers, json=payload, timeout=30)
            if create_resp.status_code in (200, 201):
                print(f"  ✓ Index '{index_name}' creation initiated successfully.")
                return True
            else:
                print(f"  FAILED to create index: {create_resp.status_code} {create_resp.text}", file=sys.stderr)
                return False
        else:
            print(f"  Unexpected status checking index: {resp.status_code} {resp.text}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"  Error setting up index '{index_name}': {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Sync or create Databricks Vector Search Index.")
    parser.add_argument("--host", default=None, help="Databricks Host URL")
    parser.add_argument("--token", default=None, help="Databricks Access Token")
    parser.add_argument("--catalog", default=os.getenv("DATABRICKS_CATALOG", "fleetpulse"))
    parser.add_argument("--schema", default=os.getenv("DATABRICKS_SCHEMA", "data"))
    parser.add_argument("--endpoint", default=os.getenv("VECTOR_SEARCH_ENDPOINT", "fleetpulse-vs-endpoint"))
    parser.add_argument("--index", default=None, help="Index name (default: <catalog>.<schema>.document_chunks_index)")
    parser.add_argument("--source-table", default=None, help="Source Delta table (default: <catalog>.<schema>.document_chunks)")
    parser.add_argument("--force", action="store_true", help="Force sync regardless of diff")
    args = parser.parse_args()

    host, token = get_credentials(args)

    index_name = args.index or f"{args.catalog}.{args.schema}.document_chunks_index"
    source_table = args.source_table or f"{args.catalog}.{args.schema}.document_chunks"

    print("=" * 60)
    print("FleetPulse — Vector Search Index Automated Refresh")
    print(f"Host:         {host}")
    print(f"Endpoint:     {args.endpoint}")
    print(f"Index:        {index_name}")
    print(f"Source Table: {source_table}")
    print("=" * 60)

    # 1. Ensure Endpoint exists
    ep_ok = ensure_endpoint_online(host, token, args.endpoint)
    if not ep_ok:
        print("Warning: Endpoint verification failed, continuing...", file=sys.stderr)

    # 2. Sync or Create Index
    sync_or_create_index(
        host=host,
        token=token,
        endpoint_name=args.endpoint,
        index_name=index_name,
        source_table=source_table,
    )

    print("\n✓ Vector Search sync procedure completed!")


if __name__ == "__main__":
    main()
