"""BigQuery connection + idempotent execute helpers (the only I/O layer)."""
from __future__ import annotations

import datetime
import subprocess
from typing import Any


def vault_get(key: str, vault: str = "oracle") -> str:
    return subprocess.run(
        ["agent-vault", "vault", "credential", "get", key, "--vault", vault],
        capture_output=True, text=True).stdout.strip()


def connect(project: str | None = None):
    """Real client via vault OAuth flow (AGENTS.md Rule 0). M-task: reads/writes
    our own project only. Never used in unit tests (fake client instead)."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google.cloud import bigquery

    creds = Credentials(
        token=None,
        refresh_token=vault_get("GOOGLE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=vault_get("GOOGLE_CLIENT_ID"),
        client_secret=vault_get("GOOGLE_CLIENT_SECRET"))
    creds.refresh(Request())
    return bigquery.Client(project=project or vault_get("GOOGLE_CLOUD_PROJECT"),
                           credentials=creds)


def merge_nodes(client: Any, dataset: str, rows: list[dict]) -> int:
    """Idempotent upsert on node_id. Returns rows merged (real client) or
    rows staged (fake client records the call)."""
    if not rows:
        return 0
    if hasattr(client, "_fake"):
        client._calls.append(("merge_nodes", dataset, rows))
        return len(rows)
    # Deduplicate by node_id (last writer wins)
    seen = {}
    for r in rows:
        seen[r["node_id"]] = r
    rows = list(seen.values())
    import uuid
    from google.cloud import bigquery
    staging_id = f"_seed_staging_{uuid.uuid4().hex[:8]}"
    staging_ref = f"{client.project}.{dataset}.{staging_id}"
    schema = [
        bigquery.SchemaField("node_id", "STRING"),
        bigquery.SchemaField("node_type", "STRING"),
        bigquery.SchemaField("properties_json", "STRING"),
        bigquery.SchemaField("created_at", "TIMESTAMP"),
        bigquery.SchemaField("updated_at", "TIMESTAMP"),
        bigquery.SchemaField("confidence", "FLOAT64"),
        bigquery.SchemaField("source", "STRING"),
    ]
    table = bigquery.Table(staging_ref, schema=schema)
    table.expires = None
    client.create_table(table)
    try:
        errors = client.insert_rows_json(staging_ref, rows)
        if errors:
            raise RuntimeError(f"staging insert errors: {errors[:3]}")
        client.query(
            f"""MERGE `{client.project}.{dataset}.graph_nodes` T
            USING `{staging_ref}` S
            ON T.node_id = S.node_id
            WHEN MATCHED THEN UPDATE SET properties_json=S.properties_json,
              updated_at=S.updated_at, confidence=S.confidence, source=S.source
            WHEN NOT MATCHED THEN INSERT
              (node_id, node_type, properties_json, created_at, updated_at,
               confidence, source)
            VALUES (S.node_id, S.node_type, S.properties_json, S.created_at,
              S.updated_at, S.confidence, S.source)""").result()
    finally:
        client.delete_table(staging_ref, not_found_ok=True)
    return len(rows)


def insert_edges_new(client: Any, dataset: str, rows: list[dict]) -> int:
    """Insert only edge_ids not already present. Returns rows inserted."""
    if not rows:
        return 0
    if hasattr(client, "_fake"):
        client._calls.append(("insert_edges_new", dataset, rows))
        return len(rows)
    existing = {r.edge_id for r in client.query(
        f"SELECT edge_id FROM `{client.project}.{dataset}.graph_edges`"
        f" WHERE edge_id IN UNNEST(@ids)",
        job_config=_id_params(client, [r["edge_id"] for r in rows])).result()}
    fresh = [r for r in rows if r["edge_id"] not in existing]
    if fresh:
        client.insert_rows_json(f"{client.project}.{dataset}.graph_edges", fresh)
    return len(fresh)


def _id_params(client: Any, ids: list[str]):
    from google.cloud import bigquery
    return bigquery.QueryJobConfig(query_parameters=[
        bigquery.ArrayQueryParameter("ids", "STRING", ids)])


def insert_observations(client: Any, dataset: str, rows: list[dict]) -> int:
    """Append-only. Observations are never updated (event-sourced truth)."""
    if not rows:
        return 0
    if hasattr(client, "_fake"):
        client._calls.append(("insert_observations", dataset, rows))
        return len(rows)
    errors = client.insert_rows_json(
        f"{client.project}.{dataset}.graph_observations", rows)
    if errors:
        raise RuntimeError(f"observation insert errors: {errors[:3]}")
    return len(rows)
