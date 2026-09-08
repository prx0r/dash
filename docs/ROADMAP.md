# Roadmap

## MVP — included

- Canonical structured corpus.
- Source provenance + verification dates.
- Human resource hub.
- JSON/Markdown alternates.
- Search API.
- Bulk NDJSON export.
- Knowledge graph.
- `llms.txt`, `llms-full.txt`, `agents.md`.
- HTTP + stdio MCP.
- Store agent-readiness auditor.
- Docker + tests + validation.

## Next: usage flywheel

1. **Platform-specific checkers** — Shopify UCP/MCP conformance, OpenAI feed linting, Merchant Center feed diagnostics, TikTok/Meta catalog checks.
2. **Live compatibility matrix** — protocol × platform × capability × region × status × version.
3. **Source-change radar** — watch official docs/repos, diff meaningful changes, create review PRs.
4. **AgentCom CLI** — `npx agentcom audit https://store` and `agentcom explain ucp`.
5. **Public MCP registry subset** — verified commerce MCP endpoints only.
6. **Merchant submissions** — submit implementation, endpoint, feed/tool; verify automatically.
7. **Agent-readiness badge** — reproducible score backed by public evidence, not pay-to-play.
8. **Country playbooks** — region-specific merchant/platform availability without mixing global assumptions.
9. **Benchmark** — repeatable tasks testing whether leading agents can discover, compare, cart, and hand off checkout correctly.
10. **Signed releases** — dated JSON snapshots and changelog for agents that need reproducibility.

## Avoid

- Generic AI-news content farm.
- Unverified protocol rumors.
- Pretending `llms.txt` alone creates ranking/discovery.
- Monetizing basic docs before the resource becomes genuinely useful.
- Creating new protocol names where an active standard already solves the problem.
