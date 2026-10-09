# Bakery — The World Abstraction

*From conversation on September 13, 2026. The design breakthrough for BreadUp.*

---

## The Core Insight

A **BreadUp World** is a user-curated economic dataset + ontology + scanner + update logic.

Not: gamified reselling app.
Not even: entrepreneurial agent.

**A system for turning expertise and public data into executable economic agents.**

---

## The Hierarchy

```text
WORLD
"What exists?"

DATASET
"What do we know?"

SCANNER
"What is happening?"

OPPORTUNITY
"What should we do?"

POLICY
"When should we act?"

AGENT
"Do it."
```

---

## World Structure

```text
WORLD: cult-live-vinyl
│
├── entities
│   ├── artists
│   ├── releases
│   ├── pressings
│   ├── labels
│   └── venues
│
├── relationships
│   ├── artist → performance
│   ├── performance → release
│   ├── release → pressing
│   └── pressing → market observations
│
├── evidence
├── valuations
├── scanners
├── watchers
└── actions
```

---

## The Killer UX

User: "I know loads about early Tool bootlegs. Let's make a dataset."

ChatGPT: "I've built the initial release graph from MusicBrainz and Discogs. I found 128 candidate live releases. Twelve have conflicting dates and seven appear to be duplicate pressings. Want to review those first?"

User corrects them.

ChatGPT: "Great. I've incorporated your corrections and created a `Tool Live Vinyl` World. What should we watch for?"

ChatGPT suggests: mislabelled pressings, releases below historical percentile, new listings with vague titles, unusual geographical listings, editions with falling available supply.

User: "Make scanners for all of those."

Done.

User: "Publish it."

Done.

**"Turn everything we just learned into a BreadUp World and publish three scanners from it."**

---

## Provenance Is Critical

Every field knows its source:

```text
value:
  "1973 Germany"

source:
  Discogs release 12345

confidence:
  0.98

observed_at:
  2026-09-13

license:
  CC0

contributor:
  system
```

User-derived knowledge:

```text
value:
  "actually recorded Manchester, not London"

source:
  user annotation

evidence:
  ticket-stub.jpg

confidence:
  0.91
```

BreadUp calculates **dataset reputation** from provenance.

---

## World Types

| Type | Description | Example |
|------|-------------|---------|
| **Product World** | Specific product category tracking | "Vintage Turntables UK" |
| **Niche World** | Aesthetic/style-based curation | "1920s Art Deco Furniture" |
| **Local World** | Geographic market intelligence | "Bristol Vintage Scene" |
| **Strategy World** | Shared sourcing approaches | "Joblot Books Flip Strategy" |
| **Brand World** | Specific brand ecosystem | "Thorens Turntable Parts" |
| **UK Business World** | Business intelligence by vertical | "UK Independent Plumbers" |

---

## The Free Data Surface

### Music Identity

| Dataset | What It Gives | License |
|---------|--------------|---------|
| **MusicBrainz** | artists, releases, recordings, labels, events, relationships | CC0 |
| **Discogs monthly dumps** | artists, labels, masters, releases, identifiers, editions | CC0 (metadata only) |
| **Discogs marketplace** | pricing, inventory, sales history | **Restricted** — not CC0 |

**Key distinction:** Discogs metadata (releases, labels, catalog numbers) is CC0. Discogs marketplace data (prices, sales) is restricted. BreadUp combines open canonical graph + observation layer.

### Product Intelligence

| Dataset | What It Gives | Size |
|---------|--------------|------|
| **Amazon Reviews 2023** | 48.19M products, 571M reviews, prices, metadata, images | Massive |
| **Amazon Berkeley Objects** | 147K products, images, 360° views | Medium |
| **MAVE (Google Research)** | 2.2M products, 3M attribute-value annotations, 1,257 categories | Medium |
| **Open Food Facts / Open Prices** | Crowdsourced product prices worldwide | Growing |

Amazon corpus includes: titles, descriptions, prices, categories, attributes, images, store identity, bought-together relationships. Category subsets line up with BreadUp: Books, CDs & Vinyl, Clothing, Electronics, Home & Kitchen, Beauty, Tools, Toys, Automotive.

