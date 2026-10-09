# Spec: weakpoint mining (AI proposes, evidence disposes)

Weakpoints are margin leaks / compliance gaps / churn vectors discovered
from data, not asserted from vibes. Every proposal starts PROPOSED.

## Proposal schema

```json
{"pain": "...", "template_id": "tpl-...",
 "mechanism": "...", "evidence_refs": ["..."],
 "verification": "PROPOSED", "basis": "template-analysis"}
```

## Promotion rule (any one)

1. Second independent source corroborates (different publisher, same direction).
2. Human confirms from trade experience.
3. Primary data (govt stats, platform fee pages, legislation text) directly states it.

Promotion = flip `verification` to VERIFIED (auditable UPDATE, never rewrite).

## Demotion rule (any one)

1. Contradicted by primary data.
2. Source retracted / superseded (track `supersedes_evidence_id` pattern).
3. Human rejects with reason.
Demotion sets REJECTED + reason; rows are never deleted (Rule 10: preserve
rejected candidates — train on the full funnel).

## Review queue

- `verification=PROPOSED` rows older than 90 days without corroboration →
  surface in quarterly review; keep, kill, or re-research.
- Precision metric: share of PROPOSED promoted within 2 quarters. Target ≥50%.

## Guardrails

- No PROPOSED row may feed a VERIFIED-only decision view (§6 views).
- No invented numbers: unmeasured impact = `annual_impact_note` prose or NULL,
  never a fabricated £ figure (Protocol Rule 1: null if unknown).
