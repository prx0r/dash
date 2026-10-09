# PEER REVIEW — fact-check of all session conclusions

Method: every load-bearing number re-checked against primary sources
(ONS/Nomis live APIs, legislation.gov.uk, gov.uk guidance, vendor pricing
pages, Big4 press/research pages). Verdicts: CONFIRMED / CORRECTED /
REJECTED / CARRIED (verified in an earlier session turn, not re-checked
this turn — flagged, never upgraded silently).

## 1. Govt & labour data

| Claim | Verdict | Evidence |
|---|---|---|
| Skills England 685k care demand (281k+404k), +199k care workers | CONFIRMED verbatim | gov.uk SNA health & social care, Jun 2026 |
| Construction 493k + 595k ≈ 1.088M | CONFIRMED verbatim (we said "~1M" — actual 1,088,000) | gov.uk SNA construction |
| 1.8M jobs +24% by 2035 | CONFIRMED | Skills England annual report 2026 |
| ONS AI use 12→35%, 58% info/comms vs 13% construction | CONFIRMED (ONS release 20 Jul 2026 + secondary) | ons.gov.uk/releases/aiinukbusinesses |
| Call centres -19%, telephone sales -23% | CONFIRMED | British Progress Apr 2026 |
| Customer service -23%, admin -22% vacancy falls | CONFIRMED (correlation, not causation — authors say so) | BoE Bank Underground Aug 2026 |
| Programming 16-24 down 44% | CONFIRMED with causality caveat (gov.uk assessment itself warns against attribution) | gov.uk AI labour assessment Jan 2026 |
| Hospitality = 53% of job losses despite low exposure | CONFIRMED — kept as the confound that disciplines our displacement claims | same |
| DSIT 16%, micro-38% usage | CARRIED (prior turn, not re-checked) | — |
| Youth apprenticeships -40% | CARRIED (prior turn, not re-checked) | — |
| ONS jobs snapshot levels (Q 5090 etc.) | CARRIED with caveat: bulletin-derived (JOBS02 via release), NOT API-pulled — ONS beta API has no VACS02 endpoint (verified: search returns nothing) | — |

## 2. Stack pricing & fees

| Claim | Verdict | Evidence |
|---|---|---|
| Booksy £40 + £5/user + 30% Boost (min £5) + 1.29%+20p | CONFIRMED to official pricing page + 2 independents | biz.booksy.com, barberinsights, setora |
| Fresha £14.95 / £9.95 + 20% new-client (min £4) | CONFIRMED | fresha.com via comparisons Mar 2026 |
| Tradify/Jobber positioning | CONFIRMED directionally; Jobber USD tiers verified (official pricing page) | getjobber.com, buyersprint Jun 2026 |
| eBay business 9.9-14.9% + £0.30/0.40 + 0.35% + VAT (~16-17% effective); private 0% since Oct 2024; Vinted 0% seller-side | CONFIRMED (official fee page + Apr/Aug 2026 calculators) | pages.ebay.co.uk, payoutmath, ecomli |
| No-shows 76%/8%/£3,621; deposits -57%, -72% late cancels; holds -16% | CONFIRMED to primaries | ResDiary 2024 report, OpenTable Oct 2025 |
| Delivery £32,760/yr gap | RECOMPUTED ✓ (100×22.50×0.28×52) | arithmetic, inputs verified |
| PwC GDP 1.2%, AI £2bn; Deloitte 9/10 + readability quote | CONFIRMED official; Deloitte bonus: ChatGPT referrals already 15-20% for some retailers; half expect journey collapse by 2027 | pwc.co.uk press release Dec 2025, deloitte.com Feb 2026 |

## 3. Legislation

All 11 `verified-2026` pack entries re-confirmed to legislation.gov.uk /
gov.uk / HSE sources this turn (GSIUR 1998 reg 3 incl. employer duties;
F-Gas incl. company-level cert + EA/SEPA enforcement — stronger than framed).
Corrections already applied: TPO per-route windows, chainsaw non-licence,
funeral no-licensing-regime, MLR bookkeeper duty added.
Open: children-DBS exact citation (rate-limited; same Act as verified adult
regime); LOLER/PUWER/Part-P/VMR/GDPR items remain `well-established`.

## 4. APIs & tooling

