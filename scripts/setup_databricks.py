"""
FleetPulse — Databricks Unity Catalog & Schema Setup Script
============================================================
Ensures that:
1. Catalog 'fleetpulse' exists (creates if not present).
2. Schema 'data' exists under 'fleetpulse' (creates if not present).
3. Schema 'rag' exists under 'fleetpulse' for vector search & document chunks.

Supports both Databricks SDK and direct REST API calls using DATABRICKS_HOST and DATABRICKS_TOKEN.

Usage:
    python scripts/setup_databricks.py
    python scripts/setup_databricks.py --catalog fleetpulse --schema data
"""

import argparse
import os
import sys
import httpx


def get_databricks_credentials(args: argparse.Namespace) -> tuple[str, str]:
    """Retrieve Databricks host and token from args or environment variables."""
    host = args.host or os.getenv("DATABRICKS_HOST", "")
    token = args.token or os.getenv("DATABRICKS_TOKEN", "")

    if not host or not token:
        # Check if running in Databricks runtime or if SDK can auto-authenticate
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient()
            host = host or (w.config.host if hasattr(w.config, "host") else "")
            token = token or (w.config.token if hasattr(w.config, "token") else "")
        except Exception:
            pass

    if not host or not token:
        print("ERROR: DATABRICKS_HOST and DATABRICKS_TOKEN must be set.", file=sys.stderr)
        print("Set them in environment variables or pass --host and --token flags.", file=sys.stderr)
        sys.exit(1)

    # Normalize host URL
    host = host.rstrip("/")
    if not host.startswith("http://") and not host.startswith("https://"):
        host = f"https://{host}"

    return host, token


def ensure_catalog_exists(host: str, token: str, catalog_name: str) -> bool:
    """Check if Unity Catalog exists, create it if not."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{host}/api/2.1/unity-catalog/catalogs/{catalog_name}"

    print(f"Checking Unity Catalog '{catalog_name}'...")
    try:
        resp = httpx.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            print(f"  ✓ Catalog '{catalog_name}' already exists.")
            return True
        elif resp.status_code == 404:
            print(f"  Catalog '{catalog_name}' does not exist. Creating...")
            create_url = f"{host}/api/2.1/unity-catalog/catalogs"
            payload = {
                "name": catalog_name,
                "comment": "FleetPulse Enterprise Mobile Device Management Catalog",
            }
            create_resp = httpx.post(create_url, headers=headers, json=payload, timeout=30)
            if create_resp.status_code in (200, 201):
                print(f"  ✓ Catalog '{catalog_name}' created successfully.")
                return True
            else:
                print(f"  FAILED to create catalog: {create_resp.status_code} {create_resp.text}", file=sys.stderr)
                return False
        else:
            print(f"  Unexpected status checking catalog: {resp.status_code} {resp.text}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"  Error checking/creating catalog '{catalog_name}': {e}", file=sys.stderr)
        return False


def ensure_schema_exists(host: str, token: str, catalog_name: str, schema_name: str) -> bool:
    """Check if Schema exists within catalog, create it if not."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    full_name = f"{catalog_name}.{schema_name}"
    url = f"{host}/api/2.1/unity-catalog/schemas/{full_name}"

    print(f"Checking Schema '{full_name}'...")
    try:
        resp = httpx.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            print(f"  ✓ Schema '{full_name}' already exists.")
            return True
        elif resp.status_code == 404:
            print(f"  Schema '{full_name}' does not exist. Creating...")
            create_url = f"{host}/api/2.1/unity-catalog/schemas"
            payload = {
                "name": schema_name,
                "catalog_name": catalog_name,
                "comment": f"FleetPulse tables and artifacts for '{schema_name}'",
            }
            create_resp = httpx.post(create_url, headers=headers, json=payload, timeout=30)
            if create_resp.status_code in (200, 201):
                print(f"  ✓ Schema '{full_name}' created successfully.")
                return True
            else:
                print(f"  FAILED to create schema: {create_resp.status_code} {create_resp.text}", file=sys.stderr)
                return False
        else:
            print(f"  Unexpected status checking schema: {resp.status_code} {resp.text}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"  Error checking/creating schema '{full_name}': {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Ensure Unity Catalog and Schema exist for FleetPulse.")
    parser.add_argument("--host", default=None, help="Databricks workspace host URL")
    parser.add_argument("--token", default=None, help="Databricks personal access token")
    parser.add_argument("--catalog", default=os.getenv("DATABRICKS_CATALOG", "fleetpulse"), help="Catalog name (default: fleetpulse)")
    parser.add_argument("--schema", default=os.getenv("DATABRICKS_SCHEMA", "data"), help="Primary schema name (default: data)")
    args = parser.parse_args()

    host, token = get_databricks_credentials(args)

    print("=" * 60)
    print(f"FleetPulse Unity Catalog & Schema Setup")
    print(f"Host:    {host}")
    print(f"Catalog: {args.catalog}")
    print(f"Schema:  {args.schema}")
    print("=" * 60)

    # 1. Ensure catalog exists
    cat_ok = ensure_catalog_exists(host, token, args.catalog)
    if not cat_ok:
        sys.exit(1)

    # 2. Ensure primary schema exists (e.g. data)
    schema_ok = ensure_schema_exists(host, token, args.catalog, args.schema)
    if not schema_ok:
        sys.exit(1)

    # 3. Ensure rag schema exists if different from primary schema
    if args.schema != "rag":
        ensure_schema_exists(host, token, args.catalog, "rag")

    print("\n✓ Unity Catalog setup complete!")


if __name__ == "__main__":
    main()
