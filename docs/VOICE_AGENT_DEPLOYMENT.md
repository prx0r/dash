# UK Business Voice Agent — Deployment Guide

*From YAML config to live voice agent in 10 minutes.*

---

## Architecture

```
Phone Call (UK local number)
    │
    ▼
Telnyx SIP Trunk
    │
    ▼
GPT-Live ($0.05/min)
    │
    ▼
voiceagent API (/chat)
    │
    ├─→ Knowledge Graph (YAML)
    │     ├─ Business identity
    │     ├─ Services offered
    │     ├─ Policies (returns, pricing, cancellation)
    │     ├─ FAQs
    │     └─ Escalation rules
    │
    ├─→ Tool System
    │     ├─ create_support_ticket
    │     ├─ request_callback
    │     ├─ book_slot
    │     └─ check_business_hours
    │
    └─→ Store (conversation history)
```

## What We Have

| Component | Status | Source |
|-----------|--------|--------|
| Voice agent kernel | **Built** | `/root/voiceagent/` |
| YAML knowledge system | **Built** | `knowledge/*.yaml` |
| Electrician template | **Built** | `sparky_electrician_en.yaml` |
| Graph-grounded chat | **Built** | `app/graph.py` + `app/llm.py` |
| Tool system | **Built** | `app/tools.py` |
| Telnyx phone provisioning | **Built** | `cmail/src/phoneIdentity.ts` |
| Voice webhook routing | **Built** | `cmail/src/mcp.ts` |
| GPT-Live voice ($0.05/min) | **Available** | LiveKit + OpenAI |
| Docker deployment | **Built** | `Dockerfile` |

## What We Need

| Component | Status | Effort |
|-----------|--------|--------|
| Per-business YAML configs | Template exists | 5 min each |
| Telnyx SIP → voiceagent routing | Code exists | 1 hour integration |
| GPT-Live → voiceagent bridge | Architecture defined | 2 hours |
| Billing per call ($0.05/min + margin) | Need to build | 1 day |
| Dashboard for business owner | Need to build | 1 week |

---

## Step-by-Step: Deploy for One Business

### Step 1: Create Business YAML (5 minutes)

Copy the electrician template:

```bash
cp /root/voiceagent/knowledge/sparky_electrician_en.yaml \
   /root/voiceagent/knowledge/jones-electrical-en.yaml
```

Edit the YAML:

```yaml
business:
  name: "Jones Electrical"
  locale: "en-GB"
  phone: "+44 7XXX XXXXXX"  # From Telnyx
  hours:
    monday-friday: "08:00-18:00"
    saturday: "09:00-14:00"
    sunday: "closed"

agent:
  system_prompt: |
    You are the after-hours agent for Jones Electrical. Be warm, brief, operational.
    After hours: take name, phone, address, job type, urgency. Emergencies
    (sparks, burning smell, exposed wires, total power loss) → say the electrician
    will be woken and call back immediately. Everything else → promise a morning
    reply with a quote and slots. Never invent prices; use only quoted ranges.
    Ask for photos when useful (consumer unit, damage). Max 2 photos at night.

voice:
  edge_voice: "en-GB-RyanNeural"

nodes:
  - id: service.ev_charger
    type: service
    name: EV charger installation
    aliases: [ev charger, car charger, wallbox, zappi, ohme]
    text: "Home EV charger installs. Needs: address, parking setup, consumer unit photo, preferred date. Typical half-day job."
  - id: service.consumer_unit
    type: service
    name: Consumer unit replacement
    aliases: [fuse box, fuseboard, consumer unit]
    text: "Fusebox upgrades. Needs: photo of existing unit, house size. Full-day job, power off required."
  - id: service.fault
    type: service
    name: Fault finding
    aliases: [fault, tripping, power cut, sockets dead]
    text: "Diagnostics visit. Needs: symptoms, when it started, photos if visible damage."
  - id: escalation.safety
    type: escalation
    name: Electrical emergency
    aliases: [sparks, burning, smoke, exposed wire, shock, power loss]
    text: "Wake the electrician immediately. Tell customer to switch off at the mains if safe and not to touch anything."

edges:
  - source: service.ev_charger
    target: policy.pricing
    relation: governed_by
  - source: escalation.safety
    target: service.fault
    relation: related_to
```

### Step 2: Deploy (1 minute)

```bash
# Option A: Docker
docker build -t voiceagent-jones .
docker run -d -p 8080:8080 \
  -e BUSINESS_CONFIG=knowledge/jones-electrical-en.yaml \
  -e LLM_API_KEY=$OPENAI_API_KEY \
  --name jones-electrical \
  voiceagent-jones

# Option B: Direct
BUSINESS_CONFIG=knowledge/jones-electrical-en.yaml \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### Step 3: Connect Telnyx (1 minute)

In cmail, wire the phone number:

```bash
# Provision UK number
curl -X POST https://cmail.tradesprior.workers.dev/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool":"name.phone_search","args":{"country":"GB"}}'

