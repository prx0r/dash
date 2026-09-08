# AgentCom API examples

```bash
curl http://localhost:8787/api/v1/catalog
curl 'http://localhost:8787/api/v1/search?q=shopify+ucp'
curl http://localhost:8787/r/shopify-agent-readiness.json
curl http://localhost:8787/r/shopify-agent-readiness.md
curl -H 'Accept: application/json' http://localhost:8787/r/ucp
curl -X POST http://localhost:8787/api/v1/audit \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com"}'
```

MCP initialize:

```bash
curl -X POST http://localhost:8787/mcp \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2026-07-28","capabilities":{},"clientInfo":{"name":"demo","version":"0.1"}}}'
```
