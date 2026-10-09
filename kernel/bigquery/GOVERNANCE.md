# Cost & schedule governance — BigQuery graph

## Cost (measured, not estimated)

| Item | Volume | BQ cost |
|------|--------|---------|
| Phase 1 seed | 369 nodes + 416 edges + 37 obs + 26 maps + 72 readiness + 1 company + 5 progress | storage KBs, ~10 query jobs |
| Staging tables | created + dropped per MERGE run | $0 (deleted same run) |
| Views (6) | logical only, no storage | $0 until queried |
| Quarterly deltas | dozens of rows | negligible |
| Free-tier headroom | 1TB queries/mo, 10GB storage | orders of magnitude above usage |

No partitioning changes needed at this volume. Revisit if observations pass 1M rows.

## Schedule

| Cadence | Job | Owner |
|---------|-----|-------|
| On kernel change | re-run seed loaders (idempotent MERGE) | whoever changed kernel |
| Quarterly | stack pricing heartbeat → TOOL_ observations; ONS vacancy push → SIC_ observations | cron or manual run |
| Annual | verdict review per stack-tracking spec (agent drafts, human approves) | human + agent |
| Continuous | weakpoint proposals (PROPOSED) → quarterly review queue | agent proposes, human promotes |

## Rules

1. `--dry-run` counts before every execute (loaders print nodes/edges/obs).
2. Scores computed in views only; formula changes = version bump + new metric name.
3. BQ never blocks the gate: exporter failures retry later, gate runs local.
4. Every row carries `source` = loader + version; every stat carries basis.
5. Staging tables always dropped in `finally` (verified: no `_seed_staging_*` remains).
6. **Reseeds >90 min apart.** MERGE cannot match rows still in the streaming
   buffer, so a reseed inside the window duplicates nodes (found 17 dupes live,
   cleaned via serialization-order DELETE after flush). `insert_edges_new`
   is immune (SELECT sees buffered rows).
