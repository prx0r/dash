# Snap-to-List Deep Design

*The consumer wedge that works from both sides of the transaction.*

---

## The Core Insight

Start one step earlier than every other resale tool.

Not: "What do you have and what's it worth?"
But: **"Take a photo."**

```
PHOTO
  ↓
canonical identity
  ↓
condition estimate
  ↓
recent sold comps
  ↓
active competition
  ↓
local supply
  ↓
sell-through / time-to-sale model
  ↓
recommended pricing curve
```

---

## The Pricing Interface

Not one fake "market value" number. A curve:

> **Estimated fair value: £95–£120**
> Likely sale within 7 days: £79
> Likely sale within 14 days: £91
> Likely sale within 30 days: £99
> Max-value strategy: list at £125, expected sale ~42 days
> Current local competition: 4 similar items within 15 miles
> Recent realized range: £82–£114

Then:

> **How quickly do you want it gone?**

After the user chooses "14 days":

- Title
- Description
- Item specifics
- Condition notes
- Price
- Shipping strategy
- Marketplace selection
- Crop/clean listing images
- Supplemental AI lifestyle images (clearly distinguished from condition photos)
- eBay listing
- Facebook listing
- Etsy if appropriate
- Vinted if appropriate
- Shopify inventory item

**One photograph becomes a sale workflow.**

---

## The Same Engine as Buyer's Scanner

At a car boot:

> 📷 "£8. Buy?"

BreadUp:

> Likely 1980s Technics SL-Q2.
> Estimated resale: £85–£120 depending on cartridge/condition.
> Similar units have historically taken ~18 days to sell at £95.
> Expected fees/transport: £19.
> Expected net profit at £8 purchase: £68–£93.
> Estimated annualized cash-on-cash return is excellent if functional.
> Check these three things before buying…

Much more useful than:

> "It's worth £100."

Because **value without liquidity is incomplete.**

---

## The Valuation Formula

$$V = f(P, T, C, L, F, R)$$

Where:
- **P** = expected sale price
- **T** = expected time to sale
- **C** = condition
- **L** = current competing inventory/liquidity
- **F** = transaction/fulfilment costs
- **R** = uncertainty/risk

**For BreadUp, cashflow is the actual product.**

---

## The Backtesting MCP

Generic shared service, not separate statistics per scanner:

```python
backtest.query(
    identity="Technics SL-Q2",
    geography="UK",
    condition="used_good",
    channels=["ebay", "facebook"],
    horizon="2y"
)
```

Returns:

```json
{
  "historical": {
    "median_exit": 96,
    "p25_exit": 78,
    "p75_exit": 118,
    "median_days_to_sale": 21,
    "sell_through_30d": 0.63
  },
  "recent": {
    "window": "14d",
    "median_exit": 108,
    "median_days_to_sale": 13,
    "sell_through": 0.78
  },
  "current_market": {
    "active_count": 37,
    "local_count": 4,
    "median_ask": 124
  }
}
```

Then any ChatGPT conversation can use it.

**Economic memory as infrastructure.**

---

## Caching Every Resolved Query

This is where the flywheel appears.

Initially: expensive research (identity resolution, comp gathering, condition classification, liquidity estimation).

After first query:

```
ENTITY
Technics SL-Q2
     │
     ├── identity aliases
     ├── visual fingerprints
     ├── marketplace search patterns
     ├── historical observations
     ├── active observations
     ├── price distribution
     ├── days-to-sale distribution
     └── resolved user outcomes
```

Next query becomes much cheaper.

The cache isn't static. Every scanner observation updates it.

```
long-term prior
        +
recent observations
        +
current active inventory
        +
user-realized sales
```

ChatGPT answers:

> Historically these sell in roughly 24 days around £90–£110, but over the last two weeks sell-through has accelerated and observed sale values are closer to £115. There are currently only two comparable units listed within 20 miles.

**Useful intelligence.**

---

## User Sales Are the Gold-Standard Dataset

Marketplace asking prices are garbage compared with real realized outcomes.

BreadUp maintains evidence classes:

```
active_ask
observed_ask
listing_disappeared
platform_sold_evidence
dealer_offer
user_purchase
user_realized_sale
```

Confidence hierarchy:

```
BreadUp user realized sale     ██████████
verified marketplace sale      ████████
dealer offer                   ██████
listing disappeared            ████
active ask                     ██
```

