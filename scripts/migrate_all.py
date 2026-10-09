#!/usr/bin/env python3
"""Full migration: JSON + MD → BigQuery.

Usage:
    python3 scripts/migrate_all.py --phase 1        # Load JSON → graph tables
    python3 scripts/migrate_all.py --phase 2        # Create new tables + load MD
    python3 scripts/migrate_all.py --phase 3        # Create derived views
    python3 scripts/migrate_all.py --phase all      # Everything
    python3 scripts/migrate_all.py --dry-run        # Print row counts only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kernel.bigquery.connect import connect, merge_nodes, insert_edges_new, insert_observations
from kernel.bigquery.seed import (
    utcnow, node, edge, observation,
    build_template_rows, build_pattern_rows, build_pattern_edge,
    build_teardown_rows, build_fix_rows, build_legislation_rows,
    build_governed_edges, tpl_node_id, _slug
)
from kernel.templates.registry import TemplateRegistry
from kernel.teardowns.registry import TeardownRegistry


# ── Phase 1: JSON → graph tables ──────────────────────────────────────────

def load_templates(client, dataset: str, dry: bool = False) -> dict:
    reg = TemplateRegistry()
    all_nodes, all_edges, all_obs = [], [], []
    for tid in reg.list_ids():
        tpl = reg.load(tid)
        n, e = build_template_rows(tpl, utcnow())
        all_nodes.extend(n)
        all_edges.extend(e)
        # Patterns
        for wf in tpl.raw.get("workflows", []):
            pname = wf.get("pattern", wf.get("name", ""))
            if pname:
                all_nodes.extend(build_pattern_rows(pname, utcnow()))
                all_edges.append(build_pattern_edge(tpl.template_id, pname, utcnow()))
        # Observations from agentic_mapping readiness signals
        for am in tpl.raw.get("agentic_mapping", []):
            if am.get("readiness_score") is not None:
                all_obs.append(observation(
                    tpl_node_id(tpl.template_id),
                    "readiness.score",
                    float(am["readiness_score"]),
                    utcnow(),
                    evidence_type="template-analysis"))

    print(f"  Templates: {len(all_nodes)} nodes, {len(all_edges)} edges, {len(all_obs)} observations")
    if dry:
        return {"nodes": len(all_nodes), "edges": len(all_edges), "obs": len(all_obs)}
    merge_nodes(client, dataset, all_nodes)
    insert_edges_new(client, dataset, all_edges)
    insert_observations(client, dataset, all_obs)
    return {"nodes": len(all_nodes), "edges": len(all_edges), "obs": len(all_obs)}


def load_teardowns(client, dataset: str, dry: bool = False) -> dict:
    reg = TeardownRegistry()
    all_nodes, all_edges, all_obs = [], [], []
    for td in reg.load_all():
        n, e, o = build_teardown_rows(td, utcnow())
        all_nodes.extend(n)
        all_edges.extend(e)
        all_obs.extend(o)
        # Readiness observations from pain ranking
        tpl_nid = tpl_node_id(td.template_id)
        has_marketplace = any(
            p.get("fix_id") == "FIX-MARKETPLACE-TAX"
            for p in td.raw.get("pain_ranking", []))
        has_owned = any(
            p.get("fix_id") in ("FIX-MISSED-INBOUND", "FIX-SILENT-CHURN")
            for p in td.raw.get("pain_ranking", []))
        compliance_count = len(td.raw.get("compliance_spine", []))
        all_obs.append(observation(tpl_nid, "readiness.has_marketplace",
                                   1.0 if has_marketplace else 0.0, utcnow()))
        all_obs.append(observation(tpl_nid, "readiness.has_owned",
                                   1.0 if has_owned else 0.0, utcnow()))
        all_obs.append(observation(tpl_nid, "readiness.compliance_count",
                                   float(compliance_count), utcnow()))

    print(f"  Teardowns: {len(all_nodes)} nodes, {len(all_edges)} edges, {len(all_obs)} observations")
    if dry:
        return {"nodes": len(all_nodes), "edges": len(all_edges), "obs": len(all_obs)}
    merge_nodes(client, dataset, all_nodes)
    insert_edges_new(client, dataset, all_edges)
    insert_observations(client, dataset, all_obs)
    return {"nodes": len(all_nodes), "edges": len(all_edges), "obs": len(all_obs)}


def load_legislation(client, dataset: str, dry: bool = False) -> dict:
    from kernel.compliance.registry import ComplianceRegistry
    reg = ComplianceRegistry()
    all_nodes, all_edges = [], []
    for entry in reg.load_all():
        n, e = build_legislation_rows([entry], utcnow())
        all_nodes.extend(n)
        all_edges.extend(e)
    # GOVERNED_BY edges from templates
    tpl_reg = TemplateRegistry()
    for tid in tpl_reg.list_ids():
        tpl = tpl_reg.load(tid)
        all_edges.extend(build_governed_edges(
            tpl.vertical, tpl.template_id, reg.load_all(), utcnow()))

    print(f"  Legislation: {len(all_nodes)} nodes, {len(all_edges)} edges")
    if dry:
        return {"nodes": len(all_nodes), "edges": len(all_edges)}
    merge_nodes(client, dataset, all_nodes)
    insert_edges_new(client, dataset, all_edges)
    return {"nodes": len(all_nodes), "edges": len(all_edges)}


def load_fixes(client, dataset: str, dry: bool = False) -> dict:
    fixes_path = ROOT / "kernel" / "teardowns" / "fixes.json"
    raw = json.loads(fixes_path.read_text())
    fixes = raw.get("fixes", raw) if isinstance(raw, dict) else raw
    rows = build_fix_rows(fixes, utcnow())
    print(f"  Fixes: {len(rows)} nodes")
    if dry:
        return {"nodes": len(rows)}
    merge_nodes(client, dataset, rows)
    return {"nodes": len(rows)}


def phase1(client, dataset: str, dry: bool = False):
    print("\n═══ Phase 1: JSON → graph tables ═══")
    r = {}
    r["templates"] = load_templates(client, dataset, dry)
    r["teardowns"] = load_teardowns(client, dataset, dry)
    r["legislation"] = load_legislation(client, dataset, dry)
    r["fixes"] = load_fixes(client, dataset, dry)
    return r


# ── Phase 2: New tables ───────────────────────────────────────────────────

PAIN_POINTS_DDL = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.pain_points` (
  pain_id STRING NOT NULL,
  pain_name STRING NOT NULL,
  pain_category STRING NOT NULL,
  pain_statement STRING NOT NULL,
  exact_statistic STRING,
  stat_source STRING,
  stat_basis STRING,
  annual_impact_gbp FLOAT64,
  impact_sample STRING,
  impact_period STRING,
  mechanism STRING,
  fix_id STRING,
  agent_autonomy INT64,
  autonomy_label STRING,
  agent_action_example STRING,
  industries ARRAY<STRING>,
  vertical_count INT64,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  source_file STRING,
  verification STRING DEFAULT 'PROPOSED'
) PARTITION BY DATE(created_at)
CLUSTER BY pain_category, agent_autonomy
"""

