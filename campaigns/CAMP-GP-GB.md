# CAMP-GP-GB — Total-triage operations layer for GP practices

Status: DISTILLED | Template: tpl-gp-gb | Teardown: td-gp-gb | Pattern: triage-led

## 1. Market overview
- Health & social work: 5.09M jobs, biggest UK sector, still growing (+61k/quarter, ONS Aug 2026).
- Accurx in 98% of GP practices; total triage is the operating model; 98% of requests done in a day under it.
- 8am rush + walk-ins + non-digital patients = the demand spike nothing staffs for.

## 2. Acquisition
- Practices directly (ICB introductions, PCN networks). Buyer: practice manager + partners.
- Pilot wedge: admin-resolution rate — resolve without appointment, prove with inbox data.

## 3. Offer catalog
- Total-triage inbox operations: all channels → structured requests, one queue.
- Reception Flow staffing (8am cover + overflow).
- Recall programmes (screening/QOF/immunisations) as managed service.
- Repeat prescription prep (clinician signs, agent prepares).

## 4. Unit economics
- Price per 1,000 patients/month (TBD: anchor vs Accurx-equivalent spend).
- Cost: triage labour saved (reception hours), avoided locum cover, QOF attainment lift.
- Margin math needs one pilot's inbox data — TBD after pilot 1.

## 5. Supply/operations strategy
- Read/write integration with EMIS/SystmOne/Vision (never a copy).
- HARD BOUNDARY: agent does admin + navigation only; clinicians triage medical. Policy-enforced, not guideline-hoped (GMC Good Medical Practice, duty of candour HSCA Reg 20).

## 6. Distribution strategy
- ICB/PCN channel partnerships; Accurx-adjacent positioning (we operate the inbox they provide).
- Case study per pilot: admin-resolution % + demand curves.

## 7. Listing structure
- NHS-adjacent procurement routes; practice-manager peer referrals.

## 8. Landing/conversion structure
- Pilot offer: 30-day inbox operations on one practice, measured on admin-resolution rate + 8am answer rate.

## 9. Success metrics + kill rules
- Admin-resolution %, 8am answer rate, recall attainment delta, zero clinical-boundary breaches (any breach = kill + review).
- Kill: practice won't grant EPR integration → no product without the record.

## 10. Next steps
- M: triage taxonomy mapping; recall cohort importers; Accurx-shape inbox spec.
- H: first pilot practice (manager + partner sign-off), EPR integration approval, clinical safety boundary sign-off.

## Evidence bindings
- 5.09M jobs / +61k growth → ONS Aug 2026.
- Accurx 98% / 98%-in-a-day / Reception Flow / Bell → Accurx verified 2026.
- SVGA/HSCA Regs → legislation pack (verified).

## 12-gate states
G1 PASS | G2 PASS (8am demand) | G3 PASS (triage structuring) | G4 PASS (admin vs clinical split mapped) | G5 PASS (reception capacity exists) | G6 PASS (no one operates the inbox as a service) | G7 PASS (no regulated-activity block on admin handling) | G8 UNKNOWN (unit economics need pilot) | G9 UNKNOWN (one pilot LOI needed) | G10 PASS | G11 PASS | G12 UNKNOWN
Verdict: BLOCKED (economics + 1 LOI — both closable, none fatal)
