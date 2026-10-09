#!/usr/bin/env python3
"""Load structured data into new BQ tables."""
import sys
import re
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kernel.bigquery.connect import connect

client = connect()
project = client.project
dataset = "drop"


def load_pain_points():
    """Parse PAIN_POINT_REGISTRY.md into pain_points rows."""
    md_path = Path("/root/PAIN_POINT_REGISTRY.md")
    text = md_path.read_text()
    rows = []
    current_section = ""

    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("## SECTION"):
            m = re.match(r"## SECTION \d+: (.+)", line)
            if m:
                current_section = m.group(1).lower().replace(" / ", "_").replace(" ", "_")
            i += 1
            continue

        if line.startswith("- **Pain:**"):
            pain_name = line.split("- **Pain:**")[1].strip()
            block_fields = {}
            i += 1
            while i < len(lines) and lines[i].strip().startswith("- **"):
                field_line = lines[i].strip()
                m = re.match(r"- \*\*(.+?):\*\*\s*(.*)", field_line)
                if m:
                    key = m.group(1).lower().replace(" ", "_").replace("£", "gbp")
                    val = m.group(2).strip()
                    block_fields[key] = val
                i += 1

            # Find pain_id
            pain_id = None
            for lookback in range(max(0, i-12), i):
                pid_m = re.search(r'\*\*(\w{2}-\d+)\*\*', lines[lookback])
                if pid_m:
                    pain_id = pid_m.group(1)
                    break
            if not pain_id:
                pain_id = f"PP-{len(rows)+1:03d}"

            # Parse autonomy
            autonomy = 3
            am = re.search(r'(\d)', block_fields.get("agent_autonomy", ""))
            if am:
                autonomy = int(am.group(1))
            autonomy_labels = {1: "advisory", 2: "assist", 3: "auto+approve",
                             4: "auto+notify", 5: "autonomous"}

            # Parse industries
            industries_str = block_fields.get("industries", "")
            industries = [s.strip().strip('"').strip("'")
                         for s in re.split(r',\s*', industries_str)
                         if s.strip() and len(s.strip()) > 1]

            # Parse impact
            impact_gbp = None
            impact_str = block_fields.get("annual_gbp_impact", block_fields.get("annual_impact_gbp", ""))
            if impact_str:
                nums = re.findall(r'[\d,]+(?:\.\d+)?', impact_str.replace("£", "").replace(",", ""))
                if nums:
                    try:
                        impact_gbp = float(nums[0])
                        if len(nums) > 1:
                            impact_gbp = (impact_gbp + float(nums[1])) / 2
                    except ValueError:
                        pass

            rows.append({
                "pain_id": pain_id,
                "pain_name": pain_name[:200],
                "pain_category": current_section or "unknown",
                "pain_statement": block_fields.get("pain", pain_name)[:500],
                "exact_statistic": block_fields.get("stat", None),
                "stat_source": block_fields.get("source", None),
                "stat_basis": block_fields.get("source", None),
                "annual_impact_gbp": impact_gbp,
                "impact_sample": block_fields.get("annual_gbp_impact", block_fields.get("annual_£_impact", None)),
                "impact_period": None,
                "mechanism": block_fields.get("mechanism", None),
                "fix_id": None,
                "agent_autonomy": autonomy,
                "autonomy_label": autonomy_labels.get(autonomy, "unknown"),
                "agent_action_example": block_fields.get("agent_action", None),
                "industries": industries,
                "vertical_count": len(industries),
                "source_file": str(md_path),
                "verification": "VERIFIED" if block_fields.get("source") == "verified-2026" else "PROPOSED",
            })

    # Insert
    if rows:
        errors = client.insert_rows_json(f"{project}.{dataset}.pain_points", rows)
        if errors:
            print(f"  Pain points insert errors: {errors[:3]}")
        else:
            print(f"  Pain points: {len(rows)} rows loaded")
    return len(rows)


