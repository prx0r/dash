# Snap-to-List + Valuation Engine

*The trust layer between sellers and marketplaces.*

---

## The Product

Three surfaces, one engine:

### 1. Snap-to-List
**Take a photo. We list it everywhere.**

```
User: [photo of vintage lamp]
        ↓
ChatGPT vision identifies: "Anglepoise Type 75 desk lamp, cream, 1990s"
        ↓
BreadUp:
  ├── finds comps (eBay sold, Etsy sold, Discogs)
  ├── calculates price range (P25 / P50 / P75)
  ├── selects optimal marketplace(s)
  ├── generates title, description, tags
  ├── picks best photo angles
  ├── sets price at P50 with "or best offer"
  └── cross-lists to eBay + Etsy + Vinted + Facebook
        ↓
User: [sees listing ready to publish]
  "Anglepoise Type 75 Desk Lamp — Cream — 1990s"
  Price: £45 (P50 of 23 sold comps)
  Expected to sell: 7-14 days
  [Publish] [Adjust Price] [Add to Store]
```

### 2. Valuation Engine
**"What's this worth?"**

```
User: [photo of random thing at car boot]
        ↓
ChatGPT vision: "What am I looking at?"
        ↓
BreadUp:
  ├── identifies item (brand, model, era, condition)
  ├── pulls comps (last 90 days, your country)
  ├── shows distribution (cheapest → median → most expensive)
  ├── calculates confidence (how many comps? how recent?)
  ├── estimates shipping cost
  └── recommends: "Buy at £X or less for 50%+ margin"
        ↓
User: [sees valuation card]
  Item: Anglepoise Type 75 (cream, 1990s)
  Median sold: £48
  Range: £25-£85
  Confidence: HIGH (23 comps, 30 days)
  Buy at: £20 or less (58% margin after fees)
  Time to sell: 7-14 days typical
  Current supply: 4 listed in your area
  [Add to Watchlist] [Create Listing] [Pass]
```

### 3. Cash Flow Forecaster
**"How quickly will this sell?"**

```
User: "I'm thinking of buying 10 of these to flip. What's the cash flow?"
        ↓
BreadUp:
  ├── historical sell-through rate (days to sale)
  ├── current supply (how many listed right now)
  ├── demand trend (is interest rising/falling)
  ├── seasonal pattern (does this sell better in Dec vs July?)
  ├── calculates: days to sell, probability of sale within 30/60/90 days
  └── builds cash flow model
        ↓
User: [sees cash flow card]
  Anglepoise Type 75 — Cash Flow Analysis
  
  Buy 10 @ £20 each = £200 invested
  
  Expected timeline:
  ├── Week 1-2: sell 3-4 (30-40% of stock)
  ├── Week 3-4: sell 2-3 (20-30%)
  ├── Week 5-8: sell 2-3 (20-30%)
  └── Week 8+: sell remaining 1-2 (slow movers)
  
  Expected return: £480 (10 × £48 median)
  After fees (13% eBay): £418
  Net profit: £218 (109% ROI)
  
  Risk: 2 may sell below £35 (15% chance)
  Worst case: £158 profit (79% ROI)
  Best case: £298 profit (149% ROI)
  
  [Buy Stock] [Set Up Listings] [Simulate Different Quantities]
```

---

## The Backtesting MCP

**Every query makes the system smarter.**

```text
QUERY CACHE
│
├── "What's an Anglepoise Type 75 worth?"
│   ├── asked 47 times in last 30 days
│   ├── price trend: +3% (stable)
│   ├── seasonal: sells 2x faster Oct-Dec
│   └── cached response: instant
│
├── "How fast do vintage lamps sell?"
│   ├── median: 12 days
│   ├── P25: 5 days (fast movers)
│   ├── P75: 28 days (slow)
│   └── cached response: instant
│
└── "What's selling well in Bristol right now?"
    ├── top categories: vinyl, furniture, cameras
    ├── demand/price ratio: cameras highest
    └── cached response: instant
```

### The Network Effect

