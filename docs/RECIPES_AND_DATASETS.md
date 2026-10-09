# BreadUp Recipes + Dataset Registry

*Workflows that demonstrate the system. Data that powers them.*

---

## Part 1: Dataset Registry

### Tier 1: Download Now (Free, No API Key)

| Dataset | Size | URL | Format | Use |
|---------|------|-----|--------|-----|
| **Companies House Bulk** | 469MB | https://download.companieshouse.gov.uk/ | CSV | UK business intelligence |
| **Companies House API** | Unlimited | https://api.companieshouse.gov.uk/ | JSON | Real-time company lookup |
| **ONS API** | Unlimited | https://api.beta.ons.gov.uk/v1 | JSON | UK economic data |
| **MusicBrainz Dump** | ~1GB | https://musicbrainz.org/doc/MusicBrainz_Database/Download | PostgreSQL XML | Canonical music identity |
| **Discogs Monthly Dump** | ~2GB | https://data.discogs.com/ | CSV/GZ | Physical edition graph |
| **Open Prices** | Growing | https://prices.openfoodfacts.org/api/v1 | JSON | Consumer product prices |
| **HM Land Registry** | 5.3GB | https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads | CSV | Property transactions since 1995 |
| **data.gov.uk** | 50K+ datasets | https://data.gov.uk | Various | UK government open data |

### Tier 2: Free Tiers (API Key Required)

| Dataset | Free Tier | URL | Use |
|---------|-----------|-----|-----|
| **Etsy Open API v3** | 200 credits/mo | https://developers.etsy.com | Vintage/handmade listings |
| **Parse.bot eBay** | 200 credits/mo | https://parse.bot | eBay search, sold prices, sellers |
| **PricesAPI** | 1,000 searches | https://pricesapi.io | Cross-retailer price comparison |
| **RetailerAPI** | 1,000 lookups/mo | https://retailerapi.com | UPC/EAN/ISBN price history |
| **eBay Developer API** | Free (app required) | https://developer.ebay.com | Official eBay data |
| **Google Trends BigQuery** | 1TB queries/mo | https://console.cloud.google.com/bigquery | Search trend data |
| **GDELT** | Unlimited | https://www.gdeltproject.org/data.html | Global events/news |
| **OpenAlex** | Unlimited | https://openalex.org | Research papers/companies |

### Tier 3: Free Datasets (Download)

| Dataset | Size | URL | Use |
|---------|------|-----|-----|
| **Amazon Reviews 2023** | 20GB+ | https://cseweb.ucsd.edu/~jmcauley/datasets.html | 48M products, 571M reviews |
| **MAVE (Google Research)** | 1GB | https://github.com/google-research-datasets/MAVE | 2.2M products, 3M attribute annotations |
| **Amazon Berkeley Objects** | 5GB | https://amazon-berkeley-objects.s3.amazonaws.com/index.html | 147K products with images |
| **Common Crawl** | Petabytes | https://commoncrawl.org | Historical web pages (since 2008) |
| **Wikidata Dump** | 100GB+ | https://dump.wikimedia.org | Entity/relationship graph |
| **Open Food Facts** | 10GB+ | https://world.openfoodfacts.org/data | 3M+ food products |

### Tier 4: Government/Institutional (Free, High Value)

| Dataset | Size | URL | Use |
|---------|------|-----|-----|
| **UK SIC Codes** | 100KB | https://standardindustrialclassification.com | Industry classification |
| **ONS Employment Data** | Via API | https://api.beta.ons.gov.uk/v1 | Jobs by industry/region |
| **ONS Wages (ASHE)** | Via API | https://api.beta.ons.gov.uk/v1 | Earnings by occupation |
| **Consumer Price Index** | Via API | https://api.beta.ons.gov.uk/v1 | Inflation data |
| **Planning Portal** | Via API | https://www.planningportal.co.uk | Planning applications |
| **EPC Register** | Via API | https://epc.opendatacommunities.org | Energy performance certificates |

---

## Part 2: Dataset Ingestion Instructions

### 1. Companies House (469MB, download today)

