# Free Datasets for BreadUp

*Market intelligence that powers the scanner and worlds system.*

---

## 1. UK Government Data (Free, No API Key)

### Companies House
- **URL:** https://api.companieshouse.gov.uk/
- **Data:** All UK limited companies — officers, filings, PSC, status, SIC codes
- **Bulk download:** https://download.companieshouse.gov.uk/ (469MB CSV, updated monthly)
- **API:** Free, no key needed for basic search
- **Use for BreadUp:** Identify UK businesses by category, find company density per vertical, verify business legitimacy
- **Value:** £1-3 billion/year estimated value to users (Companies House claim)

### ONS (Office for National Statistics)
- **URL:** https://api.beta.ons.gov.uk/v1
- **Data:** UK economic data — jobs, wages, inflation, regional stats, industry breakdowns
- **API:** Free, no API key required
- **Use for BreadUp:** Market sizing per vertical, regional demand signals, economic context for business creation
- **Key datasets:** Labour Force Survey, ASHE (wages), Consumer Price Index, Regional GVA

### Open Food Facts / Open Prices
- **URL:** https://prices.openfoodfacts.org
- **Data:** Crowdsourced product prices worldwide
- **API:** Free (AGPL-3.0)
- **Use for BreadUp:** Consumer product pricing baseline, grocery arbitrage opportunities

---

## 2. Marketplace APIs (Free Tiers)

### Etsy Open API v3
- **URL:** https://developers.etsy.com
- **Free tier:** 200 credits/month, 5 req/min
- **Data:** Listings, shops, reviews, taxonomy, sold items, favorites
- **Key endpoints:** search_listings, get_listing_details, get_listing_reviews
- **Filters:** is_vintage, is_handmade, min_price, max_price
- **Use for BreadUp:** Vintage item discovery, demand signals (favorites, reviews), pricing comps, seller benchmarking

### eBay APIs
- **Official API:** https://developer.ebay.com (requires app registration)
- **Scraping APIs (free tiers):**
  - Parse.bot: 200 credits/month free — search, item details, sold prices, seller profiles
  - Real Data API: Free key — real-time listings, sold history, 8 marketplaces
- **Use for BreadUp:** Sold price history (the most valuable data for comps), current listing density, seller competition analysis

### Shopify Storefront MCP
- **URL:** https://shopify.dev/docs/apps/build/storefront-mcp
- **Data:** Live products, carts, checkout, orders from any Shopify store
- **Use for BreadUp:** Agent-discovery of Shopify stores, product feeds, competitor monitoring

---

## 3. Price Intelligence APIs (Free Tiers)

### PricesAPI
- **URL:** https://pricesapi.io
- **Free tier:** 1,000 searches (one-time), 6 req/min
- **Data:** Product search with matched merchant offers, price history, cache metadata
- **Input:** Product name OR retailer URL
- **Output:** Matched products with offers[], prices, ratings, images
- **Use for BreadUp:** Cross-retailer price comparison, comps for any product

### RetailerAPI
- **URL:** https://retailerapi.com
- **Free tier:** 1,000 lookups/month, 5 req/min
- **Data:** Price, sellers, price history for any UPC/EAN/ISBN/ASIN
- **MCP server:** Open-source, works with Claude Desktop, Cursor
- **Use for BreadUp:** ISBN lookups for book arbitrage, UPC price comparison, historical price trends

### Product Search & Price Comparison (RapidAPI)
- **Free tier:** 1 req/sec
- **Data:** Multi-country product search with prices
- **Use for BreadUp:** Broad product discovery across retailers

### eCommerce Seller Toolkit
- **Free tier:** Available on RapidAPI
- **Data:** Fee calculators (Amazon, eBay, Etsy), margin calculators, barcode lookup
- **Use for BreadUp:** Accurate fee calculations per marketplace, profit modeling

---

## 4. Open Product Data

### Open Food Facts
- **URL:** https://world.openfoodfacts.org
- **Data:** 3M+ food products with barcodes, ingredients, nutrition, prices
- **License:** Open Database License
- **Use for BreadUp:** Grocery product identification, price benchmarking

### Barcode databases
- **UPC database:** https://www.upcdatabase.com (free API)
- **EAN-13:** https://ean-db.com (free lookups)
- **Use for BreadUp:** Product identification from photos/barcodes

---

## 5. Research & Intelligence

### Google Trends
- **URL:** https://trends.google.com
- **Data:** Search interest over time, regional demand, related queries
- **Use for BreadUp:** Demand forecasting, seasonal patterns, emerging trends

### Wayback Machine
- **URL:** https://web.archive.org
- **Data:** Historical web pages
- **Use for BreadUp:** Historical pricing from archived listings, seller evolution tracking

### UK Government Open Data
- **URL:** https://data.gov.uk
- **Data:** 50K+ datasets across all government domains
- **Use for BreadUp:** Regional economic data, housing data (for home services), transport data