```
Query 1: "What's this lamp worth?"
  → 23 comps found, 12 days median
  → result cached

Query 2: "What about this similar lamp?"
  → 23 comps + 1 new observation from Query 1
  → result cached, slightly more accurate

Query 100: "Vintage lamps in general?"
  → 2,300 observations, seasonal patterns, regional data
  → result very accurate, instant
```

**Every valuation, every listing, every sale feeds back into the system.**

### Backtesting Tool

```text
GET /backtest
  query: "Anglepoise Type 75"
  period: "90d"
  country: "GB"

Response:
{
  "comps": 47,
  "median_price": 48.50,
  "price_trend": "+2.3%",
  "median_days_to_sell": 11,
  "seasonal_peak": "Oct-Dec",
  "current_supply": 12,
  "demand_score": 0.72,
  "recommended_buy_price": 20,
  "expected_roi": 1.09,
  "confidence": 0.89,
  "cached": true,
  "cache_age_hours": 2
}
```

---

## How Pricing Works

### The Pricing Stack

```
COMP DATA (90 days, sold items)
    │
    ├── eBay sold (most data)
    ├── Etsy sold (vintage/handmade)
    ├── Vinted (clothing/accessories)
    ├── Facebook Marketplace (local)
    └── user_sales (our own data)
    │
    ▼
PRICE DISTRIBUTION
    │
    ├── P10 (bottom 10% — distressed/fast sale)
    ├── P25 (below average)
    ├── P50 (median — fair market)
    ├── P75 (above average)
    └── P90 (premium/rare)
    │
    ▼
ADJUSTMENTS
    │
    ├── condition (new/like_new/good/fair/poor)
    ├── completeness (box, manual, accessories)
    ├── rarity (how many available right now)
    ├── demand trend (rising/falling/stable)
    ├── seasonality (time of year)
    ├── location (shipping cost affects net)
    └── platform fees (different per marketplace)
    │
    ▼
RECOMMENDED PRICE
    │
    ├── "Quick sale" (P25, sell in 3-5 days)
    ├── "Fair price" (P50, sell in 7-14 days)
    ├── "Premium" (P75, sell in 14-30 days)
    └── " aspirational" (P90, may not sell)
```

### The Pricing Card

```text
┌─────────────────────────────────────────┐
│ Anglepoise Type 75 — Cream — 1990s      │
├─────────────────────────────────────────┤
│ 47 sold in last 90 days (UK)            │
│                                         │
│ £25 ──── £38 ──── £48 ──── £65 ──── £85│
│ P10      P25      P50      P75      P90 │
│                   ▲                     │
│              RECOMMENDED                │
│                                         │
│ Your condition: Good                    │
│ Adjusted recommendation: £42-52         │
│                                         │
│ If you buy at £20:                      │
│   Quick sale (£38): £13 profit (65%)    │
│   Fair price (£48): £22 profit (110%)   │
│   Premium (£65): £37 profit (185%)      │
│                                         │
│ Current supply: 4 listed                │
│ Demand trend: Stable                    │
│ Typical sell time: 7-14 days            │
│                                         │
│ [List at £48] [List at £42] [Custom]    │
└─────────────────────────────────────────┘
```

---

## The Car Boot Scout

**Point your phone at a table. Get instant intelligence.**

```
User: [takes photo of car boot table]
        ↓
ChatGPT vision: segments objects
  "I see: 1 Anglepoise lamp, 3 vinyl records, 
   1 ceramic vase, 2 books, 1 brass candlestick"
        ↓
BreadUp evaluates each:
  ├── Lamp: £48 median, buy at £20 (GOOD)
  ├── Record 1: £12 median, buy at £5 (OK)
  ├── Record 2: £8 median, buy at £3 (OK)
  ├── Record 3: £2 median, skip (BAD)
  ├── Vase: unknown maker, £15 median, risky
  ├── Books: £1 each, not worth listing
  └── Candlestick: £22 median, buy at £8 (GOOD)
        ↓
User: [sees summary card]
  Car Boot Scout — 7 items scanned
  
  BUY:
  ├── Anglepoise lamp @ £20 → expected £48 (140% ROI)
  └── Brass candlestick @ £8 → expected £22 (175% ROI)
  
  MAYBE:
  ├── Vinyl record 1 @ £5 → expected £12 (60% ROI)
  └── Vinyl record 2 @ £3 → expected £8 (80% ROI)
  
  PASS:
  ├── Record 3 (£2 median, not worth listing)
  ├── Books (£1 each, shipping kills margin)
  └── Vase (unknown maker, uncertain comps)
  
  Suggested bundle: lamp + candlestick = £28
  Expected return: £70 (150% ROI)
  
  [Add to Cart] [Take Photos] [Create Listings]
```