```bash
# Download the monthly snapshot
wget https://download.companieshouse.gov.uk/BasicCompanyDataAsOneFile-2026-09-01.zip

# Unzip
unzip BasicCompanyDataAsOneFile-2026-09-01.zip

# Load into BigQuery
# Schema: CompanyNumber, CompanyName, CompanyStatus, SICCode, RegisteredOfficeAddress, ...
bq load --source_format=CSV \
  drop.companies_house \
  BasicCompanyData-2026-09-01.csv \
  companies_house_schema.json
```

### 2. MusicBrainz (1GB, download today)

```bash
# Download the latest dump
wget https://ftp.musicbrainz.org/pub/musicbrainz/data/full/musicbrainz-20260901-000001.tar.bz2

# Extract
tar xjf musicbrainz-20260901-000001.tar.bz2

# Key tables for BreadUp:
# - artist (name, type, country, disambiguation)
# - release (title, date, country, label, barcode)
# - recording (title, length, artist)
# - release_group (type, first_release_date)
# - label (name, type, country)
# - area (name, type) -- for geography

# Load into BigQuery (key tables only)
for table in artist release recording release_group label; do
  bq load --source_format=CSV \
    drop.musicbrainz_$table \
    $table.csv \
    musicbrainz_${table}_schema.json
done
```

### 3. Discogs Monthly Dump (~2GB, download monthly)

```bash
# Download the latest monthly dump
wget https://data.discogs.com/dumps/discogsdumps/dumps/2026.09.01/
# Files: artists.csv.gz, labels.csv.gz, releases.csv.gz, masters.csv.gz, etc.

# Decompress
gunzip *.gz

# Key tables:
# - artists (name, profile, urls)
# - releases (title, country, date, labels, formats, barcode)
# - masters (main_release, year, title)
# - labels (name, profile, parent_label)

# Load into BigQuery
for table in artists releases masters labels; do
  bq load --source_format=CSV \
    drop.discogs_$table \
    $table.csv \
    discogs_${table}_schema.json
done
```

### 4. Amazon Reviews 203 (20GB, download for backtesting)

```bash
# From UCSD: https://cseweb.ucsd.edu/~jmcauley/datasets.html
# Download the "small" subset first (5GB)
wget https://jmcauley.ucsd.edu/data/amazon_v2/archive_2023.tar.gz

# Or download category-specific:
# Books, CDs & Vinyl, Electronics, Home & Kitchen, etc.

# Load into BigQuery (category by category)
for category in books_cds_vinyl electronics home_kitchen; do
  bq load --source_format=JSON \
    drop.amazon_reviews_$category \
    $category.json.gz \
    amazon_reviews_schema.json
done
```

### 5. ONS Employment Data (via API, real-time)

```python
import requests

# Get employment by industry (SIC sections)
base_url = "https://api.beta.ons.gov.uk/v1"

# List available datasets
datasets = requests.get(f"{base_url}/datasets").json()

# Get ABSEmployment data
data = requests.get(
    f"{base_url}/datasets/absemployment",
    params={"edition": "latest", "version": "latest"}
).json()

# Filter by industry and geography
observations = requests.get(
    f"{base_url}/datasets/absemployment/editions/latest/versions/latest/observations",
    params={"industry": "construction", "geography": "UK"}
).json()
```

---

## Part 3: Normalization for Backtesting

### The Entity Resolution Pipeline

Every item goes through:

