#!/usr/bin/env python3
"""Fetch the live DataCore catalog from the public demo API and write a snapshot.

The datacore.vn demo is backed by a JSON gateway:

  GET /data/group/all                      -> all dataset groups (products)
  GET /data/group/all?domainType=<DOMAIN>  -> products in one domain
  GET /data/group/<id>                     -> datasets inside a product

This script walks those endpoints, sanitizes the text (strips HTML, decodes
entities, and replaces em/en dashes with ASCII hyphens per house style), and
writes:

  catalog/catalog.json   - structured snapshot (domains > products > datasets)
  catalog/SNAPSHOT.md    - human-readable summary

It is the source of truth for the catalog visualization: no hand-maintained
taxonomy, no guessing. Run monthly in CI.

Usage:
    python scripts/fetch_catalog.py [--base URL] [--out catalog]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

DEFAULT_BASE = "https://gateway.datacore.vn/data/group"

# Stable domain enum used by the demo. If DataCore adds a domain, add it here;
# any product the API returns that is not claimed by a listed domain is still
# captured under "_UNASSIGNED" so drift is visible rather than silently dropped.
DOMAIN_TYPES = ["ECONOMY", "LOCATION", "MARKET", "MEDIA", "ORGANIZATION", "PEOPLE"]

DOMAIN_LABELS = {
    "ECONOMY": "Economy",
    "LOCATION": "Location",
    "MARKET": "Market",
    "MEDIA": "Media",
    "ORGANIZATION": "Organization",
    "PEOPLE": "People",
    "_UNASSIGNED": "Unassigned",
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def clean(text: str | None) -> str:
    """Strip HTML, decode entities, drop dashes/nbsp, collapse whitespace."""
    if not text:
        return ""
    t = _TAG_RE.sub(" ", text)
    t = html.unescape(t)
    t = t.replace("\u2013", "-").replace("\u2014", "-")  # en dash, em dash -> hyphen
    t = t.replace(" ", " ").replace("﻿", "")    # nbsp, BOM/zero-width
    return _WS_RE.sub(" ", t).strip()


def get_json(url: str, retries: int = 3, timeout: int = 30):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise RuntimeError(f"GET failed after {retries} tries: {url} ({last})")


def data_of(payload):
    """The API wraps results as {status, message, httpCode, errorCode, data}."""
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"] or []
    return payload or []


def build_catalog(base: str) -> dict:
    # 1. master product list (id -> meta)
    all_groups = data_of(get_json(f"{base}/all"))
    meta = {}
    for g in all_groups:
        gid = g.get("id")
        meta[gid] = {
            "id": gid,
            "name": (g.get("name") or "").strip(),
            "description": clean(g.get("description")),
            "descriptionVi": clean(g.get("descriptionVi")),
            "datasetCount": g.get("count"),
        }

    # 2. domain -> [product ids]
    domain_ids: dict[str, list[int]] = {}
    claimed: set = set()
    for dt in DOMAIN_TYPES:
        ids = [g.get("id") for g in data_of(get_json(f"{base}/all?domainType={dt}"))]
        domain_ids[dt] = ids
        claimed.update(ids)

    # any product not claimed by a known domain
    unassigned = [gid for gid in meta if gid not in claimed]
    if unassigned:
        domain_ids["_UNASSIGNED"] = unassigned

    # 3. datasets per product
    def datasets_for(gid: int) -> list[dict]:
        out = []
        for d in data_of(get_json(f"{base}/{gid}")):
            out.append({
                "code": (d.get("dsCode") or "").strip(),
                "name": (d.get("dsName") or "").strip(),
                "description": clean(d.get("description")) or clean(d.get("overview")),
                "descriptionVi": clean(d.get("descriptionVi")) or clean(d.get("overviewVi")),
            })
        return out

    domains = {}
    for dt, ids in domain_ids.items():
        products = []
        for gid in sorted(ids):
            m = meta.get(gid, {"id": gid, "name": f"group-{gid}", "description": "",
                               "descriptionVi": "", "datasetCount": None})
            products.append({**m, "datasets": datasets_for(gid)})
        domains[dt] = {"label": DOMAIN_LABELS.get(dt, dt.title()), "products": products}

    products_total = sum(len(d["products"]) for d in domains.values())
    datasets_total = sum(len(p["datasets"]) for d in domains.values() for p in d["products"])

    now_utc = _dt.datetime.now(_dt.timezone.utc)
    return {
        "source": base,
        "generatedAtUtc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generatedAtIct": (now_utc + _dt.timedelta(hours=7)).strftime("%Y-%m-%d %H:%M ICT"),
        "domainTypes": list(domains.keys()),
        "productsTotal": products_total,
        "datasetsTotal": datasets_total,
        "domains": domains,
    }


def write_snapshot_md(catalog: dict, path: Path) -> None:
    lines = [
        "# DataCore catalog snapshot",
        "",
        f"Source: {catalog['source']}",
        f"Generated: {catalog['generatedAtIct']}",
        "",
        f"{len(catalog['domains'])} domains, {catalog['productsTotal']} products, "
        f"{catalog['datasetsTotal']} datasets.",
        "",
    ]
    for dt, node in catalog["domains"].items():
        lines.append(f"## {node['label']}")
        if not node["products"]:
            lines.append("")
            lines.append("_No published products._")
            lines.append("")
            continue
        for p in node["products"]:
            lines.append("")
            lines.append(f"### {p['name']} ({len(p['datasets'])} datasets)")
            for d in p["datasets"]:
                code = f" `{d['code']}`" if d["code"] else ""
                lines.append(f"- {d['name']}{code}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--out", default="catalog")
    args = ap.parse_args()

    try:
        catalog = build_catalog(args.base)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if catalog["productsTotal"] == 0:
        print("ERROR: API returned zero products; refusing to overwrite snapshot.",
              file=sys.stderr)
        return 1

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    write_snapshot_md(catalog, out / "SNAPSHOT.md")

    print(f"Wrote {out/'catalog.json'} and {out/'SNAPSHOT.md'}")
    print(f"  {len(catalog['domains'])} domains, {catalog['productsTotal']} products, "
          f"{catalog['datasetsTotal']} datasets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
