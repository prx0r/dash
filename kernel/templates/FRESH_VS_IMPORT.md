# FRESH-BUILD vs IMPORT — the decision flow

Asked once per company, right after getsocials: "what is the business?"

## The two paths

```
                    ┌── FRESH ── empty graph, template seeds nodes
                    │             (new shop, new niche, new practice)
WHAT IS
THE BUSINESS? ──────┤
                    └── IMPORT ── existing data lands in graph first
                                  (clients, catalog, tickets, stock)
```

## Decision tree

```
1. Does the business already run on something?
   ├── NO → FRESH
   │         Template seeds empty nodes (services, price book, policies).
   │         First real data arrives through workflows.
   │
   └── YES → what holds the data?
               ├── booking tool (Booksy/Fresha/Square/Vagaro)
               │     → IMPORT clients + services + prices + packages
               ├── job tool (Jobber/Tradify/Garage Hive/TechMan)
               │     → IMPORT customers + vehicles/assets + history + stock
               ├── PSA/RMM/docs (CW/Halo/Ninja/ITGlue)
               │     → IMPORT clients + sites + assets + tickets + runbooks
               │       (passwords become credential refs, never values)
               └── storefront (Shopify + DSers/AutoDS)
                     → IMPORT catalog + suppliers + orders
```

## Import rules

1. **Import is one-way, into the graph.** The old tool becomes a source, not a peer.
2. **Every imported row keeps provenance.** Source tool + export date on the node.
3. **Verdicts per tool** (from each template's `canonical_stack`):
   - `import-from` — one-time migration, then the old tool can go
   - `integrate` — keep it, connect the API (marketplace discovery, DVLA, RMM, POS, Stripe)
   - `replace` — agentic version supersedes it (rare on day one; earned over time)
4. **Never silently drop a function.** If the old tool did it and the graph can't yet, that's a gap — logged, not ignored. See AGENTIC_MAPPING.md.
5. **Discovery channels stay until measured.** Booksy Boost, Fresha marketplace, Google presence — keep, track CAC per channel in the graph, then decide with data.

## What "done" looks like per path

```
FRESH:  template nodes exist, all empty → first booking/job/order/ticket fills them
IMPORT: template nodes exist, pre-filled → agent verifies a sample with the human → workflows take over
```

Both converge: after import/fresh-seed, the business runs on the graph, and the
old tools are either integrated feeds or gone.