```
RAW INPUT (photo, title, URL)
    │
    ▼
IDENTITY RESOLUTION
    │
    ├── Brand normalization (Dyson → Dyson, not "dyson" or "DYSON")
    ├── Model extraction (V15 Absolute, not "V15" or "v 15")
    ├── Variant detection (Cordless, not "corded" or "wireless")
    ├── Generation mapping (V15 Gen2, not "2nd gen" or "mk2")
    └── Alias resolution ("Henry Hoover" → Numatic Henry)
    │
    ▼
CONDITION NORMALIZATION
    │
    ├── Extracted from text: "excellent condition, minor scratches"
    ├── Mapped to scale: NEW / LIKE_NEW / GOOD / FAIR / POOR
    ├── Photos analyzed (if provided)
    └── Seller self-assessment vs buyer reality tracked
    │
    ▼
PRICE NORMALIZATION
    │
    ├── Currency conversion (GBP/EUR/USD at transaction date)
    ├── Fee calculation per platform
    ├── Shipping deduction (actual or estimated)
    ├── Bundle decomposition (if part of lot)
    └── Net price = gross - fees - shipping
    │
    ▼
TIME NORMALIZATION
    │
    ├── Listing date (first seen)
    ├── Last seen date (disappeared or sold)
    ├── Relisting detection (same item re-listed = not sold)
    ├── Price change tracking
    └── Sale confidence score
    │
    ▼
GEOGRAPHY NORMALIZATION
    │
    ├── UK region (from postcode or city)
    ├── Country (for cross-border)
    ├── Local market vs national market
    └── Shipping radius impact on demand
```

### The Observation Classes

```python
class Observation:
    """A market observation with provenance."""
    
    # What we observed
    item_id: str           # Canonical item ID
    platform: str          # ebay, etsy, vinted, facebook, user
    price: float           # Gross price
    currency: str          # GBP, EUR, USD
    net_price: float       # After fees + shipping
    condition: str         # NORMALIZED: new/like_new/good/fair/poor
    
    # When and where
    observed_at: datetime  # When we saw this
    location: str          # UK region or country
    source_url: str        # Original listing URL
    
    # How confident are we
    observation_class: str # See below
    confidence: float      # 0.0 - 1.0
    
    # What happened
    status: str            # active/sold/expired/unknown
    days_to_sale: int | None  # If we know when it sold
    price_changes: list    # History of price changes


# Confidence hierarchy
OBSERVATION_CLASSES = {
    "user_realized_sale": 1.0,      # Our user actually sold it
    "verified_marketplace_sale": 0.9,  # Confirmed sold on platform
    "listing_disappeared": 0.6,     # Was listed, now gone (probably sold)
    "observed_ask": 0.4,            # Current asking price (not sold)
    "dealer_offer": 0.5,            # Dealer/buyer offered this
    "user_purchase": 0.8,           # Our user bought it at this price
}
```

### The Backtesting Engine

```python
class BacktestEngine:
    """Query historical data for any item."""
    
    def query(
        self,
        identity: str,          # Canonical item ID
        geography: str = "UK",
        condition: str | None = None,  # Filter by condition
        channels: list[str] | None = None,
        horizon: str = "2y",    # How far back
    ) -> BacktestResult:
        """
        Returns:
            historical: median, P25, P75, days_to_sale, sell_through
            recent: last 14/30/90 days
            current_market: active listings, local supply
            confidence: based on sample size
        """
        pass
    
    def observe(self, observation: Observation):
        """Add a new observation. Updates running statistics."""
        pass
    
    def backtest_strategy(
        self,
        strategy: Strategy,
        period: str = "1y",
    ) -> StrategyResult:
        """Simulate a strategy against historical data."""
        pass
```

### The Cache Layer

Every resolved query is cached:

```python
class EntityCache:
    """Cache for resolved entities."""
    
    def get(self, entity_id: str) -> EntityRecord | None:
        """Get cached entity with all observations."""
        pass
    
    def put(self, entity_id: str, record: EntityRecord):
        """Store resolved entity. Merges new observations."""
        pass
    
    def invalidate(self, entity_id: str):
        """Force re-resolution (e.g., if identity resolution improved)."""
        pass


@dataclass
class EntityRecord:
    """Cached entity with all derived data."""
    
    entity_id: str          # e.g., "technics_sl_q2"
    aliases: list[str]      # ["Technics SL-Q2", "SLQ2", "SL-Q2"]
    brand: str              # "Technics"
    model: str              # "SL-Q2"
    category: str           # "turntable"
    
    # Visual fingerprints (for photo matching)
    visual_fingerprints: list[str]  # Image embeddings or feature hashes
    
    # Marketplace search patterns
    search_patterns: list[str]  # ["technics sl-q2", "technics slq2 turntable"]
    
    # Historical observations (append-only)
    observations: list[Observation]
    
    # Derived statistics (updated when observations change)
    price_distribution: PriceDistribution
    time_to_sale_distribution: TimeToSaleDistribution
    liquidity_score: float  # 0-1, how easy to sell
    
    # Last updated
    last_observed: datetime
    last_backtest: datetime
```

