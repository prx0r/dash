# DISTILLPROTOCOL — BigQuery sprawl → campaigns/theses, as runnable ops

Lives in `kernel/distill/` (agentcom side, never in `/root/drop`).
Six ops, each a JSON definition in `ops/` + pure executor in `executors.py`,
chained by `run_chain()` with per-op receipts.

## Recon: what /drop actually did (2026-09-07/08)

**Reports state.** `docs/STATE_OF_BIGQUERY.md` claims 1,477 rows: country packs
(NO/FI/GB/DE/DK + US stub, 1,073 rows), 22 case studies, 25 hypotheses,
27 product markets, 18 GoldProbe reports (B02–B19), 10 mechanisms, 5 experiments.
Live graph today is smaller and differently shaped (27 nodes/20 edges,
country/ecosystem/product/merchant/supplier/problem) than the doc's 47/65
(mechanism/probe-flavored) — generations differ; treat the doc as history,
the tables as truth.

**Theses chain.** `THESIS.md` (core: compatibility compiler, 8 hard gates,
ownability /130, kill conditions) → `THESIS_REFINED.md` (adds
CUSTOMER_PURCHASABLE_SHARE, self-service ratio, GEODROP_AGENT_SCORE,
downgrades whole-unit heat pumps/EV/PCB claims) → `aithesis.md`.
Pattern: each refinement ADDS correction terms and NARROWS overclaims.
The protocol's snowball op encodes exactly this.

**Snowball mechanics.** Probes → mechanisms (10, with cross-country transfer
status: Replicated/Supported) → opportunity tiers (Tier 1 = multi-source
agree) → campaigns. Loops: `LIVE_LEARNING_LOOP.md` (outcome tiers 0–3,
counterfactuals, promotion-across-niches priors for CGE),
`ACTIVE_LEARNING_EVI.md`, rubric A/B/C + secret suite + CG/CGE eval.

**Campaign end-state.** 36 files in `campaigns/active/`, all following one
10-section shell (market/competitors/catalog-75-SKUs/pricing/suppliers/ads/
feed/landing/metrics/next-steps). Most bodies are placeholders
("See original campaign file", "See market data") — compiled shells awaiting
evidence fill. State machine: DISCOVERED → … → LAUNCHABLE → LIVE_PROBE →
PROVEN/MUTATE/KILLED (reroute is success, never skip stages).

## The six ops

| # | Op | Formalizes | Side effect |
|---|----|-----------|-------------|
| 1 | distill-sprawl-scan | STATE_OF_BIGQUERY §1 (inventory + gaps) | 0 PURE |
| 2 | distill-cluster | opportunity tiering (multi-source agree) | 0 PURE |
| 3 | distill-snowball | THESIS→REFINED correction pattern | 1 (append-only) |
| 4 | distill-gate-check | campaign_gate.py + Rubric A + track router | 0 PURE |
| 5 | distill-campaign-compile | campaign.schema.v2.json + 10-section shell | 1 (artifact) |
| 6 | distill-refine | state machine + LIVE_LEARNING_LOOP tiers + priors | 1 (transition) |

## Rules (inherited + new)

- From drop: UNKNOWN never becomes PASS; no provisional passes; reroute
  preserves evidence; killed campaigns preserved with reason; resolution
  (tier 3) is the fitness function; gates dominate revenue.
- From kernel: ops are pure (I/O at boundary); side effects classified 0–5;
  placeholders explicit `TBD:`, never invented; snowball append-only with
  version + prior snapshot; every op cites its drop source in `sources`.

## Run it

```python
from agentcom.kernel.distill import run_chain
run_chain(["distill-sprawl-scan", "distill-cluster", "distill-snowball",
           "distill-gate-check", "distill-campaign-compile", "distill-refine"],
          {"inventory": [...], "candidates": [...], ...})
```

BQ mapping: scan reads table inventory; snowball/compile outputs land as
`PAIN_*`/spec artifacts via `kernel/bigquery` loaders; refine transitions
mirror `drop_campaign` state semantics.
