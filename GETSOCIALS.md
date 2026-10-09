# GETSOCIALS — guiding northstar

> Check a name → buy the domain → wire email → get phone → claim the
> handles → connect the APIs. Human confirms spend and clicks where only
> humans can. Everything else is machine.

## The question

Is it POSSIBLE for an agent to post on insta, to email, to have a website?

The agent doesn't care about content. It cares about **credentials and
capabilities**. getsocials answers the capability question once per company,
then every vertical reuses the answer.

## The shape

```
getsocials/
├── domain/    check → purchase (H) → done
├── email/     wire → verify
├── phone/     search → purchase (H)
├── insta/     check → claim (H) → verify → connect (H)
├── x/         check → claim (H) → verify → connect (H)
└── youtube/   check → claim (H) → verify → connect (H)
```

Every subroutine follows **check → claim/approve → verify → connect**:

| Phase | Who | What |
|-------|-----|------|
| check | machine | availability map, cheapest-provider pick |
| claim/approve | human | platforms block bots; spend needs `confirmed:true` |
| verify | machine | claimed handle resolves, email round-trips |
| connect | human + machine | one OAuth click per platform, machine stores the ref |

## Who does what

cmail + steve give the agent the company id and the social functions.
The agent gets references (`cred:telnyx:prod`), never values. The kernel
gates every call. The graph records every result.

## Hard honesty (from stevejobless NORTHSTAR)

1. **No platform allows programmatic social account creation.** Instagram,
   TikTok, X, YouTube all require human signup. What we automate:
   availability map → claim order → deep links → verify claimed handles
   resolve → connect APIs. Claiming stays a ~10-minute human task;
   everything around it is machine.
2. **Cloudflare Registrar excludes some TLDs.** Exotics buy on
   Porkbun/Name.com, then NS-move to Cloudflare. Same end state, one hop.
3. **Financial actions need human-issued capability.** Agent requests,
   human approves, kernel injects. Agents cannot mint authority.

## Pause / resume

Subroutines are independent except where noted (social connects need
email + phone, because platforms verify via both). At any point:

```
domain + email done → pause socials → run /dropship template
→ populate products → site live → resume socials
```

Locked steps show their blockers. Nothing is lost. The company id is
the stable root; the DAG is the visual of the graph's missing nodes.

## Where it lives

- Procedure: `agentcom/kernel/graph/getsocials.py` (`GetsocialsDAG`)
- Gate: `agentcom/kernel/capabilities/` (policy → approval → inject → audit)
- Identity: `agentcom/kernel/graph/identity.py` (`COMP-XXXXXXXX`)
- Tests: `agentcom/kernel/tests/` (98 green, incl. `SELF_JUSTIFYING_DOMAIN_PURCHASE_001`)