---

## Part 4: Recipes

### Recipe 1: "Car Boot Scout"

**Trigger:** User photographs a car boot table

```text
User: [photo of table with various items]
        ↓
BreadUp:
  1. Segment objects in photo
  2. For each object:
     a. Identify (brand, model, era, condition)
     b. Pull comps (eBay sold, Etsy sold)
     c. Calculate economics
     d. Check local supply
     e. Estimate time to sale
  3. Rank by ROI
  4. Present summary
        ↓
User sees:

Car Boot Scout — 7 items scanned

BUY (ROI > 100%):
├── Anglepoise lamp @ £20 → expected £48 (140% ROI, 12 days)
└── Brass candlestick @ £8 → expected £22 (175% ROI, 9 days)

MAYBE (ROI 50-100%):
├── Vinyl record 1 @ £5 → expected £12 (60% ROI, 21 days)
└── Ceramic vase @ £3 → expected £7 (50% ROI, 30 days)

PASS (ROI < 50% or slow):
├── Record 2 (£2 median, not worth listing)
├── Books (£1 each, shipping kills margin)
└── Picture frame (£4 median, too common)

Suggested bundle: lamp + candlestick = £28
Expected return: £70 (150% ROI)

[Add to Cart] [Take Photos] [Create Listings]
```

### Recipe 2: "Snap-to-List"

**Trigger:** User photographs an item they own

```text
User: [photo of item on desk]
        ↓
BreadUp:
  1. Identify: "Bose Wave Music System III, silver"
  2. Comps: 34 sold in 90 days
  3. Price distribution: P25=£70, P50=£85, P75=£105
  4. Current supply: 8 listed
  5. Sell-through: 65% within 30 days
        ↓
User sees:

Bose Wave Music System III — Silver

Fair value: £70–£105
├── Quick sale (7 days): list at £72
├── Balanced (14 days): list at £85
└── Max value (30+ days): list at £105

Current market: 8 listed, median ask £92
Your advantage: no platform fees if sold locally

[Choose speed]
  → User selects: "Balanced (14 days)"
        ↓
BreadUp generates:

Title: "Bose Wave Music System III — Silver — Excellent Condition"
Description: "Bose Wave Music System III in silver. Fully functional..."
Photos: [cleaned, cropped, enhanced]
Price: £85
Shipping: £12 (tracked, insured)
Marketplace: eBay + Facebook Marketplace
        ↓
User: [Publish]

BreadUp:
  Lists on eBay and Facebook
  Monitors for views, watchers, offers
  If no views in 7 days: suggests price reduction
  When sold: delists from other platforms
  Records actual sale price → feeds back into comps
```

### Recipe 3: "Room Clearance"

**Trigger:** User videos a room/garage/storage unit

```text
User: [video walkthrough of garage]
        ↓
BreadUp:
  1. Segment all objects (23 identified)
  2. Identify each
  3. Pull comps for each
  4. Group by strategy
        ↓
User sees:

Room Clearance — 23 items identified

INDIVIDUAL (sell separately, £1,280 total):
├── Vintage lawnmower (Ransomes) — £85
├── 3× power tools (Bosch/Silverline) — £45-120 each
├── Garden furniture set — £180
├── Boxing equipment — £65
├── Old radio (Bush) — £40
└── ... 18 more items

BUNDLES (sell as lots, £420 total):
├── Lot 1: "DIY toolkit" — estimated £95
├── Lot 2: "Garden tools" — estimated £65
└── Lot 3: "Sports equipment" — estimated £120

QUICK LIQUIDATION (clear everything, £380):
├── "Garage clearance — everything must go"
└── Estimated: £380 total

RECOMMENDATION:
Sell top 8 individually (high-value, fast-moving)
Bundle bottom 15 into 3 lots
Estimated total: £1,480 after fees (vs £380 all-at-once)

Time investment: ~5 hours for individual, ~1 hour for bundles

[Generate individual listings] [Generate bundles] [Liquidate all]
```

