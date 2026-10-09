# Spec: evidence ingestion pipeline

Source → fetch → normalize → basis-tag → dedupe → BigQuery. M-task only:
keyless-first; anything needing signup/keys queues as H-task (obtain key),
never auto-registers.

## Stages

1. **Source select** — pick from `blueprints/data-sources/*.json` by template
   relevance. Keyless (`auth:none`) run unattended. `key-free-signup` and up
   require an approved credential in the broker first (gate enforced).
2. **Fetch** — injectable transport (cf. `kernel/evidence/ons.py` pattern:
   `fetch(url)` callable, urllib default, fake in tests). Timeouts 25s,
   User-Agent `agentcom-kernel/0.1`, respect rate limits in catalog notes.
3. **Normalize** — map to one of three shapes only: node (new entity),
   observation (metric + timestamp + unit), edge (typed relation).
   Raw payloads are never stored; normalized rows + source URL are.
4. **Basis-tag** — every row gets `basis` (verified-2026 | govt-data |
   well-established | template-analysis) + `verification` (PROPOSED default
   for AI-handled, VERIFIED only for govt/primary sources or human confirm).
5. **Dedupe** — idempotent on (source_url + metric + timestamp) for
   observations; MERGE on node_id/edge_id for graph writes.
6. **Load** — batch inserts to `drop.graph_nodes/_edges/_observations`
   (§2 of BIGQUERY_GRAPH_PLAN.md). `--dry-run` prints counts first.
7. **Verify** — post-load count queries + one end-to-end read per §7 ritual.

## Failure modes

- Source schema drift → fetch throws, pipeline halts for that source only,
  alert logged, other sources continue.
- Rate limit → exponential backoff, then defer to next run. Never hammer.
- Key-gated source without broker credential → skip with H-task request
  (obtain key), do not attempt signup.
- Unparseable payload → quarantine row to audit log, continue.
