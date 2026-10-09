# BreadUp Payment Architecture

*Settlement rails as infrastructure, not ideology.*

---

## Core Principle

Payment is abstracted. BreadUp doesn't care about the rail. It cares about:
- **cost** — which rail is cheapest
- **privacy** — which rail preserves confidentiality
- **counterparty support** — which rail the other side accepts
- **settlement certainty** — which rail settles fastest
- **user policy** — what the user configured

---

## The Settlement Router

```
PAYMENT / SETTLEMENT
├── gbp_card (Stripe, Shopify Payments)
├── gbp_bank (BACS, Faster Payments)
├── eur_card
├── eur_sepa
├── usdc (Stablecoin, fast settlement)
├── usdt (Stablecoin)
├── btc (Bitcoin, slower but universal)
├── xmr (Monero, privacy-preserving)
├── x402 (Machine-to-machine micropayments)
└── other_rails (extensible)
```

---

## User Configuration

```yaml
payments:
  accept:
    - gbp_card
    - usdc
    - xmr

  preferred:
    supplier_payments: usdc
    private_marketplace: xmr
    customer_payments: gbp_card
    scanner_subscriptions: x402

  constraints:
    max_xmr_per_month: 500
    min_usdc_settlement: 10
    never_btc: true
```

---

## Use Cases

| Use Case | Best Rail | Why |
|----------|-----------|-----|
| Etsy/Shopify sales | gbp_card | Customer expects it |
| Scanner subscriptions | x402 | Machine-to-machine, micropayments |
| Buying inventory from crypto seller | usdc or xmr | Counterparty preference |
| Cross-border supplier payment | usdc | Fast, low fees, no FX |
| Privacy-preserving purchase | xmr | No transaction trace |
| Agent-to-agent commerce | x402 | Programmable, instant |
| Paying influencers/agencies | gbp_bank | Standard business payment |
| BreadPack purchases | gbp_card or usdc | User preference |

---

## XMRbot as BreadUp Adapter

```
ChatGPT
   ↓
BreadUp opportunity
   ↓
policy/permission check
   ↓
settlement router
   ├── Shopify/card
   ├── bank
   ├── stablecoin/x402
   └── XMRbot
          ↓
       XMR commerce
```

XMRbot isn't a separate universe. It's a settlement adapter inside BreadUp.

User can say:
- "Only show me suppliers who take XMR"
- "Spend up to £100 equivalent, but use XMR if available"
- "Sell this scanner for £3/month or equivalent XMR"

---

## Accounting Ledger

**Ledger denomination ≠ settlement asset.**

A shop might receive XMR, USDC, and GBP. BreadUp produces one coherent P&L in the user's chosen reporting currency.

```python
@dataclass
class Transaction:
    # What happened
    item_id: str
    quantity: int
    gross_price: float
    gross_currency: str  # GBP, EUR, USD
    
    # Settlement
    settlement_rail: str  # gbp_card, usdc, xmr, etc.
    settlement_amount: float
    settlement_currency: str
    settlement_fee: float
    
    # Exchange rate evidence
    exchange_rate: float  # rail_currency → ledger_currency
    rate_source: str      # "coinbase", "kraken", "ecb"
    rate_timestamp: datetime
    
    # Ledger entry (always in user's reporting currency)
    ledger_amount: float
    ledger_currency: str  # User's choice: GBP, USD, EUR
```

---

## x402 for Machine Payments

```text
GET /scanner/cult-vinyl/opportunities
402 Payment Required
X-Pay: usdc
Amount: 0.01
```

Machine agents pay per query. No human in the loop.

Supported rails for x402:
- USDC (fastest, cheapest)
- BTC ( Lightning)
- x402 native protocol

---

## Moltwork Connection

Moltwork becomes the execution layer for autonomous agent commerce:

```
BreadUp identifies opportunity
   ↓
Moltwork agent evaluates
   ↓
Policy check (budget, risk, approval)
   ↓
Settlement (via BreadUp router)
   ↓
Fulfillment (shipping, tracking)
   ↓
Reputation (both parties)
```

---

## Design Constraints

1. **Ledger is denomination-agnostic** — always produces coherent P&L in user's currency
2. **Exchange rates are evidence** — recorded at transaction time with source
3. **Settlement is pluggable** — add new rails without changing accounting
4. **User policy is supreme** — never spend outside configured constraints
5. **Privacy is opt-in** — XMR for those who want it, not forced on everyone
6. **x402 is invisible to humans** — machine-to-machine, no UI needed

---

## Revenue from Payment Layer

| Source | Fee | Notes |
|--------|-----|-------|
| Card processing | 2.9% + £0.25 | Via Stripe/Shopify |
| x402 micropayments | 1% | Machine transactions |
| Crypto conversion | 0.5% | FX spread |
| Escrow | 1% | Agent-to-agent deals |
| Settlement | £0.10 | Per transaction |

**Total payment revenue: ~3-5% of GMV flowing through BreadUp.**