def load_vertical_rankings():
    """Parse UK_BUSINESS_RANKING.md into vertical_rankings rows."""
    md_path = Path("/root/UK_BUSINESS_RANKING.md")
    text = md_path.read_text()
    rows = []
    lines = text.split("\n")

    current_vertical = None
    current_tier = 0
    vertical_data = {}

    for i, line in enumerate(lines):
        line = line.strip()

        if line.startswith("## TIER"):
            m = re.match(r"## TIER (\d+)", line)
            if m:
                current_tier = int(m.group(1))

        if line.startswith("### ") and not line.startswith("### Scoring"):
            name = line[4:].strip()
            m = re.match(r'(\d+)\.\s+(.+)', name)
            if m:
                current_vertical = m.group(2).lower().strip()
                vertical_data[current_vertical] = {"tier": current_tier, "dims": {}}

        if current_vertical and "**Score:**" in line:
            m = re.search(r'(\d+\.\d+)/5', line)
            if m:
                vertical_data[current_vertical]["score"] = float(m.group(1))

        if current_vertical and "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                dim = parts[0].lower().replace(" ", "_").replace("'", "")
                try:
                    score = int(parts[1])
                    if 1 <= score <= 5:
                        vertical_data[current_vertical]["dims"][dim] = score
                except (ValueError, IndexError):
                    pass

    # Build rows
    first_caps = {
        "electrician": ("Voice agent (missed-call recovery)", "autonomous"),
        "beauty": ("AI receptionist", "autonomous"),
        "barber": ("No-show deposit system", "autonomous"),
        "restaurant": ("Channel P&L tracker", "autonomous"),
        "window_cleaner": ("Round ledger + DD chase", "autonomous"),
        "cleaning": ("Win-back engine", "autonomous"),
        "garage": ("MOT reminder campaign", "autonomous"),
        "petcare": ("Direct booking migration", "autonomous"),
        "tutor": ("Exam countdown + package tracker", "auto+notify"),
        "msp": ("Triage prioritizer", "auto+notify"),
        "hotel": ("Direct recovery engine", "auto+notify"),
        "bookkeeping": ("MTD quarter tracker", "auto+approve"),
        "builder": ("Variation tracker", "auto+approve"),
        "medspa": ("Consult follow-up", "auto+approve"),
        "care": ("CQC evidence pack", "auto+approve"),
        "hvac": ("F-Gas tracker", "auto+approve"),
        "funeral": ("First call capture", "assist"),
        "dropship": ("Ad kill-switch", "auto+notify"),
        "gig_driver": ("Tax sweeper", "autonomous"),
        "retail": ("AI readability feed", "auto+notify"),
        "tree_surgeon": ("Cert ladder tracker", "auto+approve"),
        "vet": ("CD register logger", "auto+approve"),
        "gp_surgery": ("Triage navigator", "auto+approve"),
    }

    for vert, data in vertical_data.items():
        if vert not in data or not data.get("score"):
            continue
        dims = data.get("dims", {})
        cap = first_caps.get(vert, ("Unknown", "unknown"))
        rows.append({
            "ranking_id": "chatgpt-native-2026-09",
            "vertical": vert,
            "template_id": f"tpl-{vert.replace('_', '-')}-gb",
            "overall_score": data["score"],
            "chat_interface_fit": dims.get("chat_interface_fit", dims.get("chat", 3)),
            "pain_severity": dims.get("pain_severity", dims.get("pain", 3)),
            "capability_atomicity": dims.get("capability_atomicity", dims.get("capability", 3)),
            "discovery_potential": dims.get("discovery_potential", dims.get("discovery", 3)),
            "marketplace_dependency": dims.get("marketplace_dependency", dims.get("marketplace", 3)),
            "compliance_ceiling": dims.get("compliance_ceiling", dims.get("compliance", 3)),
            "first_capability": cap[0],
            "first_capability_type": cap[1],
            "tier": data["tier"],
            "pain_point_count": 3,
            "total_annual_impact_gbp": None,
            "source_file": str(md_path),
        })

    if rows:
        errors = client.insert_rows_json(f"{project}.{dataset}.vertical_rankings", rows)
        if errors:
            print(f"  Vertical rankings insert errors: {errors[:3]}")
        else:
            print(f"  Vertical rankings: {len(rows)} rows loaded")
    return len(rows)


