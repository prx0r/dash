# Spec: scoring v2 (readiness + opportunity, versioned formulas)

Formulas are versioned (`scoring v2.0`, this doc). Scores are NULL unless
computed by these formulas from stored inputs (Protocol Rule 4).

## Readiness v2.0 (coordination only, ceiling 90)

```
readiness = clamp(100 - 15                        # physical fulfillment human
                  - 5 × compliance_count          # regulatory drag
                  - 5 × has_marketplace           # platform dependence
                  + 5 × has_owned_demand,         # direct/repeat/referral
                  0, 90)
```

Inputs: teardown `compliance_spine` length, acquisition owners.
Mirrors `kernel/analysis.readiness_score` 1:1 (Python is the reference
implementation; SQL below must match it exactly).

```sql
-- v_readiness (formula v2.0)
WITH t AS (
  SELECT JSON_VALUE(properties_json,'$.template_id') AS tid, node_id
  FROM `drop.graph_nodes` WHERE node_type = 'template'
)
SELECT tid,
  LEAST(90, GREATEST(0, 100 - 15 - 5*comp.n - 5*mk.has_mkt + 5*od.has_owned)) AS readiness
FROM t ...
```

## Opportunity v2.0 (vacancy weight × pain density)

```
opportunity = vacancy_weight(SIC sections mapped to template)
              × (1 + 0.1 × (pains + margin_leaks))
```

Inputs: ONS jobs snapshot (`SIC_*` observations, `metric_name='ons.jobs_thousands'`),
teardown counts. Mirrors `kernel/analysis.opportunity_ranking` 1:1.
Current top (Aug-2026 snapshot): care + GP (Q), then retail-sector cluster.

## Backtest plan (before trusting v3)

- Hold out one quarter of ONS data; check ranking stability (Spearman ≥ 0.8).
- Spot-check top-3 vs human judgment per vertical; log disagreements as
  PROPOSED weakpoints (feeds §weakpoint-mining, closes the loop).
- Any formula change → version bump + recompute history note (never rewrite
  old scores; append new `metric_name='opportunity.v3'`).
