# AgentCom.org

**The open operating manual for agentic commerce.**

AgentCom is a machine-readable public resource hub for merchants, developers, and AI agents. The canonical data lives as structured records and is rendered into HTML, Markdown, JSON, API responses, NDJSON, `llms.txt`, `agents.md`, a knowledge graph, and MCP resources/tools.

## Why this exists

Agentic-commerce guidance is fragmented across protocol repos, platform docs, announcements, merchant help centers, and fast-changing integrations. AgentCom makes the *map* canonical without pretending to replace the primary sources.

Core rule: **primary sources first, provenance always, mutable facts timestamped.**

## Run the MVP

Requirements: Node.js 22+. There are no runtime npm dependencies.

```bash
npm run check
npm start
# http://localhost:8787
```

Or:

```bash
docker build -t agentcom .
docker run --rm -p 8787:8787 agentcom
```

Set the canonical URL in production:

```bash
BASE_URL=https://agentcom.org npm run build
BASE_URL=https://agentcom.org npm start
```

## Machine interfaces

| Surface | Endpoint |
|---|---|
| JSON catalog | `/api/v1/catalog` |
| Search | `/api/v1/search?q=shopify+ucp` |
| Item JSON | `/r/shopify-agent-readiness.json` |
| Item Markdown | `/r/shopify-agent-readiness.md` |
| Content negotiation | `Accept: application/json` or `text/markdown` on `/r/:slug` |
| Bulk export | `/api/v1/export.ndjson` |
| Knowledge graph | `/api/v1/graph` |
| OpenAPI | `/openapi.json` |
| LLM index | `/llms.txt` |
| Full LLM context | `/llms-full.txt` |
| Agent description | `/agents.md` |
| AgentCom descriptor | `/.well-known/agentcom.json` |
| MCP HTTP | `POST /mcp` |
| MCP stdio | `npm run mcp` |
| Store readiness audit | `POST /api/v1/audit` |

### MCP tools

- `search_agentcom`
- `get_agentcom_item`
- `list_protocols`
- `list_platform_playbooks`
- `audit_store_readiness`

The HTTP MCP endpoint implements the JSON-RPC methods required by this MVP (`initialize`, tool/resource/prompt discovery, calls, reads, and ping). For production at scale, swapping the transport adapter to the official MCP TypeScript SDK is straightforward; the domain logic is isolated in `src/lib/mcp.mjs`.

## Canonical records

`src/data/` contains:

- `protocols.json` — UCP, MCP, ACP, AP2, A2A, x402, MPP
- `platforms.json` — Shopify, Google, OpenAI, Stripe, TikTok, Meta
- `guides.json` — implementation playbooks
- `resources.json` — official docs, repos, specs, and selected high-signal indexes
- `glossary.json`
- `manifest.json`

Each published record includes primary-source provenance and `last_verified` dates.

## Upstream projects we deliberately reuse/track

Run:

```bash
./scripts/fetch-upstreams.sh
```

This shallow-clones:

1. `Universal-Commerce-Protocol/samples` — reference UCP merchant servers and A2A examples.
2. `modelcontextprotocol/typescript-sdk` — official MCP server/client implementation.
3. `AnswerDotAI/llms-txt` — `llms.txt` proposal and tooling.
4. `xpaysh/awesome-agentic-commerce` — verification-oriented ecosystem map.
5. `anthropics/commerce-agents` — retail/commerce agent blueprints.
6. `stripe-samples/machine-payments` — MPP/x402 payment examples.

They are references, not vendored dependencies. AgentCom stays small and dependency-free while pointing builders to the authoritative implementation projects.

## Store readiness auditor

`POST /api/v1/audit` with:

```json
{"url":"https://example.com"}
```

The auditor checks public surfaces such as HTTPS, `robots.txt`, `llms.txt`, `agents.md`, product structured data, pricing/availability signals, policies, `/.well-known/ucp`, and sitemap presence. It is intentionally labeled heuristic; platform eligibility and authenticated transaction flows require deeper checks.

## Source and editorial policy

See `docs/SOURCE_POLICY.md`. Short version:

- Primary protocol/platform docs outrank commentary.
- No uncited platform requirement enters a canonical guide.
- Every source gets a verification date.
- Guidance should say what is **required**, **available**, **optional**, or **experimental**.
- AgentCom never invents a protocol-discovery convention and labels its own convenience descriptors as such.

## Deploy

The whole app is one Node process and can run on Fly.io, Render, Railway, Google Cloud Run, AWS App Runner, a VPS, or any Docker host. See `docs/DEPLOY.md`.

## License

- Code: MIT (`LICENSE`)
- Canonical content/data: intended for CC BY 4.0 reuse; see `CONTENT-LICENSE.md`.