def load_capabilities():
    """Load the 10 core capabilities."""
    capabilities = [
        {"capability_id": "voice-agent", "capability_name": "Voice Agent (Missed-Call Recovery)",
         "description": "Answers calls when owner is on the tools. Takes message, books callback via SMS.",
         "pain_points_served": ["MI-01", "MI-02", "MI-03", "MI-04", "MI-06"],
         "industries_served": ["electrician", "builder", "hvac", "garage", "funeral", "restaurant"],
         "industry_count": 6, "autonomy_level": 5, "implementation_complexity": "medium", "mvp_effort_days": 14},
        {"capability_id": "no-show-protector", "capability_name": "No-Show Protector (Deposits + Reminders)",
         "description": "Sends deposit links, reminders at 24h + 2h. Tracks confirmation status.",
         "pain_points_served": ["NS-01", "NS-02", "NS-03", "NS-04"],
         "industries_served": ["barber", "beauty", "restaurant", "hotel", "medspa"],
         "industry_count": 5, "autonomy_level": 5, "implementation_complexity": "low", "mvp_effort_days": 7},
        {"capability_id": "lapse-detector", "capability_name": "Lapse Detector (Win-Back Engine)",
         "description": "Monitors customer visit frequency. Alerts when regulars go quiet. Sends win-back messages.",
         "pain_points_served": ["SC-01", "SC-02", "SC-03", "SC-04", "SC-05", "SC-06", "SC-07", "SC-08", "SC-09"],
         "industries_served": ["barber", "beauty", "cleaning", "petcare", "tutor", "retail", "vet"],
         "industry_count": 7, "autonomy_level": 5, "implementation_complexity": "low", "mvp_effort_days": 5},
        {"capability_id": "quote-follower", "capability_name": "Quote Follower (Estimate Chase + Approval)",
         "description": "Sends follow-ups on unresponded estimates. Digital approval via SMS.",
         "pain_points_served": ["QM-01", "QM-02", "QM-03", "UW-01", "UW-02", "UW-03"],
         "industries_served": ["electrician", "builder", "hvac", "garage", "medspa"],
         "industry_count": 5, "autonomy_level": 4, "implementation_complexity": "low", "mvp_effort_days": 7},
        {"capability_id": "channel-pl", "capability_name": "Channel P&L (Per-Channel Margin Tracker)",
         "description": "Tracks true margin per sales channel after commission, VAT, promos.",
         "pain_points_served": ["MT-01", "MT-02", "DV-01"],
         "industries_served": ["restaurant", "hotel", "reseller", "dropship"],
         "industry_count": 4, "autonomy_level": 5, "implementation_complexity": "medium", "mvp_effort_days": 10},
        {"capability_id": "compliance-dashboard", "capability_name": "Compliance Dashboard (Cert Expiry + Alerts)",
         "description": "Monitors certificate expiry dates. Alerts 60 days before. Tracks compliance status.",
         "pain_points_served": ["CD-01", "CD-02", "CD-03", "CD-04", "CD-05", "CD-06", "CD-07", "CD-08", "CD-09"],
         "industries_served": ["electrician", "hvac", "builder", "tree_surgeon", "care", "vet"],
         "industry_count": 6, "autonomy_level": 4, "implementation_complexity": "medium", "mvp_effort_days": 10},
        {"capability_id": "direct-migration", "capability_name": "Direct Migration (Marketplace to Direct)",
         "description": "Migrates marketplace clients to direct booking. Campaigns + incentives.",
         "pain_points_served": ["MM-01", "MM-02", "MM-03", "MT-03", "MT-04", "MT-05"],
         "industries_served": ["petcare", "restaurant", "hotel", "barber", "beauty", "tutor"],
         "industry_count": 6, "autonomy_level": 4, "implementation_complexity": "medium", "mvp_effort_days": 10},
        {"capability_id": "review-engine", "capability_name": "Review Engine (Collection + Response)",
         "description": "Sends review requests after service. Responds to reviews. Tracks rating.",
         "pain_points_served": ["RC-02"],
         "industries_served": ["restaurant", "hotel", "beauty", "barber", "cleaning", "garage"],
         "industry_count": 6, "autonomy_level": 4, "implementation_complexity": "low", "mvp_effort_days": 5},
        {"capability_id": "round-ledger", "capability_name": "Round Ledger (Skip/Credit/Debt Tracker)",
         "description": "Digital round book. Tracks skips, credits, DD failures. Auto-chases debt.",
         "pain_points_served": ["UW-07", "PF-01"],
         "industries_served": ["window_cleaner", "cleaning"],
         "industry_count": 2, "autonomy_level": 5, "implementation_complexity": "low", "mvp_effort_days": 5},
        {"capability_id": "tax-sweeper", "capability_name": "Tax Sweeper (Gig Driver / MTD Tracker)",
         "description": "Weekly tax set-aside. Mileage tracking. MTD quarter reminders.",
         "pain_points_served": ["PF-04", "CD-07"],
         "industries_served": ["gig_driver", "bookkeeping"],
         "industry_count": 2, "autonomy_level": 5, "implementation_complexity": "low", "mvp_effort_days": 5},
    ]

    errors = client.insert_rows_json(f"{project}.{dataset}.capabilities", capabilities)
    if errors:
        print(f"  Capabilities insert errors: {errors[:3]}")
    else:
        print(f"  Capabilities: {len(capabilities)} rows loaded")
    return len(capabilities)


