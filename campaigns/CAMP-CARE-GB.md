# CAMP-CARE-GB — Domiciliary care agency OS

Status: DISTILLED | Template: tpl-care-gb | Teardown: td-care-gb | Pattern: rota-led

## 1. Market overview
- Adult social care demand +281k new + 404k replacement = **685k workers to 2035** (Skills England 2026). Care workers +199k — single biggest occupation demand in any sector.
- Self-employment in health/social work +51k in one quarter (ONS Aug 2026) — micro-agency formation is already happening.
- 40% decline in youth apprenticeship starts over the decade — recruitment pipeline broken, retention is the game.

## 2. Acquisition
- Council commissioning blocks (repeat, retender risk — win on outcomes evidence).
- Private-pay families (direct, highest margin, review-sensitive).
- Hospital discharge teams (reablement pipeline).

## 3. Offer catalog
- Domiciliary visits (30/45/60-min bands, TBD: local rate card).
- Live-in care placements (TBD: weekly rate).
- Reablement packages for discharge teams (outcome-priced where commissioners allow).

## 4. Unit economics
- Revenue per visit-hour minus carer pay, travel, insurance, training amortisation.
- Council rates squeezed; private rates carry margin. Track separately from day one (funeral-disbursement discipline applied to funding streams).
- Carer turnover is the hidden P&L line: churn + agency cover at premium.

## 5. Supply/operations strategy
- Rota built for continuity (familiar faces), not just coverage.
- DBS/Right-to-Work/training hard gates on rostering — uncertified = unassigned, automatic.
- MAR-gap same-day escalation; safeguarding route with policy-time SLAs.

## 6. Distribution strategy
- Commissioners: evidence packs (visit Volumes, outcomes, CQC-ready).
- Private: Google + local reputation + discharge-team relationships.

## 7. Listing structure
- CQC directory profile (ratings are public data), NHS care-pl finder equivalents, own site with live availability.

## 8. Landing/conversion structure
- Assessment-first funnel: needs assessment → care plan → trial visits → package. Family portal from day one.

## 9. Success metrics + kill rules
- Fill rate, continuity %, MAR-gap count (target 0), CQC rating, staff retention.
- Kill: CQC Inadequate on first inspection → pause growth, fix governance.

## 10. Next steps
- M: import users/plans/roster; configure compliance register; set funding split.
- H: CQC registration (provider application), DBS batch, council approved-provider lists.

## Evidence bindings
- 685k/199k demand → Skills England SNA health & adult social care (gov.uk, Jun 2026).
- +51k self-employment → ONS jobs & vacancies Aug 2026.
- Reg 19 fit/proper, RAP duty to refer → SVGA 2006, HSCA Regs 2014 (verified).
- Youth apprenticeships -40% → Skills England annual report 2026.

## 12-gate states
G1 PASS (demand evidenced) | G2 PASS (ageing + discharge flow) | G3 PASS (rota+MAR complexity) | G4 UNKNOWN (buyer selection: family vs council vs hospital — needs mapping) | G5 PASS (carers exist) | G6 PASS (no incumbent owns the OS layer) | G7 PASS (CQC registration path) | G8 UNKNOWN (unit economics need local rate card) | G9 UNKNOWN (validated demand per patch) | G10 PASS (ops heavy but modelable) | G11 PASS (agent-readable rostering) | G12 UNKNOWN (retrieval whitespace unmeasured)
Verdict: BLOCKED (4 UNKNOWNs — all mappable with local data, none fatal)
