-- Derived views for the Agentcom knowledge graph (BIGQUERY_GRAPH_PLAN.md §6).
-- Formulas mirror kernel/analysis (Python is the reference implementation).
-- Scores are computed, never stored (Protocol Rule 4).

-- 1. Verified-only node slice (PROPOSED hidden from decision queries)
CREATE OR REPLACE VIEW `drop.v_verified_nodes` AS
SELECT * FROM `drop.graph_nodes`
WHERE JSON_VALUE(properties_json, '$.verification') IS NULL
   OR JSON_VALUE(properties_json, '$.verification') = 'VERIFIED';

-- 2. Pain index: fix → templates (mirrors TeardownRegistry.pain_index)
CREATE OR REPLACE VIEW `drop.v_pain_index` AS
SELECT e2.target_node AS fix, ARRAY_AGG(DISTINCT e1.source_node) AS templates
FROM `drop.graph_edges` e1
JOIN `drop.graph_edges` e2
  ON e1.target_node = e2.source_node
WHERE e1.edge_type = 'HAS_PAIN' AND e2.edge_type = 'FIXED_BY'
GROUP BY fix;

-- 3. Opportunity ranking (formula opportunity.v2: vacancy weight × pain density)
CREATE OR REPLACE VIEW `drop.v_opportunity` AS
WITH vac AS (
  SELECT o.node_id AS sic, o.metric_value AS w
  FROM `drop.graph_observations` o
  WHERE o.metric_name = 'ons.jobs_thousands'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY o.node_id ORDER BY o.observed_at DESC) = 1
),
tpl_weight AS (
  SELECT e.target_node AS tpl, SUM(v.w) AS weight
  FROM `drop.graph_edges` e JOIN vac v ON v.sic = e.source_node
  WHERE e.edge_type = 'MAPS_TO'
  GROUP BY tpl
),
density AS (
  SELECT tpl, COUNT(*) AS pains FROM (
    SELECT DISTINCT e.source_node AS tpl, e.target_node AS pain
    FROM `drop.graph_edges` e WHERE e.edge_type = 'HAS_PAIN') GROUP BY tpl
),
leaks AS (
  SELECT node_id AS tpl, COUNT(*) AS leaks
  FROM `drop.graph_observations`
  WHERE metric_name LIKE 'leak.%' GROUP BY tpl
)
SELECT w.tpl AS template_id,
  ROUND(w.weight * (1 + 0.1 * (IFNULL(d.pains, 0) + IFNULL(l.leaks, 0))), 1)
    AS opportunity,
  w.weight AS vacancy_weight
FROM tpl_weight w
LEFT JOIN density d USING (tpl)
LEFT JOIN leaks l ON l.tpl = w.tpl
ORDER BY opportunity DESC;

-- 4. Readiness (formula readiness.v2: 100-15-5*comp-5*mkt+5*owned, ceiling 90)
CREATE OR REPLACE VIEW `drop.v_readiness` AS
WITH inputs AS (
  SELECT node_id AS tpl,
    MAX(IF(metric_name = 'readiness.compliance_count', metric_value, NULL)) AS comp,
    MAX(IF(metric_name = 'readiness.has_marketplace', metric_value, NULL)) AS mkt,
    MAX(IF(metric_name = 'readiness.has_owned', metric_value, NULL)) AS owned
  FROM `drop.graph_observations`
  WHERE metric_name LIKE 'readiness.%'
  GROUP BY tpl
)
SELECT tpl AS template_id,
  LEAST(90, GREATEST(0, 100 - 15 - 5*IFNULL(comp, 0) - 5*IFNULL(mkt, 0) + 5*IFNULL(owned, 0)))
    AS readiness
FROM inputs
ORDER BY readiness DESC;

-- 5. Compliance coverage: vertical → laws with basis split
CREATE OR REPLACE VIEW `drop.v_compliance_coverage` AS
SELECT n.node_id AS template_id,
  COUNTIF(JSON_VALUE(m.properties_json, '$.basis') = 'verified-2026') AS verified_laws,
  COUNTIF(JSON_VALUE(m.properties_json, '$.basis') = 'well-established') AS established_laws,
  COUNT(*) AS total_laws
FROM `drop.graph_edges` e
JOIN `drop.graph_nodes` n ON n.node_id = e.source_node
JOIN `drop.graph_nodes` m ON m.node_id = e.target_node
WHERE e.edge_type = 'GOVERNED_BY'
GROUP BY template_id;

-- 6. Stack watch: latest price signal per TOOL_ (+ verdict from node)
CREATE OR REPLACE VIEW `drop.v_stack_watch` AS
WITH latest AS (
  SELECT o.node_id AS tool, o.metric_name, o.metric_value, o.observed_at,
    ROW_NUMBER() OVER (PARTITION BY o.node_id, o.metric_name ORDER BY o.observed_at DESC) AS rn
  FROM `drop.graph_observations` o
  WHERE o.metric_name LIKE 'price.%'
)
SELECT n.node_id AS tool,
  JSON_VALUE(n.properties_json, '$.tool') AS tool_name,
  JSON_VALUE(n.properties_json, '$.verdict') AS verdict,
  l.metric_name, l.metric_value, l.observed_at
FROM `drop.graph_nodes` n
LEFT JOIN latest l ON l.tool = n.node_id AND l.rn = 1
WHERE n.node_type = 'stack_tool';