def load_competitor_stacks():
    """Parse CAMP-*-GB.md files into competitor_stacks rows."""
    camp_dir = Path("/root/agentcom/campaigns")
    rows = []

    for camp_file in sorted(camp_dir.glob("CAMP-*-GB.md")):
        m = re.match(r'CAMP-(.+)-GB\.md', camp_file.name)
        if not m:
            continue
        vertical = m.group(1).lower()
        text = camp_file.read_text()

        in_table = False
        for line in text.split("\n"):
            line = line.strip()
            if "Tool" in line and "|" in line and ("Category" in line or "Pricing" in line or "Cost" in line):
                in_table = True
                continue
            if in_table and line.startswith("|") and "---" not in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    tool_name = parts[0][:100]
                    pricing = parts[1] if len(parts) > 1 else ""
                    pricing_value = None
                    pricing_model = None
                    pricing_period = None
                    nums = re.findall(r'[\d.]+', pricing.replace(",", ""))
                    if nums:
                        try:
                            pricing_value = float(nums[0])
                        except ValueError:
                            pass
                    if "£" in pricing:
                        pricing_model = "flat"
                        pricing_period = "monthly"
                    elif "%" in pricing:
                        pricing_model = "commission"
                    elif "free" in pricing.lower():
                        pricing_value = 0
                        pricing_model = "flat"
                    rows.append({
                        "vertical": vertical, "tool_name": tool_name,
                        "tool_category": None, "pricing_model": pricing_model,
                        "pricing_value": pricing_value, "pricing_period": pricing_period,
                        "pricing_currency": "GBP", "market_share_note": None,
                        "has_ai_receptionist": False, "export_available": True,
                        "source": str(camp_file), "last_verified": None,
                    })
            elif in_table and not line.startswith("|"):
                in_table = False

    if rows:
        errors = client.insert_rows_json(f"{project}.{dataset}.competitor_stacks", rows)
        if errors:
            print(f"  Competitor stacks insert errors: {errors[:3]}")
        else:
            print(f"  Competitor stacks: {len(rows)} rows loaded")
    return len(rows)


if __name__ == "__main__":
    print("Loading pain points...")
    load_pain_points()
    print("Loading vertical rankings...")
    load_vertical_rankings()
    print("Loading capabilities...")
    load_capabilities()
    print("Loading competitor stacks...")
    load_competitor_stacks()
    print("Done.")