Over time BreadUp develops its own **ground-truth transaction tape**.

That's one of the strongest moats available.

---

## Two-Sided Marketplace

Not exploiting information asymmetry.

**Reducing search/pricing friction on both sides.**

Sellers use the same intelligence:

> photograph item → receive fair price → optimized listing

Choose:

**Quick sale**
£72 / ~3 days

**Balanced**
£91 / ~14 days

**Maximize value**
£115 / ~45 days

**That's fantastic UX.**

---

## Price a Whole Room

Scales beyond individual items.

Someone moving house:

> 📷 video of garage

BreadUp:

```
23 recognized saleable objects
estimated gross resale value: £1,940
expected net after fees: £1,530
```

Then:

> Sell everything over £30 individually; bundle the bottom 11 items into three lots.

Applications:
- house clearances
- inheritance
- storage units
- charity shops
- estate sales
- car boots
- liquidation stock
- business closure
- hotel/office furniture
- returned goods

---

## Stores Become Inventory Strategies

Connects to the "World" idea.

Someone creates:

> **My Mid-Century Store World**

The store has a buying function:

```python
def accept(item):
    return (
        item.aesthetic_similarity > 0.82
        and item.expected_profit > 40
        and item.expected_days_to_sale < 45
        and item.purchase_price < 0.35 * item.expected_exit
    )
```

At a car boot, photograph things. BreadUp returns:

> **BUY — strong fit for your store.**

or:

> PASS — profitable, but doesn't fit your current brand/audience.

BreadUp evaluates:
1. absolute market value
2. economic attractiveness
3. fit with this specific business

**That's very powerful.**

---

## General Backtesting as Platform Primitive

Shared API:

```
observe()
identify()
comps()
history()
liquidity()
backtest()
simulate()
evaluate()
```

Scanners merely compose them:

```python
class VintageLampScanner:
    def scan(self):
        candidates = marketplace.search(...)
        for candidate in candidates:
            identity = identify(candidate)
            stats = backtest(identity)
            economics = evaluate(candidate, stats)
            if economics.expected_roi > 1.5:
                emit(opportunity)
```

A user-created World inherits all the hard economic machinery for free.

They provide specialist knowledge. BreadUp provides:
- marketplace transport
- identity framework
- observations
- historical engine
- statistics
- simulation
- P&L
- execution.

**Strong platform split.**

---

## Statistical Honesty

Don't say:

> "These take 17 days to sell."

unless you genuinely observe sales accurately.

With marketplaces where sold dates aren't exposed, estimate from:
- first-seen timestamp
- disappearance
- relisting behavior
- price changes
- eventual confirmed sale
- user-realized outcomes

Retain evidence quality:

> Estimated median listing lifetime: 17–24 days (medium confidence).

Versus:

> Verified BreadUp transactions: median 15 days.

**Provenance is essential. Otherwise the system becomes sophisticated-looking hallucination.**

---

## The First-Run Interaction

Forget onboarding screens.

Open BreadUp in ChatGPT:

> **Take a picture of something near you.**

User photographs a random object.

BreadUp:

> That's probably a Bose Wave Music System III. In this condition I'd estimate £70–£95. If you wanted it gone this week, I'd start around £75. Want me to create listings?

Immediately demonstrates the product.

Then:

> Or take me to a car boot and I'll tell you what to buy.

**Unusually legible consumer proposition.**

---

## The Game Evolves

Not simulated anymore.

Your phone becomes an **economic augmented-reality layer over the physical world**:

> 📷 object → identity → value → liquidity → cashflow → BUY/PASS

The store/World you've built determines what opportunities are relevant to you.

Much closer to the eventual BreadUp than the original gamified-business dashboard.

---

## Summary

```
PHOTO → IDENTIFY → VALUE → LIQUIDITY → CASHFLOW → ACTION
  │        │         │         │           │          │
  │     ChatGPT   BreadUp   BreadUp     BreadUp    BreadUp
  │    vision     comps     backtest    simulate   list/buy
  │
  └── EVERY STEP FEEDS BACK INTO THE SYSTEM
      EVERY QUERY MAKES THE NEXT ONE SMARTER
      EVERY SALE IMPROVES THE PRICING ENGINE
```

**The moat:** we have the best pricing data because every transaction teaches us something. No one else has this feedback loop.

**The endgame:** everyone values things through us because we price better than they can. The data moat grows with every query, every listing, every sale.