### Recipe 4: "Business Idea Validator"

**Trigger:** User describes a business idea

```text
User: "I want to start selling vintage turntables"
        ↓
BreadUp:
  1. Market research:
     - eBay UK: 2,400 active listings, 1,800 sold in 90 days
     - Etsy UK: 890 listings, 340 sold in 90 days
     - Average price: £85-£180 depending on brand/model
     - Top brands: Technics, Thorens, Rega, Dual, Pro-Ject
  2. Competition analysis:
     - 12 sellers with >100 sales in this category
     - Average seller rating: 4.7/5
     - Average listing quality: medium
  3. Sourcing analysis:
     - Car boots: £10-£40 per unit (good condition)
     - Charity shops: £15-£60 per unit
     - eBay lots: £20-£80 per unit (volume)
     - Facebook Marketplace: £15-£50 per unit
  4. Economics simulation:
     - Average buy: £35
     - Average sell: £95
     - Average fees: £12
     - Average shipping: £15
     - Average profit: £33 per unit
     - Average days to sell: 18
     - Monthly turnover: ~5 units with £200 capital
        ↓
User sees:

Vintage Turntables UK — Business Validation

MARKET SIZE
├── Active listings: 3,290
├── Monthly sold: ~2,140
├── Average price: £95-£180
└── Market is liquid and active

COMPETITION
├── 12 serious sellers (>100 sales)
├── Average rating: 4.7/5
├── Room for new entrants: YES
└── Differentiation opportunity: better photos, faster shipping

SOURCING
├── Best channels: car boots, Facebook, charity shops
├── Average buy price: £35
├── Supply availability: GOOD (year-round)
└── Seasonal peak: Sep-Dec (Christmas demand)

ECONOMICS (with £500 starting capital)
├── Month 1: buy 10 units, sell 6, profit £198
├── Month 3: rolling capital £800, sell 10/month, profit £330
├── Month 6: rolling capital £1,200, sell 15/month, profit £495
└── Year 1 projected: £4,500-£6,000 profit on £500 start

VERDICT: VIABLE — good margins, active market, low capital requirement

[Create business] [Backtest 6 months] [Find first 10 items to buy]
```

### Recipe 5: "Pinterest Niche Finder"

**Trigger:** User wants to start a Pinterest-driven business

```text
User: "Find me a Pinterest niche with rising demand and low competition"
        ↓
BreadUp:
  1. Pinterest trend analysis:
     - Rising: "dark academia decor" (+180% searches)
     - Rising: "cottagecore kitchen" (+120% searches)
     - Rising: "japandi furniture" (+95% searches)
  2. Marketplace supply analysis:
     - Dark academia: 12,000 listings (high competition)
     - Cottagecore kitchen: 4,500 medium (medium)
     - Japandi furniture: 800 listings (low competition)
  3. Margin analysis:
     - Dark academia: AOV £35, margin 45%
     - Cottagecore kitchen: AOV £28, margin 52%
     - Japandi furniture: AOV £120, margin 65%
  4. Ad viability:
     - Japandi: high AOV supports paid acquisition
     - Pinterest CPC: £0.40-£0.80
     - Target CAC: £12
        ↓
User sees:

TOP PICK: Japandi Furniture

WHY THIS NICHE:
├── Search interest: +95% (rising fast)
├── Listing density: LOW (only 800 on eBay UK)
├── AOV: £120 (high — supports paid ads)
├── Gross margin: 65% (excellent)
├── Source availability: good (scandinavian auctions)
└── Pinterest fit: HIGH (visual, aesthetic, aspirational)

ECONOMICS
├── Average product: £45 cost → £120 sale
├── After fees + shipping: £85 net
├── Profit per unit: £40
├── With 20% ad spend: £24 profit per unit
└── Break-even: 8 units/month

TEST BUSINESS: £300
├── Source 6 items from auctions
├── Create Pinterest business account
├── Generate 20 pins (lifestyle shots)
├── Run £50 test campaign
└── Expected return in 30 days: £240

[Create Japandi business] [Backtest] [Generate Pinterest campaign]
```