| Claim | Verdict |
|---|---|
| ONS beta API keyless, catalogue + dataset metadata | CONFIRMED live (200s this turn) |
| Nomis keyless data | CONFIRMED live — with CORRECTION: geography 2092957699 is England JSA, not UK; client relabelled, test enforces honest scope |
| FHRS keyless v2 | CONFIRMED live (200) |
| police.uk keyless | CONFIRMED live (200) |
| ONS beta lacks VACS02 (bulletin XLSX only) | LIMITATION recorded — snapshot numbers are bulletin-derived |
| ons-mcp live 401 / pipeworx 404 | CONFIRMED again; raw-API decision stands |

## 5. Internal consistency

24/24/24 templates/teardowns/campaigns with perfect ID mapping; BQ agrees
(24 TPL_ nodes); all 24 campaign verdicts BLOCKED with resolvable reasons,
zero self-promotions, zero FAILs. `test_no_invented_numbers` caught 2 real
gaps (fixed in files).

## Positives

- Stat basis discipline held: the one `template-analysis` stat ("majority of
  calls") never wore a fake number.
- Corrections went into source files, never into tests.
- Gate honesty is machine-checked across all 24 campaigns.
- BQ ↔ disk agreement is total.

## Round 2 verdicts (legit pass)

| Claim | Verdict |
|---|---|
| Children teaching = regulated activity (SVGA Sch 4 Pt 1, weekly+/4-in-30 unsupervised) + DfE supervision nuance | CONFIRMED to legislation.gov.uk + statutory guidance; tutor gate holds, supervision exception noted |
| LOLER reg 9 (6-monthly persons) / PUWER regs 4,8,9 (suitability, info, training) | CONFIRMED to legislation.gov.uk + HSE L113 |
| Part P + competent-person schemes (Certsure/NICEIC/NAPIT) + third-party certifier route | CONFIRMED to planningportal + gov.uk scheme list |
| VMR 5yr retention / CD Schedule-2 register 2yr minimum, per-product, ink, witnessed destruction | CONFIRMED to legislation.gov.uk + gov.uk guidance + VMD inspector blog Feb 2025 |
| DSIT 16% + micro nuance | CORRECTED: 38% is staff-share *within* micro firms, not firm adoption (14%). Gov.uk DSIT Jan 2026 |
| Youth apprenticeships -40% | CONFIRMED (BBC Dec 2025, minister quote) — promoted from CARRIED |
| Accurx 98% practices | CONFIRMED with vendor-source caveat (their site); Reception Flow + NHS App integration confirmed via help centre |
| MTD £50k/£30k/£20k + quarterly + points | CONFIRMED to gov.uk (incl. 2028 £20k tier + grace rules) |
| Tutorful closed + unpublished % (~35% third-party); MyTutor undisclosed; First Tutors closed permanently 2026 | CONFIRMED (official closed page + TutorLab/Tutorperch checks); First Tutors closure added to tutor template |
| HaloPSA £69/agent, 5-min, £3.2k sub-5 onboarding | CORRECTED from ~$65 (template updated) |
| Gridwise "1M+ users" | CORRECTED to 150k+ monthly drivers (LinkedIn 2026) — vendor marketing retired |
| Electricity at Work 1989 (standalone) | NOT separately verified — stays `well-established` inside LEG-ELECTRICAL |
| Pack promotions | LEG-SVGA-CHILD, LEG-LOLER-CHAINSAW, LEG-VETMEDS → verified-2026 with source URLs |
| Nomis geography | CORRECTED: client returned England JSA labeled UK — relabeled + regression test |
| ONS beta lacks VACS02 | LIMITATION recorded (bulletin XLSX only) |
| Heartbeat | First run live: Booksy £40, Fresha £14.95, HaloPSA £69 as TOOL_ observations |
| MERGE-vs-buffer duplicates | NEW FINDING (self-caught): 17 dup nodes from reseed-in-window; cleaned; governance rule 6 added |

## Negatives (updated)

- Nomis UK mislabel shipped in the client (fixed + regression-tested).
- TPO/chainsaw/funeral-licensing overstatements shipped in templates
  (fixed + pack states corrections explicitly).
- Density multiplier in opportunity ranking is inert (uniform 3p/3l) —
  ranking currently equals vacancy weight; documented, not hidden.
- ~10 figures ride on CARRIED (prior-turn) verification, listed above.
- Live BQ still contains the demo REJECTED weakpoint row (intentional,
  demonstrates the demotion path; documented).
