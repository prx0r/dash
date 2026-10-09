#!/usr/bin/env python3
"""Create remaining BQ tables and load data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from kernel.bigquery.connect import connect

client = connect()
project = client.project
dataset = "drop"

# Create competitor_stacks table
client.query(f"""
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
""").result()
print("Created: competitor_stacks")

# Create capabilities table
client.query(f"""
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
""").result()
print("Created: capabilities")

print("All tables created.")
