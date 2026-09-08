# Upstream reuse map

| Upstream | Reuse decision |
|---|---|
| Universal-Commerce-Protocol/samples | Reference merchant-server shapes, discovery/capability flows, tests. Do not fork the entire merchant implementation into AgentCom. |
| modelcontextprotocol/typescript-sdk | Canonical production MCP SDK. MVP keeps domain logic transport-independent so this can be dropped in later. |
| AnswerDotAI/llms-txt | Follow the index/full-context pattern; do not invent a competing LLM index format. |
| xpaysh/awesome-agentic-commerce | Seed taxonomy and cross-check protocol/adoption links; AgentCom adds structured provenance, APIs, playbooks, and freshness. |
| anthropics/commerce-agents | Reference real retail-agent implementation patterns rather than making fictional agent architectures. |
| stripe-samples/machine-payments | Link to working MPP/x402 examples rather than reimplement payment cryptography. |

The `scripts/fetch-upstreams.sh` command shallow-clones all of these for local research.
