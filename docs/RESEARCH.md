# Prior-art research and build decisions — 2026-09-08

AgentCom should not rebuild infrastructure that already has a credible canonical implementation.

## What already exists

### Universal Commerce Protocol

Official UCP repos already provide the commerce protocol, SDKs, conformance tests, and sample merchant implementations. The Node sample demonstrates a merchant server using Hono/Zod; official samples also cover A2A. **Decision:** AgentCom indexes/explains/tests UCP; it does not invent a replacement commerce protocol or vendor a parallel checkout server.

- https://github.com/Universal-Commerce-Protocol/ucp
- https://github.com/Universal-Commerce-Protocol/samples
- https://github.com/Universal-Commerce-Protocol/js-sdk
- https://github.com/Universal-Commerce-Protocol/conformance

### MCP

The official TypeScript SDK implements the current MCP spec and includes transports, middleware, and runnable examples. **Decision:** keep AgentCom's domain logic transport-independent. The zero-dependency MVP implements the narrow JSON-RPC surface required for its public read/search/audit use case; production can wire the same handlers to the official SDK instead of growing a custom MCP framework.

- https://github.com/modelcontextprotocol/typescript-sdk

### llms.txt

Answer.AI already proposed `/llms.txt` as an LLM-friendly index. **Decision:** implement it rather than create a competing site-index convention. AgentCom adds `llms-full.txt`, canonical JSON records, and MCP/API access.

- https://github.com/AnswerDotAI/llms-txt

### Awesome agentic-commerce lists

Multiple curated GitHub lists already track protocols and ecosystem links. The strongest useful pattern is verification/version awareness. **Decision:** AgentCom is not another README list. It adds normalized records, provenance dates, platform-specific implementation playbooks, machine interfaces, graph relationships, and a readiness auditor.

- https://github.com/xpaysh/awesome-agentic-commerce
- https://github.com/OrcaQubits/awesome-agentic-commerce
- https://github.com/bitrefill/awesome-agentic-payments

### Retail/commerce agent blueprints

Anthropic and other vendors publish reference commerce-agent architectures. **Decision:** link to real blueprints instead of manufacturing a proprietary generic agent framework.

- https://github.com/anthropics/commerce-agents

### Machine payments

Stripe/Tempo MPP and x402 already supply protocols and reference implementations. **Decision:** AgentCom explains where they fit and links working samples; it does not implement payment cryptography.

- https://mpp.dev/
- https://github.com/stripe-samples/machine-payments
- https://github.com/x402-foundation/x402

## Gap AgentCom fills

Existing resources tend to be one of:

1. protocol specifications,
2. SDK/sample repositories,
3. platform-specific docs,
4. curated link lists,
5. vendor marketing/field guides.

The missing useful layer is a **canonical, source-grounded operational map** where the same fact is consumable by humans and agents.

AgentCom MVP therefore focuses on:

- normalized protocol/platform/resource records,
- source authority and verification dates,
- practical merchant playbooks,
- deterministic HTML/Markdown/JSON alternates,
- searchable JSON API and bulk NDJSON,
- protocol/platform knowledge graph,
- MCP resources/tools/prompts,
- public merchant readiness auditing,
- explicit conventions (`llms.txt`, `agents.md`, OpenAPI) rather than decorative AI content.