### Recipe 6: "Price Drop Claimer"

**Trigger:** User bought something that dropped in price

```text
User: "I bought this laptop 2 weeks ago. Did the price drop?"
        ↓
BreadUp:
  1. Identifies: "MacBook Air M3 13-inch, 256GB, Space Gray"
  2. Checks purchase date: Sep 1, 2026
  3. Current price: £949 (was £999)
  4. Price drop: £50
  5. Check retailer price protection:
     - Apple: 14-day window (expired)
     - Credit card: some cards offer 90-day
  6. Check price tracking services
        ↓
User sees:

Price Drop Alert — MacBook Air M3

Purchase: £999 on Sep 1, 2026 (12 days ago)
Current: £949 (-£50)

PRICE PROTECTION STATUS:
├── Apple: EXPIRED (14-day window passed)
├── Credit card: CHECK YOUR CARD
│   (some cards offer 90-day price protection)
└── Third party: Not applicable

RECOMMENDATION:
Check if your credit card offers price protection.
If yes: claim £50.
If no: consider setting price alerts for future purchases.

[Set price alert for this item] [Check my credit card policy]
```

### Recipe 7: "Agent-to-Agent Negotiation"

**Trigger:** Both buyer and seller are BreadUp users

```text
Buyer Agent: "I need 10 vintage Anglepoise lamps. Max £22 each."
        ↓
BreadUp:
  1. Scans marketplace for matching items
  2. Finds seller with 15 in stock
  3. Buyer agent contacts seller agent
        ↓
Negotiation:

Buyer: "10 units, £22 each, £220 total"
Seller: "Can do £24 each for 10, or £21.50 for 20"
Buyer: "£23 each for 10, deal?"
Seller: "Counter: £23.50, or I include free shipping"
Buyer: "Deal at £23.50"
        ↓
BreadUp:
  1. Creates order
  2. Holds payment in escrow
  3. Seller ships with tracked delivery
  4. Buyer confirms receipt
  5. Payment released
  6. Both get reputation score updated
        ↓
Transaction:
├── Amount: £235
├── Escrow held: 3 days
├── Shipping: tracked, insured
├── Both parties verified
└── Reputation: +1 for both
```

### Recipe 8: "Seasonal Playbook"

**Trigger:** User asks what to stock for upcoming season

```text
User: "What should I stock for Christmas?"
        ↓
BreadUp:
  1. Analyzes historical demand patterns
  2. Cross-references with current supply
  3. Calculates margin potential
  4. Recommends timing
        ↓
User sees:

Christmas Playbook 2026

BUY NOW (Oct-Nov, before prices rise):
├── Vintage Christmas decorations: +200% demand in Dec
│   Source: car boots, charity shops. Buy at £2-5, sell at £15-25
├── Retro board games: +150% demand. Buy at £3-8, sell at £20-35
├── Mid-century serving ware: +120% demand. Buy at £10-20, sell at £40-60
└── Old-fashioned toys: +180% demand. Buy at £5-10, sell at £25-40

BUY IN NOVEMBER (before Black Friday):
├── Gift boxes/baskets: +300% demand. Buy at £2-4, sell at £15-25
├── Scented candles: +150% demand. Buy at £3-8, sell at £18-30
└── Personalised items: +200% demand. Source POD at £5-10, sell at £25-40

AVOID:
├── Christmas jumpers: oversaturated, low margins
├── Generic gift sets: Amazon dominates
└── Tech accessories: too much competition

TIMELINE:
├── Oct 15: Start sourcing decorations
├── Nov 1: List Christmas items
├── Nov 15: Start Pinterest ads
├── Dec 1: Peak sales window
├── Dec 15: Last shipping dates
└── Dec 26: Clearance begins

Estimated total investment: £500
Estimated return: £1,800-£2,400
ROI: 260-380%

[Create Christmas strategy] [Find suppliers] [Generate Pinterest campaign]
```

