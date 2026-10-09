# Spec: stack tracking (pricing + usage signals per TOOL_)

Every `TOOL_*` node gets a quarterly price/usage heartbeat. Same pattern as
domain price-drift (>10% aborts): **>10% price move or plan restructure
emits an alert row** for human review.

## Pricing capture (quarterly, M-task)

- Source: vendor pricing pages (public, no login). Record:
  `price.monthly_gbp` | `price.per_user_gbp` | `price.transaction_pct` |
  `price.notes` (add-on traps, lock-ins, e.g. BigChange 36-mo, Vagaro add-ons).
- Metric rows on `TOOL_*`: `metric_name='price.monthly_gbp'`,
  `evidence_type='stack-research'`, `verification=VERIFIED` (primary source).
- Drift rule: |new-old|/old > 0.10 → `metric_name='price.drift_alert'`,
  value = ratio. Review queue, not auto-action.

## Usage signals (quarterly, M-task, confidence ≤ 0.6)

- GitHub stars/forks/commit cadence (cal.diy, Medusa, ONS MCPs) — OSS health.
- Review counts + scores (Capterra/G2/Trustpilot, manual read or vendor-claimed
  with `basis` downgraded unless cross-checked).
- Marketplace presence (listing counts where observable, e.g. Booksy city counts).
- All `verification=PROPOSED` until second source. Never feed VERIFIED-only views.

## Verdict review (annual, H-task input)

`replace|integrate|import-from` per tool is revisited yearly against tracked
data: price drift, feature overlap with kernel, vendor stability (acquisitions:
IRIS→Senta, Access→Guestline, DoorDash→Deliveroo — ownership changes terms).
Agent drafts the verdict-change proposal; human approves.
