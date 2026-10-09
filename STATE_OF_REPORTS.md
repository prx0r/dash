# State of Reports — Agentcom BigQuery Graph

**Date:** 2026-09-12
**Status:** Operational
**Report ID:** `STATE-OF-REPORTS-001`

---

## 1. Executive summary

Agentcom BigQuery holds the distilled knowledge graph: 24 vertical templates, 24 teardowns, 26 legislation entries, ONS vacancy snapshot, and a live company node — queryable through 6 derived views. Built by kernel loaders from validated JSON; every stat carries basis.

## 2. Table inventory (live counts, 2026-09-12)

| table | type | rows | purpose |
|---|---|---|---|
| graph_nodes | TABLE | ~400 | all entities (drop-native + agentcom namespaces) |
| graph_edges | TABLE | ~470 | all relationships |
| graph_observations | TABLE | ~130 | metrics: leaks, readiness, ONS, prices, getsocials |
| agent_decisions | TABLE | 0 | kernel audit export (table ready, no exports yet) |
| v_verified_nodes | VIEW | - | PROPOSED hidden from decisions |
| v_pain_index | VIEW | - | fix → templates |
| v_opportunity | VIEW | - | vacancy weight × pain density |
| v_readiness | VIEW | - | coordination score, ceiling 90 |
| v_compliance_coverage | VIEW | - | vertical → laws with basis split |
| v_stack_watch | VIEW | - | latest price per TOOL_ |
| products/sources/probes_* | TABLES | mixed | pre-existing drop research data (untouched) |

## 3. Knowledge-graph census (live)

| node_type | count | notes |
|---|---|---|
| stack_tool | 174 | canonical-stack tools across templates |
| pain | 73 | 72 ranked + 1 demo REJECTED (intentional) |
| template | 24 | all verticals |
| vertical | 24 | 1:1 with templates |
| legislation | 24 | incl. LEG-CLEANCHEM backfilled |
| sic_section | 15 | ONS sections |
| pattern | 14 | analysis patterns |
| fix | 6 | shared fixes |
| company | 1 | COMP_AGENTCOM |
| country/ecosystem/product/merchant | 15 | pre-existing drop rows (untouched) |

| edge_type | count | meaning |
|---|---|---|
| USES_STACK | 191 | template uses tool |
| HAS_PAIN | 72 | template has pain |
| FIXED_BY | 72 | pain fixed by shared fix |
| GOVERNED_BY | 59 | template governed by law |
| MAPS_TO | 26 | SIC section maps to template |
| IN_PATTERN | 24 | template in pattern |
| HAS_ECOSYSTEM/HAS_PROBLEMS/SOLD_IN/LOCATED_IN/ORACLE_FOR | 20 | pre-existing drop edges (untouched) |
| SEEDED_FROM/OPERATES_IN | 2 | company links |

## 4. Queryable proof (run live)

```sql
SELECT fix, ARRAY_LENGTH(templates) n FROM drop.v_pain_index ORDER BY n DESC
```
→ 6 fixes with template counts 20/17/12/11/8/4 — matches kernel index exactly

```sql
SELECT template_id, opportunity FROM drop.v_opportunity LIMIT 5
```
→ TPL_CARE_GB 7126.0, TPL_GP_GB 7126.0, TPL_RETAIL_GB 6943.5, …

```sql
SELECT MIN(readiness), MAX(readiness) FROM drop.v_readiness
```
→ min 70.0, max 85.0 (ceiling holds — coordination only)

```sql
SELECT node_id, metric_value FROM drop.graph_observations WHERE metric_name='price.monthly_gbp'
```
→ TOOL_BOOKSY 40.0, TOOL_FRESHA 14.95, TOOL_HALOPSA 69.0 (exact-match rerun)

## 5. Gaps (honest)

| gap | impact | fix |
|---|---|---|
| agent_decisions 0 rows | no live audit trail yet | export on first gated deployment |
| stack prices: 3 tools only | stack watch thin | quarterly heartbeat per spec |
| ONS snapshot static (Aug 2026) | vacancy weights age | quarterly ONS push per spec |
| VACS02 not in ONS API | bulletin-derived, not API-pulled | manual quarterly refresh |
| demo REJECTED row live | none (intentional lifecycle proof) | documented, do not delete blindly |
| MERGE blind to streaming buffer | reseeds <90min duplicate nodes | governance rule 6: space reseeds, dedupe after flush |

## 6. Patterns found (computed, not asserted)

| tier | criterion | members |
|---|---|---|
| Tier 1: structural demand + law | govt demand + criminal-tier compliance | care, GP, HVAC, vet, funeral |
| Tier 2: marketplace-taxed volume | high volume, platform-dependent | restaurant, hotel, barber, reseller, gig-driver |
| Tier 3: relationship-led | referral/repeat dominant, thin data | builder, tutor, medspa, petcare |

## 7. Honest assessment

Real: 24/24/24 templates/teardowns/campaigns validated; BQ mirrors disk exactly; views reproduce kernel math; legislation verified to statute with basis tags; heartbeat live. Not real yet: any business running on any template; agent_decisions empty; stack prices thin; ONS snapshot static. The graph is an asset awaiting its first deployment, exactly as drop's was.

## 8. Next steps

1. Quarterly heartbeat (prices + ONS push). 2. First gated deployment to fill agent_decisions. 3. Deepen teardowns unevenly so opportunity density differentiates. 4. cmail Worker → kernel gate wiring (TS/Python boundary open).

## 9. Sources

kernel/templates (24), kernel/teardowns (24), kernel/compliance (26+26), kernel/evidence (ONS/Nomis live), blueprints/data-sources (25 entries), blueprints/specs (4). Structure distilled from /drop: STATE_OF_BIGQUERY, HCC_V2, campaign verifications, REDTEAM, CAMPAIGN_STATE_MACHINE, LIVE_LEARNING_LOOP.