VERTICAL_RANKINGS_DDL = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.vertical_rankings` (
  ranking_id STRING NOT NULL,
  vertical STRING NOT NULL,
  template_id STRING,
  overall_score FLOAT64,
  chat_interface_fit INT64,
  pain_severity INT64,
  capability_atomicity INT64,
  discovery_potential INT64,
  marketplace_dependency INT64,
  compliance_ceiling INT64,
  first_capability STRING,
  first_capability_type STRING,
  tier INT64,
  pain_point_count INT64,
  total_annual_impact_gbp FLOAT64,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  source_file STRING
) CLUSTER BY tier
"""

EVIDENCE_DDL = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.evidence` (
  evidence_id STRING NOT NULL,
  claim STRING NOT NULL,
  statistic STRING,
  stat_numeric FLOAT64,
  stat_unit STRING,
  source_type STRING,
  source_detail STRING,
  source_url STRING,
  confidence FLOAT64,
  applicable_industries ARRAY<STRING>,
  applicable_verticals ARRAY<STRING>,
  first_captured TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_verified TIMESTAMP,
  verification_status STRING DEFAULT 'PROPOSED',
  source_file STRING,
  source_line INT64
) PARTITION BY DATE(first_captured)
CLUSTER BY source_type
"""

COMPETITOR_STACKS_DDL = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.competitor_stacks` (
  vertical STRING NOT NULL,
  tool_name STRING NOT NULL,
  tool_category STRING,
  pricing_model STRING,
  pricing_value FLOAT64,
  pricing_period STRING,
  pricing_currency STRING DEFAULT 'GBP',
  market_share_note STRING,
  has_ai_receptionist BOOL DEFAULT FALSE,
  export_available BOOL DEFAULT TRUE,
  source STRING,
  last_verified TIMESTAMP
)
"""