---

## The Listing Engine

**One photo → optimised listing on every platform.**

```
PHOTO + ITEM IDENTIFICATION
    │
    ▼
LISTING GENERATOR
    │
    ├── Title (SEO-optimised per platform)
    │   eBay: "Anglepoise Type 75 Desk Lamp Cream 1990s - Excellent Condition"
    │   Etsy: "Vintage Anglepoise Desk Lamp - Cream - Mid-Century Modern"
    │   Vinted: "Anglepoise lamp cream"
    │
    ├── Description (detailed, honest, includes measurements)
    │   "Original Anglepoise Type 75 desk lamp in cream. 
    │    Made in UK, circa 1990s. Fully functional...
    │    Height: 45cm, Base: 17cm diameter..."
    │
    ├── Tags (per platform best practices)
    │
    ├── Photos (cleaned, cropped, supplemental generated)
    │
    ├── Price (from pricing engine)
    │
    ├── Shipping (calculated from location + weight)
    │
    └── Category (mapped per platform taxonomy)
    │
    ▼
CROSS-LIST
    │
    ├── eBay (highest fees, highest traffic)
    ├── Etsy (best for vintage, lower fees)
    ├── Vinted (clothing/accessories, 0% seller fees)
    ├── Facebook Marketplace (local, 0% fees)
    └── Shopify (if they have a store)
    │
    ▼
INVENTORY SYNC
    │
    ├── Track per-channel availability
    ├── When sold on one → delist from others
    └── Record actual sale price → feeds back into pricing
```

---

## The Flow

```
PHOTO → IDENTIFY → VALUE → PRICE → LIST → TRACK → LEARN
  │        │         │       │       │       │        │
  │     ChatGPT   BreadUp  BreadUp  BreadUp  BreadUp  BreadUp
  │    vision     comps    pricing  listing  inventory backtest
  │
  └── EVERY STEP FEEDS BACK INTO THE SYSTEM
```

**The loop:**
1. User takes photo
2. We identify and value
3. User lists (or we list for them)
4. Item sells (or doesn't)
5. We learn: "This type of item took X days, sold for Y% of asking"
6. Next user gets better data

**At scale:** we have the best pricing data in the UK because every transaction teaches us something.

---

## Revenue

| Surface | Price | Model |
|---------|-------|-------|
| **Snap-to-list** | £0.50/listing | Per listing (or free with subscription) |
| **Valuation** | £0.10/query | Pay per valuation (or 5 free/day) |
| **Car boot scout** | £1/session | Per scan session |
| **Cash flow forecast** | £0.50/analysis | Per analysis |
| **Full subscription** | £10/mo | Unlimited listings + valuations + forecasts |
| **x402 (machine)** | £0.01/call | Agent-to-agent |

**The network effect:** every query makes the system smarter. Early users get cheap access. Later users pay more for better data. The data moat grows with every transaction.

---

## Why This Wins

1. **Pricing accuracy** — we have better data than any individual seller
2. **Speed** — photo to listing in 60 seconds
3. **Multi-channel** — one photo, every marketplace
4. **Learning** — every transaction improves the system
5. **Trust** — we're not guessing, we're calculating from real sales
6. **Network effect** — more users = more data = better pricing = more users

**The endgame:** everyone lists through us because we price better than they can. We become the valuation layer for all of UK secondhand commerce.