### Recipe 9: "Failure Pattern Detector"

**Trigger:** User's listings aren't selling

```text
User: "My listings aren't selling. What am I doing wrong?"
        ↓
BreadUp:
  1. Analyzes user's listing history
  2. Compares to successful sellers in same category
  3. Identifies patterns
        ↓
User sees:

Listing Performance Analysis

YOUR LISTINGS:
├── Average photos: 3.2 (below category avg of 6.8)
├── Average title length: 28 chars (below 60 char best practice)
├── Average price vs comps: 15% above median
├── Average shipping: £8.50 (above category avg of £5.50)
├── Average response time: 4.2 hours (below 1-hour best practice)
└── Average description: 45 words (below 150 word best practice)

TOP ISSUES:
1. PHOTOS: You average 3.2 photos. Successful sellers average 6.8.
   → Add 3-4 more photos: back, sides, any flaws, scale reference.
2. PRICING: You're 15% above median. Items priced above P75 take
   3x longer to sell.
   → Try pricing at P50 (median) for faster turnover.
3. TITLES: Your titles are too short. Include brand, model, condition,
   and key features.
4. DESCRIPTIONS: 45 words vs 150 word average. Include measurements,
   condition details, and what's included.

IMPROVEMENT ESTIMATE:
If you fix photos + pricing, expect 40-60% more sales.

[Auto-fix photos] [Reprice listings] [Rewrite descriptions]
```

### Recipe 10: "Cross-Border Arbitrage"

**Trigger:** User wants to buy in UK, sell in Germany

```text
User: "What can I buy cheap in UK and sell for more in Germany?"
        ↓
BreadUp:
  1. Cross-references UK prices vs German prices
  2. Calculates shipping + fees + customs
  3. Identifies profitable channels
        ↓
User sees:

Cross-Border Arbitrage: UK → Germany

TOP OPPORTUNITIES:
├── Vintage audio (Thorens, Dual, Beogram)
│   UK price: £80-150 | DE price: €150-280
│   After shipping (€25) + fees (10%): profit €40-100
├── British pottery (Wedgwood, Royal Doulton, Moorcroft)
│   UK price: £20-60 | DE price: €45-120
│   After shipping: profit €15-40
├── UK children's books (Enid Blyton, Beatrix Potter first editions)
│   UK price: £15-80 | DE price: €30-150
│   After shipping: profit €10-50
└── British heritage brands (Barbour, Hunter, Dr. Martens)
    UK price: £30-80 | DE price: €60-150
    After shipping: profit €15-50

LOGISTICS:
├── Shipping: Royal Mail International (€15-25 per item)
├── Customs: under €150 = no duty for buyer
├── Payment: Wise for EUR transfers (0.5% fee)
├── Platform: eBay.de (reach German buyers)
└── Time: 5-10 days delivery

TEST: Buy 5 items, list on eBay.de
Investment: ~£300
Expected return: ~€500 (after all costs)
ROI: ~50%

[Find first 5 items] [Create eBay.de listings] [Set up Wise account]
```

---

## Part 5: Backtesting API Spec