MAVE teaches BreadUp what matters per category:
- Record: label, catalog_number, year, country, format, speed, edition
- Chair: brand, model, generation, material, size, color, base, arms
- Camera: model, mount, sensor, lens, condition, shutter_count

### UK Government Data

| Dataset | What It Gives | Cost |
|---------|--------------|------|
| **Companies House API** | Every UK company, SIC codes, officers, filings | Free |
| **Companies House bulk** | 469MB CSV of all live UK companies | Free |
| **ONS API** | Employment, wages, inflation by industry/region | Free |
| **HM Land Registry** | Every property transaction in England/Wales since 1995 | Free (5.3GB CSV) |
| **data.gov.uk** | 50K+ government datasets | Free |

### Market Intelligence

| Dataset | What It Gives | Cost |
|---------|--------------|------|
| **Google Trends BigQuery** | Rising/top searches, 5-year daily history, 50 countries | Free (1TB/mo) |
| **GDELT** | Global news events, entities, themes, relationships | Free |
| **Common Crawl** | 300B+ historical web pages since 2008 | Free |
| **OpenAlex** | Research papers, authors, companies, topics | Free |
| **Wikidata** | Massive entity/relationship graph | Free |

### Marketplace APIs (Free Tiers)

| API | Free Tier | Key Data |
|-----|-----------|----------|
| **Etsy Open API v3** | 200 credits/month | Listings, shops, reviews, vintage filter |
| **Parse.bot eBay** | 200 credits/month | Search, item details, sold prices, seller profiles |
| **PricesAPI** | 1,000 searches | Cross-retailer product search with offers |
| **RetailerAPI** | 1,000 lookups/month | UPC/EAN/ISBN price history |
| **eCommerce Seller Toolkit** | Free tier | Fee calculators for Amazon/eBay/Etsy |

---

## Worlds Unify BreadUp and Agentcom

### UK Business World Example

```text
UK Independent Plumbers World
│
├── Companies House (all UK plumbing companies)
├── Google/OSM (locations, reviews)
├── Websites (scraped, analyzed)
├── ChatGPT research (specialist knowledge)
├── User annotations (corrections, additions)
│
├── Scanners
│   ├── newly_incorporated_no_website
│   ├── high_reviews_poor_visibility
│   ├── old_website_growing_fast
│   └── missing_chatgpt_presence
│
└── Actions
    ├── onboarding_outreach
    ├── voice_agent_setup
    └── capability_provisioning
```

This is the UK onboarding lead engine. Same architecture as vinyl, different data.

### Property World Example

```text
UK Property Investment World
│
├── Land Registry (every transaction since 1995)
├── EPC data (energy ratings)
├── Planning applications
├── Rental listings
├── Crime data
├── Schools data
├── Transport data
│
├── Scanners
│   ├── undervalued_terraces
│   ├── high_yield_rents
│   ├── planning_permitted_development
│   └── below_market_auctions
│
└── Actions
    ├── valuation_alerts
    ├── investment_analysis
    └── viewing_scheduling
```

---

## Revenue Model

| Layer | Price | What They Get |
|-------|-------|---------------|
| **Browse** | Free | See world description, sample listings |
| **Daily Digest** | Free | Top 5 opportunities per day |
| **Full Access** | £4/mo | All listings, comps, alerts, strategy |
| **Per Alert** | £0.01 (x402) | Pay per notification via machine payments |
| **Fork** | Free | Copy world config, customize, run your own |
| **API** | x402 | Machine-consumable intelligence |

### x402 Underneath, Invisible to Users

Users see: **£4/month**

Machine agents see:
```text
GET /scanner/cult-vinyl/opportunities
402 Payment Required
```

Pay. Receive data. Exactly what x402 is good for: machine-consumable intelligence with tiny economic boundaries.

---

## World Publishing Stack

```text
WORLD
  │
  ├── human page (browse, subscribe)
  │
  ├── ChatGPT App/MCP (conversation)
  │
  ├── WebMCP (agent-facing)
  │
  ├── REST API (integration)
  │
  ├── x402 paid endpoint (machine payments)
  │
  └── scanner subscription (recurring)
```