CAPABILITIES_DDL = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.capabilities` (
  capability_id STRING NOT NULL,
  capability_name STRING NOT NULL,
  description STRING,
  pain_points_served ARRAY<STRING>,
  industries_served ARRAY<STRING>,
  industry_count INT64,
  autonomy_level INT64,
  implementation_complexity STRING,
  mvp_effort_days INT64,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def create_tables(client, project: str, dataset: str, dry: bool = False):
    print("\n═══ Phase 2a: Create new tables ═══")
    tables = {
        "pain_points": PAIN_POINTS_DDL,
        "vertical_rankings": VERTICAL_RANKINGS_DDL,
        "evidence": EVIDENCE_DDL,
        "competitor_stacks": COMPETITOR_STACKS_DDL,
        "capabilities": CAPABILITIES_DDL,
    }
    for name, ddl in tables.items():
        formatted = ddl.format(project=project, dataset=dataset)
        if dry:
            print(f"  Would create: {name}")
        else:
            client.query(formatted).result()
            print(f"  Created: {name}")


# ── Phase 2b: Parse MD → structured data ──────────────────────────────────

def parse_pain_registry(md_path: Path) -> list[dict]:
    """Parse PAIN_POINT_REGISTRY.md into pain_points rows."""
    text = md_path.read_text()
    rows = []
    current_category = ""
    current_section = ""

    # Split by sections
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Track sections
        if line.startswith("## SECTION"):
            m = re.match(r"## SECTION \d+: (.+)", line)
            if m:
                current_section = m.group(1).lower().replace(" / ", "_").replace(" ", "_")
            i += 1
            continue

        # Track subsections
        if line.startswith("### "):
            current_category = line[4:].strip()
            i += 1
            continue

        # Parse pain point blocks
        if line.startswith("### ") or (line.startswith("**") and "Pain:**" in line):
            i += 1
            continue

        # Look for structured fields
        if line.startswith("- **Pain:**"):
            pain_name = line.split("- **Pain:**")[1].strip()
            # Collect the full pain block
            block = {"pain_name": pain_name, "fields": {}}
            i += 1
            while i < len(lines) and lines[i].strip().startswith("- **"):
                field_line = lines[i].strip()
                m = re.match(r"- \*\*(.+?):\*\*\s*(.*)", field_line)
                if m:
                    key, val = m.group(1).lower().replace(" ", "_"), m.group(2).strip()
                    block["fields"][key] = val
                i += 1

            # Extract fields
            f = block["fields"]
            pain_id_m = re.search(r'\*\*(\w{2}-\d+)\*\*', lines[i-1] if i > 0 else "")
            # Find pain_id in nearby lines
            pain_id = None
            for lookback in range(max(0, i-10), i):
                pid_m = re.search(r'\*\*(\w{2}-\d+)\*\*', lines[lookback])
                if pid_m:
                    pain_id = pid_m.group(1)
                    break

            if not pain_id:
                # Generate from category + count
                pain_id = f"PP-{len(rows)+1:03d}"

            # Parse annual impact
            impact_gbp = None
            impact_str = f.get("annual_£_impact", f.get("annual_impact_gbp", ""))
            if impact_str:
                nums = re.findall(r'[\d,]+(?:\.\d+)?', impact_str.replace("£", "").replace(",", ""))
                if nums:
                    try:
                        impact_gbp = float(nums[0])
                    except ValueError:
                        pass
                # Handle ranges
                if impact_gbp and len(nums) > 1:
                    try:
                        impact_gbp = (impact_gbp + float(nums[1])) / 2
                    except ValueError:
                        pass

            # Parse autonomy
            autonomy = 3
            autonomy_str = f.get("agent_autonomy", "")
            am = re.search(r'(\d)', autonomy_str)
            if am:
                autonomy = int(am.group(1))

            autonomy_labels = {1: "advisory", 2: "assist", 3: "auto+approve",
                             4: "auto+notify", 5: "autonomous"}

            # Parse industries
            industries_str = f.get("industries", "")
            industries = [s.strip().strip('"').strip("'")
                         for s in re.split(r',\s*', industries_str)
                         if s.strip() and s.strip() not in ("", "universal trades")]

            rows.append({
                "pain_id": pain_id,
                "pain_name": block["pain_name"],
                "pain_category": current_section or "unknown",
                "pain_statement": f.get("pain", block["pain_name"]),
                "exact_statistic": f.get("stat", None),
                "stat_source": f.get("source", None),
                "stat_basis": f.get("source", None),
                "annual_impact_gbp": impact_gbp,
                "impact_sample": f.get("annual_£_impact", None),
                "impact_period": None,
                "mechanism": f.get("mechanism", None),
                "fix_id": None,
                "agent_autonomy": autonomy,
                "autonomy_label": autonomy_labels.get(autonomy, "unknown"),
                "agent_action_example": f.get("agent_action", None),
                "industries": industries,
                "vertical_count": len(industries),
                "source_file": str(md_path),
                "verification": "VERIFIED" if f.get("source") == "verified-2026" else "PROPOSED",
            })

    return rows


def parse_vertical_rankings(md_path: Path) -> list[dict]:
    """Parse UK_BUSINESS_RANKING.md into vertical_rankings rows."""
    text = md_path.read_text()
    rows = []
    lines = text.split("\n")

    current_vertical = None
    current_tier = 0
    in_table = False

    for i, line in enumerate(lines):
        line = line.strip()

        # Track tier
        if line.startswith("## TIER"):
            m = re.match(r"## TIER (\d+)", line)
            if m:
                current_tier = int(m.group(1))

        # Track vertical from ### headers
        if line.startswith("### ") and not line.startswith("### Scoring"):
            name = line[4:].strip()
            # Parse "1. Electrician" format
            m = re.match(r'(\d+)\.\s+(.+)', name)
            if m:
                current_vertical = m.group(2).lower()
                rows.append({
                    "vertical": current_vertical,
                    "tier": current_tier,
                    "ranking_id": "chatgpt-native-2026-09",
                })

        # Parse score from table
        if current_vertical and line.startswith("**Score:**"):
            m = re.search(r'(\d+\.\d+)/5', line)
            if m:
                rows[-1]["overall_score"] = float(m.group(1))

        # Parse dimension scores
        if current_vertical and "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 3:
                dim_name = parts[0].lower().replace(" ", "_").replace("'", "")
                try:
                    score = int(parts[1])
                    if 1 <= score <= 5:
                        key = None
                        if "chat" in dim_name and "fit" in dim_name:
                            key = "chat_interface_fit"
                        elif "pain" in dim_name and "severity" in dim_name:
                            key = "pain_severity"
                        elif "capab" in dim_name and "atomic" in dim_name:
                            key = "capability_atomicity"
                        elif "discover" in dim_name:
                            key = "discovery_potential"
                        elif "marketplace" in dim_name and "depend" in dim_name:
                            key = "marketplace_dependency"
                        elif "compliance" in dim_name and "ceiling" in dim_name:
                            key = "compliance_ceiling"
                        if key and rows and rows[-1].get("vertical") == current_vertical:
                            rows[-1][key] = score
                except (ValueError, IndexError):
                    pass

        # Parse first capability
        if current_vertical and line.startswith("**Why #"):
            # The "Why #N" paragraph often comes after the first capability
            pass

        # Look for first capability in the pain table
        if current_vertical and "Voice agent" in line and "first_capability" not in rows[-1]:
            rows[-1]["first_capability"] = "Voice agent (missed-call recovery)"
            rows[-1]["first_capability_type"] = "autonomous"
        if current_vertical and "AI receptionist" in line and "first_capability" not in rows[-1]:
            rows[-1]["first_capability"] = "AI receptionist"
            rows[-1]["first_capability_type"] = "autonomous"
        if current_vertical and "Deposit" in line and "first_capability" not in rows[-1]:
            rows[-1]["first_capability"] = "No-show deposit system"
            rows[-1]["first_capability_type"] = "autonomous"
        if current_vertical and "Channel P&L" in line and "first_capability" not in rows[-1]:
            rows[-1]["first_capability"] = "Channel P&L tracker"
            rows[-1]["first_capability_type"] = "autonomous"
        if current_vertical and "Round ledger" in line and "first_capability" not in rows[-1]:
            rows[-1]["first_capability"] = "Round ledger + DD chase"
            rows[-1]["first_capability_type"] = "autonomous"
        if current_vertical and "Win-back engine" in line and "first_capability" not in rows[-1]:
            rows[-1]["first_capability"] = "Win-back engine"
            rows[-1]["first_capability_type"] = "autonomous"

    return rows


def parse_evidence(md_path: Path) -> list[dict]:
    """Parse PAIN_POINT_REGISTRY.md into evidence rows."""
    text = md_path.read_text()
    rows = []
    evidence_count = 0

    lines = text.split("\n")
    for i, line in enumerate(lines):
        line = line.strip()

        # Look for stats with sources
        if "**Stat:**" in line:
            stat_text = line.split("**Stat:**")[1].strip()
            if stat_text and stat_text != "(no stat" and stat_text != "(no stat —":
                evidence_count += 1

                # Try to extract numeric value
                stat_numeric = None
                stat_unit = None
                nums = re.findall(r'(\d+(?:\.\d+)?)', stat_text.replace(",", ""))
                if nums:
                    try:
                        stat_numeric = float(nums[0])
                        if "%" in stat_text:
                            stat_unit = "percent"
                        elif "£" in stat_text or "gbp" in stat_text.lower():
                            stat_unit = "gbp"
                        elif "/mo" in stat_text or "/yr" in stat_text:
                            stat_unit = "gbp"
                    except ValueError:
                        pass

                # Determine source type
                source_type = "template-analysis"
                if "verified-2026" in line or "verified-2026" in stat_text:
                    source_type = "verified-2026"
                elif "govt-data" in line or "govt-data" in stat_text:
                    source_type = "govt-data"
                elif "well-established" in line:
                    source_type = "well-established"

                # Confidence from source type
                confidence_map = {
                    "verified-2026": 0.9,
                    "govt-data": 0.85,
                    "well-established": 0.75,
                    "template-analysis": 0.6,
                }

                rows.append({
                    "evidence_id": f"EVD-{evidence_count:03d}",
                    "claim": stat_text[:500],
                    "statistic": stat_text[:200],
                    "stat_numeric": stat_numeric,
                    "stat_unit": stat_unit,
                    "source_type": source_type,
                    "source_detail": None,
                    "source_url": None,
                    "confidence": confidence_map.get(source_type, 0.5),
                    "applicable_industries": [],
                    "applicable_verticals": [],
                    "first_captured": None,
                    "last_verified": None,
                    "verification_status": "VERIFIED" if source_type in ("verified-2026", "govt-data") else "PROPOSED",
                    "source_file": str(md_path),
                    "source_line": i + 1,
                })

    return rows


def parse_competitor_stacks(md_path: Path) -> list[dict]:
    """Parse CAMP-*-GB.md files into competitor_stacks rows."""
    rows = []
    campaign_dir = md_path.parent

    for camp_file in sorted(campaign_dir.glob("CAMP-*-GB.md")):
        # Extract vertical from filename
        m = re.match(r'CAMP-(.+)-GB\.md', camp_file.name)
        if not m:
            continue
        vertical = m.group(1).lower()

        text = camp_file.read_text()

        # Look for competitor/stack tables
        in_table = False
        for line in text.split("\n"):
            line = line.strip()
            if "| Tool" in line or "| tool" in line or "| Platform" in line:
                in_table = True
                continue
            if in_table and line.startswith("|") and "---" not in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    tool_name = parts[0]
                    pricing = parts[1] if len(parts) > 1 else ""

                    # Parse pricing
                    pricing_value = None
                    pricing_model = None
                    pricing_period = None
                    nums = re.findall(r'[\d.]+', pricing.replace(",", ""))
                    if nums:
                        try:
                            pricing_value = float(nums[0])
                        except ValueError:
                            pass
                    if "£" in pricing or "gbp" in pricing.lower():
                        pricing_model = "flat"
                        pricing_period = "monthly"
                    elif "%" in pricing:
                        pricing_model = "commission"
                    elif "free" in pricing.lower():
                        pricing_value = 0
                        pricing_model = "flat"

                    rows.append({
                        "vertical": vertical,
                        "tool_name": tool_name[:100],
                        "tool_category": None,
                        "pricing_model": pricing_model,
                        "pricing_value": pricing_value,
                        "pricing_period": pricing_period,
                        "pricing_currency": "GBP",
                        "market_share_note": None,
                        "has_ai_receptionist": False,
                        "export_available": True,
                        "source": str(camp_file),
                        "last_verified": None,
                    })
            elif in_table and not line.startswith("|"):
                in_table = False

    return rows


def load_pain_points(client, project: str, dataset: str, dry: bool = False) -> int:
    md_path = Path("/root/PAIN_POINT_REGISTRY.md")
    rows = parse_pain_registry(md_path)
    print(f"  Pain points: {len(rows)} rows from {md_path.name}")
    if dry or not rows:
        return len(rows)

    # Insert rows
    errors = client.insert_rows_json(f"{project}.{dataset}.pain_points", rows)
    if errors:
        print(f"  ⚠ Insert errors: {errors[:3]}")
    return len(rows)


def load_vertical_rankings(client, project: str, dataset: str, dry: bool = False) -> int:
    md_path = Path("/root/UK_BUSINESS_RANKING.md")
    rows = parse_vertical_rankings(md_path)
    print(f"  Vertical rankings: {len(rows)} rows from {md_path.name}")
    if dry or not rows:
        return len(rows)

    errors = client.insert_rows_json(f"{project}.{dataset}.vertical_rankings", rows)
    if errors:
        print(f"  ⚠ Insert errors: {errors[:3]}")
    return len(rows)


def load_evidence(client, project: str, dataset: str, dry: bool = False) -> int:
    md_path = Path("/root/PAIN_POINT_REGISTRY.md")
    rows = parse_evidence(md_path)
    print(f"  Evidence: {len(rows)} rows from {md_path.name}")
    if dry or not rows:
        return len(rows)

    errors = client.insert_rows_json(f"{project}.{dataset}.evidence", rows)
    if errors:
        print(f"  ⚠ Insert errors: {errors[:3]}")
    return len(rows)


def load_competitor_stacks(client, project: str, dataset: str, dry: bool = False) -> int:
    camp_dir = Path("/root/agentcom/campaigns")
    rows = parse_competitor_stacks(camp_dir)
    print(f"  Competitor stacks: {len(rows)} rows from {camp_dir}")
    if dry or not rows:
        return len(rows)

    errors = client.insert_rows_json(f"{project}.{dataset}.competitor_stacks", rows)
    if errors:
        print(f"  ⚠ Insert errors: {errors[:3]}")
    return len(rows)


def load_capabilities(client, project: str, dataset: str, dry: bool = False) -> int:
    """Load the 10 core capabilities from our analysis."""
    capabilities = [
        {
            "capability_id": "voice-agent",
            "capability_name": "Voice Agent (Missed-Call Recovery)",
            "description": "Answers calls when owner is on the tools. Takes message, books callback via SMS.",
            "pain_points_served": ["MI-01", "MI-02", "MI-03", "MI-04", "MI-06"],
            "industries_served": ["electrician", "builder", "hvac", "garage", "funeral", "restaurant"],
            "industry_count": 6,
            "autonomy_level": 5,
            "implementation_complexity": "medium",
            "mvp_effort_days": 14,
        },
        {
            "capability_id": "no-show-protector",
            "capability_name": "No-Show Protector (Deposits + Reminders)",
            "description": "Sends deposit links, reminders at 24h + 2h. Tracks confirmation status.",
            "pain_points_served": ["NS-01", "NS-02", "NS-03", "NS-04"],
            "industries_served": ["barber", "beauty", "restaurant", "hotel", "medspa"],
            "industry_count": 5,
            "autonomy_level": 5,
            "implementation_complexity": "low",
            "mvp_effort_days": 7,
        },
        {
            "capability_id": "lapse-detector",
            "capability_name": "Lapse Detector (Win-Back Engine)",
            "description": "Monitors customer visit frequency. Alerts when regulars go quiet. Sends win-back messages.",
            "pain_points_served": ["SC-01", "SC-02", "SC-03", "SC-04", "SC-05", "SC-06", "SC-07", "SC-08", "SC-09"],
            "industries_served": ["barber", "beauty", "cleaning", "petcare", "tutor", "retail", "vet"],
            "industry_count": 7,
            "autonomy_level": 5,
            "implementation_complexity": "low",
            "mvp_effort_days": 5,
        },
        {
            "capability_id": "quote-follower",
            "capability_name": "Quote Follower (Estimate Chase + Approval)",
            "description": "Sends follow-ups on unresponded estimates. Digital approval via SMS.",
            "pain_points_served": ["QM-01", "QM-02", "QM-03", "UW-01", "UW-02", "UW-03"],
            "industries_served": ["electrician", "builder", "hvac", "garage", "medspa"],
            "industry_count": 5,
            "autonomy_level": 4,
            "implementation_complexity": "low",
            "mvp_effort_days": 7,
        },
        {
            "capability_id": "channel-pl",
            "capability_name": "Channel P&L (Per-Channel Margin Tracker)",
            "description": "Tracks true margin per sales channel after commission, VAT, promos.",
            "pain_points_served": ["MT-01", "MT-02", "DV-01"],
            "industries_served": ["restaurant", "hotel", "reseller", "dropship"],
            "industry_count": 4,
            "autonomy_level": 5,
            "implementation_complexity": "medium",
            "mvp_effort_days": 10,
        },
        {
            "capability_id": "compliance-dashboard",
            "capability_name": "Compliance Dashboard (Cert Expiry + Alerts)",
            "description": "Monitors certificate expiry dates. Alerts 60 days before. Tracks compliance status.",
            "pain_points_served": ["CD-01", "CD-02", "CD-03", "CD-04", "CD-05", "CD-06", "CD-07", "CD-08", "CD-09"],
            "industries_served": ["electrician", "hvac", "builder", "tree_surgeon", "care", "vet"],
            "industry_count": 6,
            "autonomy_level": 4,
            "implementation_complexity": "medium",
            "mvp_effort_days": 10,
        },
        {
            "capability_id": "direct-migration",
            "capability_name": "Direct Migration (Marketplace→Direct)",
            "description": "Migrates marketplace clients to direct booking. Campaigns + incentives.",
            "pain_points_served": ["MM-01", "MM-02", "MM-03", "MT-03", "MT-04", "MT-05"],
            "industries_served": ["petcare", "restaurant", "hotel", "barber", "beauty", "tutor"],
            "industry_count": 6,
            "autonomy_level": 4,
            "implementation_complexity": "medium",
            "mvp_effort_days": 10,
        },
        {
            "capability_id": "review-engine",
            "capability_name": "Review Engine (Collection + Response)",
            "description": "Sends review requests after service. Responds to reviews. Tracks rating.",
            "pain_points_served": ["RC-02"],
            "industries_served": ["restaurant", "hotel", "beauty", "barber", "cleaning", "garage"],
            "industry_count": 6,
            "autonomy_level": 4,
            "implementation_complexity": "low",
            "mvp_effort_days": 5,
        },
        {
            "capability_id": "round-ledger",
            "capability_name": "Round Ledger (Skip/Credit/Debt Tracker)",
            "description": "Digital round book. Tracks skips, credits, DD failures. Auto-chases debt.",
            "pain_points_served": ["UW-07", "PF-01"],
            "industries_served": ["window_cleaner", "cleaning"],
            "industry_count": 2,
            "autonomy_level": 5,
            "implementation_complexity": "low",
            "mvp_effort_days": 5,
        },
        {
            "capability_id": "tax-sweeper",
            "capability_name": "Tax Sweeper (Gig Driver / MTD Tracker)",
            "description": "Weekly tax set-aside. Mileage tracking. MTD quarter reminders.",
            "pain_points_served": ["PF-04", "CD-07"],
            "industries_served": ["gig_driver", "bookkeeping"],
            "industry_count": 2,
            "autonomy_level": 5,
            "implementation_complexity": "low",
            "mvp_effort_days": 5,
        },
    ]

    print(f"  Capabilities: {len(capabilities)} rows")
    if dry:
        return len(capabilities)

    errors = client.insert_rows_json(f"{project}.{dataset}.capabilities", capabilities)
    if errors:
        print(f"  ⚠ Insert errors: {errors[:3]}")
    return len(capabilities)


def phase2(client, project: str, dataset: str, dry: bool = False):
    print("\n═══ Phase 2: New tables + MD → structured data ═══")
    create_tables(client, project, dataset, dry)
    r = {}
    r["pain_points"] = load_pain_points(client, project, dataset, dry)
    r["vertical_rankings"] = load_vertical_rankings(client, project, dataset, dry)
    r["evidence"] = load_evidence(client, project, dataset, dry)
    r["competitor_stacks"] = load_competitor_stacks(client, project, dataset, dry)
    r["capabilities"] = load_capabilities(client, project, dataset, dry)
    return r


# ── Phase 3: Derived views ────────────────────────────────────────────────

VIEWS = {
    "v_pain_index": """
CREATE OR REPLACE VIEW `{project}.{dataset}.v_pain_index` AS
SELECT
  im.vertical,
  im.pain_id,
  pp.pain_name,
  pp.pain_category,
  pp.exact_statistic,
  pp.annual_impact_gbp,
  im.pain_rank,
  im.solution_autonomy,
  pp.agent_action_example
FROM `{project}.{dataset}.industry_pain_matrix` im
JOIN `{project}.{dataset}.pain_points` pp ON im.pain_id = pp.pain_id
ORDER BY im.vertical, im.pain_rank
""",
    "v_opportunity_ranking": """
CREATE OR REPLACE VIEW `{project}.{dataset}.v_opportunity_ranking` AS
SELECT
  vr.vertical,
  vr.overall_score,
  vr.tier,
  vr.first_capability,
  vr.pain_point_count,
  vr.total_annual_impact_gbp,
  vr.chat_interface_fit,
  vr.pain_severity,
  vr.capability_atomicity
FROM `{project}.{dataset}.vertical_rankings` vr
WHERE vr.ranking_id = 'chatgpt-native-2026-09'
ORDER BY vr.overall_score DESC
""",
    "v_evidence_quality": """
CREATE OR REPLACE VIEW `{project}.{dataset}.v_evidence_quality` AS
SELECT
  source_type,
  COUNT(*) as total_claims,
  COUNTIF(verification_status = 'VERIFIED') as verified,
  COUNTIF(verification_status = 'PROPOSED') as proposed,
  COUNTIF(stat_numeric IS NOT NULL) as has_number,
  AVG(confidence) as avg_confidence
FROM `{project}.{dataset}.evidence`
GROUP BY source_type
ORDER BY avg_confidence DESC
""",
    "v_capability_coverage": """
CREATE OR REPLACE VIEW `{project}.{dataset}.v_capability_coverage` AS
SELECT
  capability_id,
  capability_name,
  industry_count,
  autonomy_level,
  ARRAY_LENGTH(pain_points_served) as pain_points_covered,
  industries_served
FROM `{project}.{dataset}.capabilities`
ORDER BY industry_count DESC, autonomy_level DESC
""",
}


def phase3(client, project: str, dataset: str, dry: bool = False):
    print("\n═══ Phase 3: Derived views ═══")
    for name, ddl in VIEWS.items():
        formatted = ddl.format(project=project, dataset=dataset)
        if dry:
            print(f"  Would create view: {name}")
        else:
            client.query(formatted).result()
            print(f"  Created view: {name}")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Migrate agentcom data to BigQuery")
    parser.add_argument("--phase", default="all", choices=["1", "2", "3", "all"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dataset", default="drop")
    args = parser.parse_args()

    project = None  # from vault
    dataset = args.dataset

    if not args.dry_run:
        print("Connecting to BigQuery...")
        client = connect()
        project = client.project
        print(f"Project: {project}, Dataset: {dataset}")
    else:
        client = None
        project = "project-ff2366d2-8fda-4fcb-9ba"
        print("DRY RUN — no writes")

    results = {}
    if args.phase in ("1", "all"):
        if not args.dry_run:
            results["phase1"] = phase1(client, dataset, args.dry_run)
        else:
            results["phase1"] = "dry-run"

    if args.phase in ("2", "all"):
        if not args.dry_run:
            results["phase2"] = phase2(client, project, dataset, args.dry_run)
        else:
            results["phase2"] = "dry-run"

    if args.phase in ("3", "all"):
        if not args.dry_run:
            results["phase3"] = phase3(client, project, dataset, args.dry_run)
        else:
            results["phase3"] = "dry-run"

    print("\n═══ Summary ═══")
    for phase, data in results.items():
        print(f"  {phase}: {data}")


if __name__ == "__main__":
    main()
