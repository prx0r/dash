# BigQuery Graph Plan — Agentcom knowledge graph on `drop`

Project: `project-ff2366d2-8fda-4fcb-9ba` (from `agent-vault … GOOGLE_CLOUD_PROJECT --vault oracle`)
Auth: OAuth refresh-token flow per AGENTS.md Rule 0 (no dedicated BQ key exists;
`GOOGLE_REFRESH_TOKEN` + `GOOGLE_CLIENT_ID/SECRET` is the credential path).

## 0. What exists today (verified live 2026-09-12)

One dataset: `drop`. Populated tables: `graph_nodes` (27), `graph_edges` (20),
`graph_observations` (7), `products` (75), `sources` (52), `information_sources` (9),
`operator_events` (21), `opportunities` (8), `probe_*` (12 rows total), `x_accounts` (12).
Everything else (`fact_*`, `keyword_data`, `ml_predictions`, …) exists at 0 rows.

Live conventions (do not break):
- `graph_nodes(node_id, node_type, properties_json STRING, created_at, updated_at, confidence, source)`
- IDs namespaced: `COUNTRY_NO`, `ECO_FI_HEAT_PUMP`, `PROD_*`, `MERCHANT_*`, `PROB_*`
- `graph_edges(edge_id, source_node, target_node, edge_type, weight, created_at, source)`
- Edge types UPPER_SNAKE: `HAS_ECOSYSTEM`, `SOLD_IN`, `LOCATED_IN`, `ORACLE_FOR`, `HAS_PROBLEMS`
- `properties_json` is STRING — loaders must `json.dumps`, never raw dicts
- `graph_observations(node_id, observed_at, metric_name, metric_value, evidence_type, source)`
- The 4-dataset design (`drop_evidence/drop_graph/drop_campaign/drop_live` in
  `sql/BIGQUERY_DDL.sql`) was **never deployed**. Do not create it. One dataset: `drop`.

## 1. Design decision: reuse, don't fork

All Agentcom content goes into the SAME three tables. New `node_type` /
`edge_type` values + namespaced IDs. One graph, one query surface, zero migration.
Exactly ONE new table (kernel runtime audit, §5) — everything else fits.

### 1.1 Node ID namespaces (new, reserved)

| Prefix | Example | Source |
|---|---|---|
| `TPL_` | `TPL_BARBER_GB` | `kernel/templates/tpl-*.json` → `template_id` upper, `-`→`_` |
| `VERT_` | `VERT_BARBER` | distinct `vertical` values |
| `PAT_` | `PAT_BOOKING_LED` | `VERTICAL_PATTERN` map in `teardowns/graph.py` |
| `PAIN_` | `PAIN_BARBER_01` | teardown `pain_ranking` rank per template |
| `FIX_` | `FIX_NOSHOW` | `teardowns/fixes.json` ids verbatim |
| `LAW_` | `LAW_FGAS` | `compliance/legislation.json` ids verbatim |
| `TOOL_` | `TOOL_BOOKSY` | template `canonical_stack[].tool`, slugified |
| `COMP_` | `COMP_DBE371FA` | kernel `CompanyIdentity` (strip `COMP-`, keep 8+ hex) |

### 1.2 Edge vocabulary (new, append-only)

`HAS_TEARDOWN` (TPL→teardown doc node? No — teardown lives in PAIN nodes; use
`TPL→HAS_PAIN→PAIN`), `HAS_PAIN`, `FIXED_BY` (PAIN→FIX), `IN_PATTERN`
(template→PAT), `USES_STACK` (TPL→TOOL), `GOVERNED_BY` (TPL→LAW),
`EVIDENCED_BY` (TPL→graph_observations metric), `SEEDED_FROM` (COMP→TPL),
`RANKED` never an edge — ranks are observation values.

### 1.3 `properties_json` contracts (per node_type)

