# Source policy

AgentCom aims to be canonical by being conservative.

## Source hierarchy

1. Protocol specification / official repository.
2. Platform developer documentation or merchant help center.
3. First-party product announcement.
4. Maintainer-authored implementation sample.
5. High-quality secondary explanation, only when the primary source does not answer the practical question.

## Record requirements

Every canonical item must have:

- stable `slug`
- concise factual `summary`
- at least one source
- source `authority`
- source `last_verified` (`YYYY-MM-DD`)
- tags that map to protocols/platforms where useful

## Mutable claims

Program availability, regions, APIs, eligibility, pricing, limits, versions, and rollout status are mutable. Treat them as stale unless periodically re-verified.

Do not turn an announced roadmap into a current capability. Distinguish:

- `active`
- `beta`
- `early-access`
- `announced`
- `deprecated`

## Agent-generated changes

Agents can propose edits, but canonical publication should require deterministic validation plus human/editorial approval until source-change detection and confidence scoring are proven reliable.

## Machine-readable honesty

`/.well-known/agentcom.json` is an AgentCom discovery convenience. `/.well-known/mcp.json` is explicitly labeled as an AgentCom descriptor rather than asserted as a universal standard. Protocol-specific well-known paths are only described when they are documented by that protocol/platform.