# Purchase number (after human confirms)
curl -X POST https://cmail.tradesprior.workers.dev/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool":"name.phone_purchase","args":{"phone_number":"+447XXXXXXXXX","confirmed":true}}'

# Set voice webhook to point to voiceagent
# Telnyx dashboard → Call Control → Webhook URL: https://voiceagent.yourdomain.com/chat
```

### Step 4: Connect GPT-Live (1 minute)

Configure GPT-Live to bridge Telnyx SIP to voiceagent:

```bash
# Telnyx: Create SIP connection → voiceagent API
# GPT-Live: Point to voiceagent /chat endpoint
# Voice webhook: Telnyx → GPT-Live → voiceagent → response → caller
```

### Step 5: Test (1 minute)

```bash
# Call the number
# Say: "Hi, I need an EV charger installed"
# Agent should: greet, take details, offer callback
# Check: voiceagent logs show conversation + tool calls
```

---

## The 10-Minute Onboarding Flow

For each new UK business:

| Minute | Action | Automation |
|--------|--------|------------|
| 0-1 | "What's your business name?" | cmail MCP |
| 1-2 | Buy domain (~$10) | cmail MCP (human confirmed) |
| 2-3 | Wire email (hello@business.co) | cmail MCP |
| 3-4 | Get UK phone number (~$1/mo) | cmail MCP (human confirmed) |
| 4-5 | Set voice agent greeting | Generate from business name + type |
| 5-6 | Create YAML config | Template + business info |
| 6-7 | Deploy voice agent | Docker |
| 7-8 | Connect Telnyx SIP | Auto |
| 8-9 | Forward existing number | cmail MCP |
| 9-10 | Voice agent live | Test call |

**Total cost to us per business:** ~$1/mo (Telnyx) + $0.05/min voice (billed to customer)
**Charge to business:** £15/mo (voice agent) + £0.10/min (calls) = ~£25-50/mo typical

---

## Revenue Model

| Component | Cost to Us | Charge to Customer | Margin |
|-----------|-----------|-------------------|--------|
| Telnyx number | $1/mo | £5/mo | £4/mo |
| Voice agent (GPT-Live) | $0.05/min | £0.10/min | 50% |
| Domain (amortized) | $0.83/mo | £3/mo | £2.17/mo |
| Email routing | $0 (Cloudflare free) | £2/mo | £2/mo |
| **Total per business** | ~£5/mo + voice | ~£15-50/mo | **£10-45/mo** |

At 100 businesses: **£1,000-4,500/mo recurring revenue.**

---

## Scaling: From One to 100

### Phase 1: Manual (0-10 businesses)
- Hand-craft each YAML config
- Manual Telnyx setup
- Manual GPT-Live bridge
- 10 minutes per business

### Phase 2: Semi-Automated (10-50 businesses)
- YAML generator from business profile
- Automated Telnyx provisioning via cmail
- One-click deployment
- 5 minutes per business

### Phase 3: Fully Automated (50-100+ businesses)
- ChatGPT plugin: "Set up a voice agent for [business]"
- Auto-detect business type from Google Business Profile
- Generate YAML from template + scraped data
- Deploy + connect in background
- 2 minutes per business

---

## The ChatGPT-Native Transition

Once the voice agent is running, the business owner can interact through ChatGPT:

```
Business owner: "Any missed calls today?"
ChatGPT: "Yes, 3 calls while you were on the tools:
  1. John Smith (07XXX) — wants EV charger install, callback tomorrow 2pm
  2. Sarah Jones (07XXX) — consumer unit quote, sent photos
  3. Emergency: sparks from socket — you've been alerted
   Want me to send any of them a message?"

Business owner: "Send John a confirmation for 2pm tomorrow"
ChatGPT: "Done. Sent SMS to John confirming EV charger consultation, tomorrow 2pm."
```

This is the ChatGPT-native endpoint. The voice agent is the input layer. ChatGPT is the management layer. The business runs through both.

---

## What's Different About This vs Vapi/Bland.ai?

| Feature | Vapi/Bland | Our Stack |
|---------|-----------|-----------|
| Monthly fee | $50-500/mo | £0 (just per-minute) |
| Per-minute cost | $0.05-0.15 | $0.05 (GPT-Live) |
| Customization | Limited | Full YAML control |
| Knowledge grounding | RAG on docs | Graph-grounded (nodes + edges) |
| Tool integration | Basic | Full tool system (tickets, bookings, callbacks) |
| Multi-language | Extra cost | Built-in (EN/NO/SV in templates) |
| Ownership | Rented | Ours (data, config, graph) |
| ChatGPT integration | None | Native (MCP endpoint) |

**Our advantage:** We own the full stack. No vendor lock-in. No monthly fees. Just per-minute cost + margin.