```json
// TPL_*  {"template_id": "...", "vertical": "...", "countries": ["GB"],
//         "entry_question": "...", "import_sources": [...], "workflows": [...]  (names only)}
// PAIN_* {"pain": "...", "rank": 1, "why": "...", "fix_id": "FIX-NOSHOW"}
// FIX_*  {"name": "...", "description": "..."}   // from fixes.json
// LAW_*  {"law": "...", "citation": "...", "basis": "verified-2026|well-established",
//         "requires": [...], "source_url": "..."}   // basis enum mirrors kernel tests
// TOOL_* {"tool": "...", "category": "...", "does": "...",
//         "verdict": "replace|integrate|import-from"}
// COMP_* {"name": "...", "vertical": "...", "country": "...", "status": "..."}
```

### 1.4 Verification convention (no evidence dataset exists)

Every AI-generated claim carries in `properties_json`:
`{"verification": "PROPOSED|VERIFIED|REJECTED", "basis": "verified-2026|govt-data|template-analysis|well-established"}`
Derived views (§6) expose `*_verified` variants filtering `verification=VERIFIED`.
Human promotion = single UPDATE flipping the flag (auditable via `updated_at`).

## 2. Phase 1 — Seed loaders (kernel JSON → BQ, ~500 rows, $0)