---

## 6. The "Worlds" System

### Concept
Users create **worlds** — curated datasets + scanners + strategies that others can browse and subscribe to.

```text
User: "I'm researching vintage turntables"
         ↓
BreadUp: creates a World
  ├── Dataset: all turntable listings from eBay, Vinted, Facebook
  ├── Scanner: monitors new listings matching criteria
  ├── Comps: historical sold prices for each model
  ├── Strategy: buy under 35% of median comp
  └── Community: others can browse, subscribe, fork
```

### World Structure

```yaml
world:
  id: "vintage-turntables-uk"
  name: "Vintage Turntables UK"
  creator: "user123"
  description: >
    Scanning eBay, Vinted, and Facebook Marketplace for vintage
    turntables under £200. Focus on Thorens, Rega, Technics, Dual.
  
  dataset:
    sources:
      - ebay_uk (hourly scan)
      - vinted_uk (daily scan)
      - facebook_marketplace (daily scan)
    filters:
      categories: ["audio", "hi-fi", "turntables"]
      max_price: 200
      min_age: "1970-01-01"
      brands: ["Thorens", "Rega", "Technics", "Dual", "Pro-Ject", "Audio-Technica"]
    fields:
      - title
      - price
      - brand
      - model
      - condition
      - photos
      - seller_rating
      - location
      - listing_date
      - source_url
  
  scanner:
    frequency: "hourly"
    strategy:
      min_expected_profit: 30
      min_roi: 1.5
      max_hold_days: 60
  
  comps:
    sources:
      - ebay_sold (90 day history)
      - ebay_completed
    models:
      - "Thorens TD160"
      - "Rega Planar 3"
      - "Technics SL-1200"
      - "Dual 1229"
  
  subscription:
    free_tier: "browse listings, see daily digest"
    paid_tier: "£5/mo — full data, alerts, strategy signals"
    x402: "£0.01/alert — pay per notification"
```

### World Types

| Type | Description | Example |
|------|-------------|---------|
| **Product World** | Specific product category tracking | "Vintage Turntables UK" |
| **Niche World** | Aesthetic/style-based curation | "1920s Art Deco Furniture" |
| **Local World** | Geographic market intelligence | "Bristol Vintage Scene" |
| **Strategy World** | Shared sourcing approaches | "Joblot Books Flip Strategy" |
| **Brand World** | Specific brand ecosystem | "Thorens Turntable Parts" |

### Revenue Model

| Layer | Price | What They Get |
|-------|-------|---------------|
| **Browse** | Free | See world description, sample listings |
| **Daily Digest** | Free | Top 5 opportunities per day |
| **Full Access** | £5/mo | All listings, comps, alerts, strategy |
| **Per Alert** | £0.01 (x402) | Pay per notification via machine payments |
| **Fork** | Free | Copy world config, customize, run your own |

### The Stack

```
User creates World
    ↓
World definition (YAML/JSON)
    ↓
BreadUp Scanner (runs on schedule)
    ↓
Marketplace APIs (eBay, Etsy, Vinted, Facebook)
    ↓
Dataset (stored in BreadUp)
    ↓
Comps Engine (sold price history)
    ↓
Strategy Layer (buy/sell rules)
    ↓
Notifications (ChatGPT, email, SMS, x402)
    ↓
Community (browse, subscribe, fork)
```

---

## Priority Integration Order

| Priority | Dataset | Cost | Value |
|----------|---------|------|-------|
| 1 | Companies House API | Free | UK business intelligence |
| 2 | ONS API | Free | Market sizing per vertical |
| 3 | eBay sold prices (via Parse.bot) | Free tier | Comp engine foundation |
| 4 | Etsy API | Free tier | Vintage item discovery |
| 5 | PricesAPI | Free tier | Cross-retailer comparison |
| 6 | RetailerAPI | Free tier | ISBN/UPC lookups |
| 7 | Google Trends | Free | Demand forecasting |
| 8 | Open Prices | Free | Consumer product baseline |

---

## Quick Start: Companies House + ONS

```python
# Companies House — find all UK businesses by SIC code
import requests

# Search for electricians (SIC code 43210)
r = requests.get(
    "https://api.companies-house.gov.uk/search/companies",
    params={"q": "electrician", "items_per_page": 100},
    auth=("YOUR_API_KEY", "")  # Free registration
)
companies = r.json()

# ONS — get UK employment data by industry
r = requests.get(
    "https://api.beta.ons.gov.uk/v1/datasets/absemployment/editions/latest/versions/latest/observations",
    params={"industry": "construction", "measure": "employment"}
)
```

These two free APIs alone give us:
- Every UK business by category
- Employment data per industry
- Regional economic context
- Company status and officers
- SIC code mapping to our verticals
