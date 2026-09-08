# Architecture

## Principle: structured truth, rendered everywhere

AgentCom does not author separate HTML pages, JSON files, and LLM documents. Structured records under `src/data/` are the source of truth.

```text
src/data/*.json
      │
      ├── Human HTML: / and /r/:slug
      ├── Markdown: /r/:slug.md
      ├── JSON: /r/:slug.json + /api/v1/*
      ├── Bulk: /api/v1/export.ndjson
      ├── Graph: /api/v1/graph
      ├── LLM: /llms.txt + /llms-full.txt + /agents.md
      └── MCP: resources + tools + prompts
```

## Runtime

- Node.js 22 built-ins only.
- `server.mjs` owns HTTP routes and static serving.
- `src/lib/data.mjs` loads canonical JSON records.
- `src/lib/search.mjs` provides deterministic local search.
- `src/lib/format.mjs` renders a record as Markdown/HTML.
- `src/lib/mcp.mjs` is transport-independent MCP domain logic.
- `src/lib/audit.mjs` performs public merchant-readiness checks.

## Why no database in the MVP?

The first product is a curated, Git-versioned canonical corpus. That makes review, provenance, diffs, forks, and static exports easy. Introduce Postgres/SQLite only when submissions, user accounts, high-frequency freshness checks, or event history require it.

## Production evolution

1. Keep canonical editorial records in Git.
2. Add a source-monitor worker that watches primary URLs and GitHub releases for material changes.
3. Add append-only source snapshots/hashes for provenance.
4. Add a review queue before machine-generated updates touch canonical records.
5. Add vector/full-text indexing when the corpus becomes too large for in-memory search.
6. Replace the minimal MCP transport adapter with the official SDK while keeping the same `search/get/audit` domain functions.
7. Add signed data releases and public changelogs.
