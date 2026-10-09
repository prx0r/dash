# CAMP-DROPSHIP-GB — Ugly-commerce compatibility compiler (AgentUgly)

Status: DISTILLED | Template: tpl-dropship-gb | Teardown: td-dropship-gb | Pattern: catalog-led

## 1. Market overview
- Drop thesis (verified in-repo): own the compatibility + supersession + local-supply subgraph for installed-base niches too small/local/ugly for big platforms. Refined: find systems with millions of installed units where failures reduce to "identify this weird replaceable object correctly."
- 36 drop campaigns catalogue the niches (heat-pump parts, ventilation, marine, cabin, EV accessories, fire-alarm 75 SKUs...). Equation: installed_base × failure_events × CUSTOMER_PURCHASABLE_SHARE × info_gap × contribution.
- Deloitte 2026: 9 in 10 execs expect AI over search — AI-readable PDPs are visibility itself.

## 2. Acquisition
- Google Shopping/Search exact-model intent (brand + model + delar/erstatning pattern); free listings day one; marketplaces as overflow (no customer ownership).

## 3. Offer catalog
- Per-niche SKU sets (75-SKU launch pattern from drop campaigns); fitment matrices; successors/adapters; Q&A per common failure.

## 4. Unit economics
- 25-35% gross margins (drop campaign band); break-even 15-20 orders/mo; probe budgets with kill thresholds (unbounded testing is the fastest way to lose money).

## 5. Supply/operations strategy
- OEM direct → local distributors → specialist retailers; net pricing + direct-ship verification; multi-supplier fallback (single-supplier fragility kills); UKCA/category compliance per SKU.

## 6. Distribution strategy
- One compatibility graph compiled to every surface: human PDP, Google/AI Mode, Shopify catalog, agent commerce (voiceagent resolver runtime).

## 7. Listing structure
- Merchant Center feed (verified SKUs only); brand + MPN + compatibility details + related parts.

## 8. Landing/conversion structure
- Hero (image + compatibility statement + price/availability) → identification (photos/measurements) → compat table → FAQ → buy. Resolver path for uncertain buyers.

## 9. Success metrics + kill rules
- 75 SKUs live week 1; first paid order week 4; 15-20 orders/mo month 3; wrong-part rate, return rate, resolution success (tier-3 fitness).
- Kill rules per drop state machine: failed gates REJECT; UNKNOWN blocks; reroute (services/D2C/benchmark) preserves evidence.

## 10. Next steps
- M: pick first niche from opportunity ranking (heat-pump filters/ventilation lead on evidence); compile 75-SKU feed; resolver YAML.
- H: supplier contact sequence (OEM → distributors → pricing/direct-ship), store launch sign-off.

## Evidence bindings
- Compatibility thesis + gates + scoring + kill conditions → drop THESIS.md / THESIS_REFINED.md (in-repo).
- 12-gate rubric + state machine → drop rubric/campaign_gate.py, CAMPAIGN_STATE_MACHINE.md.
- AI>search → Deloitte Retail Trends 2026.

## 12-gate states (per-niche at compile time; heat-pump-filters exemplar)
G1 PASS (installed base evidenced) | G2 PASS (failure triggers) | G3 PASS (model/generation complexity) | G4 UNKNOWN (buyer self-select rate — needs probe) | G5 UNKNOWN (local supply mapping per niche) | G6 UNKNOWN (ownership gap per niche) | G7 UNKNOWN (reseller authorisation) | G8 UNKNOWN (CPC/margin with real numbers) | G9 UNKNOWN (demand validation) | G10 UNKNOWN (returns burden) | G11 PASS (agent feed eligible) | G12 UNKNOWN (retrieval whitespace)
Verdict: BLOCKED (probe-gated UNKNOWNs — this is the correct state pre-launch; probes resolve them)