```python
# The general backtesting MCP

@function_tool
def backtest_item(
    identity: str,
    geography: str = "UK",
    condition: str | None = None,
    channels: list[str] | None = None,
    horizon: str = "2y",
) -> BacktestResult:
    """Query historical data for any item.
    
    Returns median price, price distribution, days to sale,
    sell-through rate, current supply, and confidence.
    """
    pass


@function_tool
def backtest_category(
    category: str,
    geography: str = "UK",
    price_range: tuple[float, float] | None = None,
    horizon: str = "1y",
) -> CategoryResult:
    """Get category-level statistics.
    
    Returns average margins, turnover rates, seasonal patterns,
    competition density, and opportunity score.
    """
    pass


@function_tool
def backtest_strategy(
    strategy_config: str,
    capital: float = 500,
    period: str = "6m",
) -> StrategyResult:
    """Simulate a strategy against historical data.
    
    Returns simulated P&L, win rate, max drawdown,
    Sharpe ratio, and recommended adjustments.
    """
    pass


@function_tool
def observe_sale(
    item_id: str,
    sale_price: float,
    platform: str,
    fees: float = 0,
    shipping: float = 0,
) -> str:
    """Record a realized sale. Feeds back into backtesting.
    
    This is how the system gets smarter. Every sale
    improves future valuations.
    """
    pass


# Response schemas

@dataclass
class BacktestResult:
    historical: HistoricalStats  # 2-year stats
    recent: RecentStats          # 14/30/90 day stats
    current_market: MarketStats  # Active listings, supply
    confidence: float            # 0.0 - 1.0
    cached: bool                 # Was this from cache?

@dataclass
class HistoricalStats:
    median_price: float
    p25_price: float
    p75_price: float
    median_days_to_sale: float
    sell_through_30d: float  # % sold within 30 days
    sell_through_90d: float
    total_observations: int
    date_range: str          # "2024-09 to 2026-09"

@dataclass
class RecentStats:
    window: str              # "14d", "30d", "90d"
    median_price: float
    median_days_to_sale: float
    sell_through: float
    price_trend: str         # "+3%", "-2%", "stable"
    supply_trend: str        # "increasing", "decreasing", "stable"
```

---

## Part 6: Data Pipeline

```text
                    SOURCES
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
 MARKETPLACES     GOVERNMENT        USER DATA
    │                  │                  │
 eBay API         Companies House    User sales
 Etsy API         ONS                User purchases
 Vinted           Land Registry      User valuations
 Facebook         Google Trends      User photos
 Discogs          GDELT              User annotations
 MusicBrainz      Wikidata           User feedback
    │                  │                  │
    └──────────────────┼──────────────────┘
                       │
                  INGESTION
                       │
                  ┌────┴────┐
                  │         │
              Raw Data  Normalized
                  │         │
              Storage    Resolution
                  │         │
              Cache      Statistics
                  │         │
              Query     Backtest
                  │         │
                  └────┬────┘
                       │
                  OUTPUT
                       │
              ┌────────┼────────┐
              │        │        │
          ChatGPT   API    Web UI
              │        │        │
          Recipes  x402  Dashboard
```

---

## Part 7: Storage Requirements

| Dataset | Size | Storage | Notes |
|---------|------|---------|-------|
| Companies House | 469MB | BigQuery | Monthly refresh |
| MusicBrainz | 1GB | BigQuery | Bi-weekly refresh |
| Discogs | 2GB | BigQuery | Monthly refresh |
| Amazon Reviews | 20GB | BigQuery | Static (2023 snapshot) |
| eBay observations | Growing | BigQuery | Real-time |
| User sales | Growing | BigQuery | Real-time |
| Entity cache | ~5GB | Redis + BigQuery | Real-time |
| Backtest results | ~10GB | BigQuery | Cached queries |

**Total initial: ~30GB (fits in BigQuery free tier)**

**BigQuery free tier:** 1TB queries/mo, 10GB storage. More than enough for MVP.

---

## Part 8: Quick Start

### Today (30 minutes)

1. Download Companies House bulk (469MB)
2. Download MusicBrainz dump (1GB)
3. Download Discogs monthly dump (2GB)
4. Load all three into BigQuery
5. Test: "Find all UK companies with SIC code 95220 (repair of household appliances)"

### This Week (4 hours)

1. Set up Etsy API credentials
2. Set up Parse.bot eBay API
3. Build entity resolution pipeline
4. Test: "What's a Technics SL-Q2 worth?" → backtest from comps

### This Month (20 hours)

1. Build the backtesting engine
2. Build the caching layer
3. Build the first 5 recipes
4. Test with real users
5. Iterate

### This Quarter (100 hours)

1. Build Worlds system
2. Build BreadPacks marketplace
3. Build BreadActors marketplace
4. Launch ChatGPT app
5. Launch Shopify app
