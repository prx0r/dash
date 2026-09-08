# Deploy

## VPS / systemd

```bash
npm run check
BASE_URL=https://agentcom.org PORT=8787 node server.mjs
```

Put Caddy or nginx in front for TLS and compression.

## Docker

```bash
docker build -t agentcom .
docker run -e BASE_URL=https://agentcom.org -p 8787:8787 agentcom
```

## Cloud Run / Render / Railway / Fly

Use the included Dockerfile and set:

- `BASE_URL=https://agentcom.org`
- `PORT` if the platform does not inject it

## DNS / caching

Put Cloudflare in front if desired. Cache static assets and GET APIs briefly; do not cache MCP POST or audit POST requests.

## Before launch

- Set `BASE_URL` and run `npm run build`.
- Confirm `/llms.txt`, `/agents.md`, `/openapi.json`, and `/.well-known/agentcom.json` contain the production domain.
- Add uptime monitoring for `/api/v1/health`.
- Add request logs and abuse limits to `/api/v1/audit` before opening it to heavy public traffic.
