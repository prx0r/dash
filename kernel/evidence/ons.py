"""ONS + Nomis evidence client — keyless UK govt statistics for the kernel.

Why raw APIs instead of the three MCP servers:
- ons-mcp.library-apps.dev needs Cloudflare Access org OAuth (401 from here)
- pipeworx gateway path 404s without further docs
- npx TS server adds a node process for what urllib already does
The MCP servers remain the right choice for MCP-native clients
(Claude Desktop etc.) — see MCP_VERDICT.md. The kernel talks HTTP.

All network goes through an injectable fetch callable so tests never
touch the network. Every figure carries provenance (source + retrieved_at).
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

ONS_BASE = "https://api.beta.ons.gov.uk/v1"
NOMIS_BASE = "https://www.nomisweb.co.uk/api/v01"
UK_GEO = "K02000001"


def _http_fetch(url: str, timeout: float = 25.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "agentcom-kernel/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


@dataclass(frozen=True)
class Evidence:
    """One govt-data fact with provenance."""
    metric: str
    value: Any
    unit: str = ""
    source: str = ""
    dataset: str = ""
    retrieved_at: float = field(default_factory=time.time)


# SIC 2007 section → template ids. Vacancies/jobs weight in VACS02 order:
# Q (health/social) > G (retail/motor) > M (professional) > P (education) >
# N (admin) > I (hospitality) > C (manufacturing) > F (construction) ...
# Extend as new templates land (care, builder, retail are next).
SIC_TO_TEMPLATES: dict[str, list[str]] = {
    "Q": ["tpl-gp-gb", "tpl-care-gb"],                                 # health & social work
    "G": ["tpl-dropship-gb", "tpl-reseller-gb", "tpl-garage-gb",
          "tpl-retail-gb"],                                              # retail + motor repair
    "M": ["tpl-bookkeeping-gb", "tpl-msp-gb", "tpl-vet-gb"],             # professional/scientific (incl. veterinary div 75)
    "P": ["tpl-tutor-gb"],                                               # education
    "N": ["tpl-cleaning-gb", "tpl-tree-surgeon-gb",
          "tpl-window-cleaner-gb"],                                      # admin/support (incl. landscape 81.30, cleaning 81.22)
    "I": ["tpl-restaurant-gb", "tpl-hotel-gb"],                          # hospitality
    "F": ["tpl-electrician-gb", "tpl-hvac-gb", "tpl-builder-gb"],        # construction
    "S": ["tpl-barber-gb", "tpl-beauty-gb", "tpl-petcare-gb",
          "tpl-funeral-gb", "tpl-medspa-gb"],                      # other services
    "T": ["tpl-barber-gb", "tpl-beauty-gb"],                       # households as employers
    "H": ["tpl-gig-driver-gb"],                                    # transport & storage
    "R": [],  # arts/entertainment — no template yet
    "C": [],  # manufacturing — out of SMB-agent scope
    "L": [],  # real estate — deferred (vacancies falling)
    "K": [],  # finance/insurance — out of scope
    "J": [],  # info/comms — not a local-business vertical
}


class ONSClient:
    """Discovery-first client for the keyless ONS beta API."""

    def __init__(self, fetch: Callable[[str], Any] | None = None):
        self._fetch = fetch or _http_fetch

    def list_datasets(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        data = self._fetch(f"{ONS_BASE}/datasets?limit={limit}&offset={offset}")
        return data.get("items", [])

    def search_datasets(self, keyword: str, limit: int = 200) -> list[dict[str, Any]]:
        """Client-side substring search (API has no server-side search)."""
        kw = keyword.lower()
        found: list[dict[str, Any]] = []
        offset = 0
        while len(found) < limit:
            batch = self.list_datasets(limit=100, offset=offset)
            if not batch:
                break
            for d in batch:
                hay = f"{d.get('id', '')} {d.get('title', '')} {d.get('description', '')}".lower()
                if kw in hay:
                    found.append(d)
            offset += 100
            if len(batch) < 100:
                break
        return found[:limit]

    def get_dataset(self, dataset_id: str) -> dict[str, Any]:
        return self._fetch(f"{ONS_BASE}/datasets/{dataset_id}")

    def get_observations(self, dataset_id: str, dimensions: dict[str, str]) -> Any:
        """One observation; exactly one dimension may be '*' (wildcard)."""
        qs = "&".join(f"{k}={urllib.parse.quote(v, safe='*')}" for k, v in dimensions.items())
        return self._fetch(
            f"{ONS_BASE}/datasets/{dataset_id}/editions/time-series/versions/latest/observations?{qs}")


class NomisClient:
    """Client for the keyless Nomis labour-market API (flat JSON)."""

    def __init__(self, fetch: Callable[[str], Any] | None = None, uid: str | None = None):
        self._fetch = fetch or _http_fetch
        self._uid = uid

    def _url(self, path: str, params: dict[str, str]) -> str:
        if self._uid:
            params = {**params, "uid": self._uid}
        return f"{NOMIS_BASE}/{path}?{urllib.parse.urlencode(params)}"

    def search_datasets(self, keyword: str) -> Any:
        return self._fetch(self._url("dataset/def.sdmx.json", {"search": f"*{keyword}*"}))

    def resolve_geography(self, dataset: str, name: str) -> Any:
        return self._fetch(self._url(f"dataset/{dataset}/geography.json",
                                     {"search": f"{name}*"}))

    def get_data(self, dataset: str, params: dict[str, str]) -> list[dict[str, Any]]:
        data = self._fetch(self._url(f"dataset/{dataset}.data.json", params))
        return data.get("obs", [])

    def claimant_count_latest(self) -> Evidence | None:
        """Latest claimant count (NM_1_1). Geography is whatever the dataset
        returns — verified England-level JSA; do NOT label UK unless the
        response description confirms it. See PEER_REVIEW audit."""
        obs = self.get_data("NM_1_1", {
            "geography": "2092957699",  # verified: England
            "sex": "7",                 # all persons
            "item": "1",                # claimant count
            "measures": "20100",        # value
            "time": "latest",
        })
        if not obs:
            return None
        return Evidence(metric="claimant_count_england_jsa", value=obs[0].get("obs_value"),
                        unit="persons", source="Nomis NM_1_1 (ONS Crown Copyright)",
                        dataset="NM_1_1")

    def claimant_count_uk_latest(self) -> Evidence | None:
        """Kept for compatibility; currently England-level. Prefer claimant_count_latest."""
        return self.claimant_count_latest()


def template_priority(vacancies_by_sic: dict[str, float]) -> list[tuple[str, float]]:
    """Rank templates by vacancy weight of their SIC sections.

    vacancies_by_sic: {"Q": 5090, "G": 4629, ...} (any consistent unit).
    Returns [(template_id, score)] sorted desc. Templates spanning
    sections sum their sections' weights.
    """
    scores: dict[str, float] = {}
    for sic, weight in vacancies_by_sic.items():
        for tid in SIC_TO_TEMPLATES.get(sic, []):
            scores[tid] = scores.get(tid, 0.0) + weight
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
