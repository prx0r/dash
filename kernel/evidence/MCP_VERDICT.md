# ONS MCP verdict (probed 2026-09-12 from this box)

| Option | Result | Use when |
|--------|--------|----------|
| Raw ONS beta API (`api.beta.ons.gov.uk/v1`) | ✅ keyless, catalogue + dataset metadata verified live | Kernel evidence feed (this is what `ons.py` uses) |
| Raw Nomis API (`nomisweb.co.uk/api/v01`) | ✅ keyless, NM_1_1 claimant data verified live | Labour-market tables (no ONS equivalent) |
| `brynmrgn/ons-mcp` live service | ❌ 401 — Cloudflare Access org OAuth from here | Self-host the Python FastMCP yourself, or use from an MCP client inside their Access org |
| `dwain-barnes/uk-ons-mcp-server` (npx) | ⚠️ not tried — needs node process for what urllib does | MCP-native clients (Claude Desktop, Cursor) that want ONS tools |
| `pipeworx-io/mcp-ons-uk` gateway | ❌ 404 on documented path | Re-check docs before use |

Rule: kernel talks HTTP to the raw APIs (no new processes, no org OAuth,
no gateway dependency). MCP servers are for MCP-native clients.
Re-probe quarterly — beta APIs move.