`agentcom/kernel/bigquery_loaders/` (new, stdlib + google-cloud-bigquery):
- `seed_templates.py`: 24 `TPL_*` + 24 `VERT_*`(dedup→24 verticals… actually 24 distinct verticals? map: 24 templates, ~24 verticals) + 14 `PAT_*` nodes; `IN_PATTERN`, `USES_STACK` (sum of stack entries ≈ 200), `GOVERNED_BY` edges.
- `seed_teardowns.py`: ~72 `PAIN_*` nodes + `HAS_PAIN`/`FIXED_BY`; 6 `FIX_*` nodes.
- `seed_compliance.py`: 25 `LAW_*` nodes + `GOVERNED_BY` edges (skip NONLAW_* as nodes; record as `properties_json.design_rule` on relevant TPL_ instead).
- `seed_stats.py`: every teardown `margin_leaks[].stat` → `graph_observations`
  (`metric_name='leak:<slug>'`, `metric_value`=NULL when non-numeric — store text in
  `evidence_type`? No: metric_value NULL + full stat text in a `STAT_*` node? Simpler:
  stats WITH numbers → observations; stats text-only → `properties_json` on the leak's parent PAIN node. Rule: numbers flow, prose stays.)
- `seed_ons_snapshot.py`: ONS Aug-2026 jobs table → `graph_observations`
  (`metric_name='ons.jobs_thousands'`, node per SIC section `SIC_Q`… new tiny namespace, 15 nodes) + `template_priority()` output → observations on TPL_ nodes (`metric_name='opportunity.score'`).
- All loaders: `--dry-run` prints row counts; `--execute` inserts; idempotent on
  (`node_id` / `edge_id`) via `MERGE` (nodes) / `INSERT IF NOT EXISTS` check (edges have no PK — dedupe by `edge_id` in loader query first).
- Verify after each: `SELECT node_type, COUNT(*) FROM drop.graph_nodes GROUP BY 1`
  and edge-type counts; expect nodes ≈ 27+~350, edges ≈ 20+~400.

## 3. Phase 2 — Metrics pipelines (time-series, append-only)

- Stack pricing: re-run template stack research quarterly → `graph_observations`
  on `TOOL_*` (`metric_name='price.registration_gbp'|'price.monthly_gbp'`, `evidence_type='stack-research'`). Reuses pattern of `fact_series_price` (0 rows, compatible shape) — but write to `graph_observations` to keep one read path; leave `fact_series_*` for probe series.
- ONS vacancies: `kernel/evidence/ons.py` already fetches; add `push_vacancies(snapshot_dict)` writing `ons.jobs_thousands` per `SIC_*` quarterly. Nomis claimant count → `metric_name='nomis.claimant_uk'`.
- Adoption/readiness/opportunity: **never store scores except via versioned formula** (Protocol Rule 4). Store inputs as observations; compute in views (§6). The kernel `readiness_score`/`opportunity_ranking` functions are the versioned formulas — port logic 1:1 to SQL.
- Usage metrics for stacks (where measurable without violating ToS: pricing pages, review counts, GitHub stars for OSS like cal.diy/Medusa) → `graph_observations` with `evidence_type='public-signal'`, `confidence` ≤ 0.6, `verification=PROPOSED` until second source.

## 4. Phase 3 — Weakpoint loop (AI proposes, evidence disposes)

- Any agent may INSERT `PAIN_*`-candidate nodes with `verification=PROPOSED` + `basis` + source URL in `properties_json`. Never `VERIFIED` on insert.
- Promotion rule: second independent source OR human confirm → `UPDATE … SET properties_json=JSON_SET(…, '$.verification','"VERIFIED"')`.
- `*_verified` views hide PROPOSED from decision queries; research queries can include them explicitly. This is the AISec-shaped contribution loop without a new table.

## 5. Phase 4 — Kernel runtime writes (one new table)

Companies (`COMP_*` nodes) + getsocials progress (observations: `metric_name='getsocials.progress_pct'`, subroutine statuses as JSON in a `COMP_*` properties update — nodes are mutable via `updated_at`, history lives in observations).

```sql
CREATE TABLE IF NOT EXISTS `drop.agent_decisions` (
  decision_id STRING NOT NULL,          -- AUD-XXXXXXXX from kernel AuditLog
  decided_at TIMESTAMP NOT NULL,
  actor STRING NOT NULL,                -- agent:* | human:*
  company_id STRING,                    -- COMP_* or NULL
  task_id STRING,                       -- A-XXXXXXXX or NULL
  action STRING NOT NULL,
  resource STRING NOT NULL,
  decision STRING NOT NULL,             -- ALLOW | DENY | HUMAN
  reason STRING,
  approval_id STRING,                   -- APR-* or NULL
  side_effect INT64                      -- 0..5 kernel SideEffect
)
PARTITION BY DATE(decided_at)
CLUSTER BY company_id, decision, action;
```

Sync rule (D1 hot, BQ truth): CompanyGraph D1 stays the operational store;
a nightly (later hourly) exporter appends decisions + node snapshots to BQ.
BQ never blocks the gate (fail-closed locally if BQ unavailable).

## 6. Phase 5 — Derived views (SQL mirrors of kernel/analysis)

```sql
-- verified-only graph slices
CREATE OR REPLACE VIEW `drop.v_verified_nodes` AS
SELECT * FROM `drop.graph_nodes`
WHERE JSON_VALUE(properties_json, '$.verification') IS NULL
   OR JSON_VALUE(properties_json, '$.verification') = 'VERIFIED';
-- pain index: fix → templates (mirrors TeardownRegistry.pain_index)
CREATE OR REPLACE VIEW `drop.v_pain_index` AS
SELECT e2.target_node AS fix, ARRAY_AGG(DISTINCT e1.source_node) AS templates
FROM `drop.graph_edges` e1 JOIN `drop.graph_edges` e2
  ON e1.target_node = e2.source_node
WHERE e1.edge_type='HAS_PAIN' AND e2.edge_type='FIXED_BY' GROUP BY fix;
-- opportunity ranking (mirrors opportunity_ranking(); formula version pinned in view comment)
-- readiness (mirrors readiness_score rubric)
-- compliance coverage (vertical → laws, with basis split verified vs well-established)
-- stack watch (latest price per TOOL_*, quarter-over-quarter change)
```

## 7. Phase 6 — Schedule, cost, governance

- Loaders run on demand (seed = once); metrics pipelines quarterly (cron/Cloud Scheduler + tiny VM or local run — data volumes are KBs, free tier).
- Cost guard: seed ≈ 800 rows; quarterly deltas ≈ dozens of rows. Negligible.
- Governance: `source` column on every row = loader name + git sha; `confidence` per Protocol Rule 2 (0-1 or NULL); scores NULL unless formulaic (Rule 4); every observation needs provenance (Rule 3).
- Verification ritual per phase (Rule 0): run the §2 count queries + one end-to-end read (`v_pain_index` returns 6 fixes; opportunity view ranks `TPL_CARE_GB`/`TPL_GP_GB` top on current snapshot) before declaring done.
- Country packs (`data/raw/geodrop_country_*`, not on this box): when present, land as `COUNTRY_*` properties updates + `ECO_*` nodes per existing convention — no new namespaces needed; UK template work attaches via `SOLD_IN`/`HAS_ECOSYSTEM`-style edges (`OPERATES_IN` for COMP_→COUNTRY_).
