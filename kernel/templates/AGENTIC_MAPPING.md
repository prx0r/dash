# AGENTIC MAPPING — retain functionality, go agentic

The rule: **for each template, google what the most common stack is, model
what data structures are needed so we can retain functionality, but allow it
to become agentic.**

## The pattern (applied to every canonical function)

```
1. NAME the canonical function
   e.g. "SMS reminders", "DVI with photos", "SLA escalation"

2. MODEL the data it needs
   Which nodes + edges + fields? Write them into the template's graph_shape.
   If the data doesn't exist as nodes, the function can't survive migration.

3. MAP it to an agentic equivalent
   Same outcome, agent-executed inside kernel policy. Record in agentic_mapping
   with retained=true. If retained=false, say why and what replaces the outcome.

4. CLASSIFY the side effect (0-5)
   PURE → autonomous. REVERSIBLE → autonomous in task. EXTERNAL → scoped/H-task.
   FINANCIAL / PRIVILEGED / IRREVERSIBLE → human-issued capability. Always.

5. KEEP the irreplaceable
   DVLA, RMM agents, marketplace discovery, Stripe/POS rails, government APIs —
   verdict=integrate. The agent orchestrates around them, never rebuilds them.
```

## Worked example (garage DVI)

```
canonical:  technician takes photos, writes up findings in Tekmetric
data:       inspection{job_card_id, photos, advisories, sent_at} → finds → job_line
agentic:    tech captures photos; agent assembles customer-facing report instantly
side effect: EXTERNAL (sends report to customer) → scoped, approval per policy
kept:       the photos, the advisories, the customer approval gate on estimates
gained:     report goes out in minutes not hours; approval is kernel-enforced
```

## Anti-patterns

- **Dropping discovery.** Killing Booksy/Fresha listings on day one because "we have our own booking now". Discovery is revenue. Measure CAC first.
- **Rebuilding infrastructure.** Writing our own RMM, our own DVLA, our own card rails. Integrate.
- **Silent function loss.** Old tool sent MOT reminders; new graph has no reminder workflow. That's a regression, not a migration. Log the gap.
- **Agent-discretionary money.** Deposits, estimates, refunds, ad budgets always policy-bound. The agent proposes; the kernel enforces.
- **Content-first thinking.** The agent doesn't care about copy or creative. It cares: can I read the calendar, can I send the SMS, can I charge the deposit. Capabilities first, content later.