Users can create the capability themselves. That's the jump.

---

## The Vinyl Demo (First World)

### Why Vinyl Is Perfect

1. **MusicBrainz** gives canonical identity (CC0)
2. **Discogs** gives physical edition graph (CC0 metadata)
3. **eBay/Etsy** give marketplace observations
4. **Community** is passionate and knowledgeable
5. **Physical products** = real inventory, real shipping, real P&L
6. **Niche knowledge** = moat (nobody knows every pressing)
7. **Measurable** — can track if intelligence leads to profit

### The Stack

```
MusicBrainz (canonical identity)
    +
Discogs CC0 (physical editions)
    +
eBay sold prices (market observations)
    +
User annotations (specialist knowledge)
    ↓
WORLD: cult-live-vinyl
    ↓
Scanners
    ├── underpriced_bootleg
    ├── rising_artist
    ├── rare_pressing
    └── repricing_lag
    ↓
Subscribers get alerts
    ↓
x402 for machine access
```

---

## Event Layer (GDELT)

Scanners become causal, not just price-based:

```
artist dies
     ↓
GDELT detects event
     ↓
Vinyl World resolves artist
     ↓
Discogs release graph
     ↓
BreadUp checks marketplace
     ↓
scanner detects repricing lag
```

Or:

```
film adaptation announced
     ↓
author / book graph
     ↓
first edition scanner
```

This is the Seesaw concept applied to collectible commerce.

---

## Historical Pricing (Common Crawl)

Common Crawl has 300B+ pages since 2008. Extract historical:
- retailer catalogues
- discontinued products
- MSRP
- dealer catalogues
- auction pages
- manufacturer pages

Example: "Make a World for 1990–2010 Japanese synthesizers."

ChatGPT searches historical crawl data and constructs:
- model
- release date
- original MSRP
- specification
- reviews
- historical retailer listings
- used observations
- modern marketplace observations

**The user doesn't manually construct a database. ChatGPT supervises dataset construction.**

---

## The World YAML Spec

```yaml
world:
  id: cult-live-vinyl
  name: "Cult Live Vinyl"
  creator: user123
  description: >
    Scanning for underpriced live-performance vinyl
    from cult artists. Focus on bootlegs, limited
    pressings, and rare concert recordings.

  ontology:
    entities:
      - artist
      - concert
      - recording
      - release
      - pressing
      - listing
    relationships:
      - artist → performance
      - performance → release
      - release → pressing
      - pressing → market_observations

  sources:
    canonical:
      - musicbrainz (CC0)
      - discogs_metadata (CC0)
    observations:
      - ebay_uk (API)
      - etsy (API)
      - user_sales
      - user_purchases

  transforms:
    - canonicalize_artist
    - resolve_release
    - identify_pressing
    - normalize_condition

  datasets:
    - release_graph
    - market_observations
    - price_history

  scanners:
    - id: underpriced_bootleg
      description: "Live recordings priced below 40% of median comp"
      frequency: hourly
      strategy:
        min_expected_profit: 25
        min_roi: 1.5

    - id: rising_artist
      description: "Artists with rising search interest but stable prices"
      frequency: daily
      strategy:
        trend_threshold: 0.4
        price_stability: 0.1

    - id: rare_pressing
      description: "Pressings with <10 known copies on marketplace"
      frequency: daily
      strategy:
        max_available: 10

  provenance:
    required: true
    confidence_threshold: 0.8

  subscription:
    free: "browse, daily digest"
    paid: "£4/mo — full access"
    x402: "£0.01/alert"
    fork: free
```

---

## The Redefinition

**BreadUp** = A system for turning expertise and public data into executable economic agents.

Not a reselling app.
Not a scanner marketplace.
Not a gamified entrepreneur tool.

**An operating system for economic intelligence.**

The reselling product is the perfect first application because you can measure whether intelligence is useful in **realized P&L**.

And the beautiful part: **ChatGPT becomes the World-builder UI.** Someone spends three hours nerding out about obscure vinyl with ChatGPT and at the end says:

> "Turn everything we just learned into a BreadUp World and publish three scanners from it."

That's the product.
