#!/usr/bin/env python3
"""Render the live DataCore catalog snapshot into a static site.

Reads catalog/catalog.json (produced by scripts/fetch_catalog.py from the real
datacore.vn API) and the JSON Schemas under schema/, then writes a single
self-contained site/index.html with four views:

  1. Taxonomy   - domain > product > dataset tree, searchable
  2. Datasets   - one card per dataset (EN + VN description, code, domain/product)
  3. Dashboard  - counts per domain/product, freshness, empty-domain flags
  4. Schemas    - the catalog-spec JSON Schemas (field reference)

No external assets: data, CSS, JS are inlined, so the page works from file://
and from GitHub Pages.

Usage:
    python scripts/build_site.py [--out site]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_JSON = REPO_ROOT / "catalog" / "catalog.json"
SCHEMA_DIR = REPO_ROOT / "schema"

SCHEMA_FILES = {
    "domain": "domain.schema.json",
    "product": "product.schema.json",
    "dataset": "dataset.schema.json",
    "column": "column.schema.json",
}


def schema_fields(schema: dict):
    req = set(schema.get("required", []))
    rows = []
    for name, spec in (schema.get("properties", {}) or {}).items():
        t = spec.get("type")
        if isinstance(t, list):
            t = " | ".join(t)
        if spec.get("type") == "array":
            items = spec.get("items", {})
            it = items.get("type") or (items.get("$ref", "").split("/")[-1] if "$ref" in items else "")
            t = f"array<{it}>" if it else "array"
        if not t and "enum" in spec:
            t = "enum"
        rows.append({
            "name": name, "type": t or "",
            "required": name in req,
            "description": spec.get("description", ""),
        })
    rows.sort(key=lambda r: (not r["required"], r["name"]))
    return rows


def load_schemas():
    out = {}
    for key, fname in SCHEMA_FILES.items():
        fp = SCHEMA_DIR / fname
        if fp.exists():
            out[key] = schema_fields(json.loads(fp.read_text(encoding="utf-8")))
    return out


def render(catalog: dict, schemas: dict) -> str:
    payload = {"catalog": catalog, "schemas": schemas}
    data_json = json.dumps(payload, ensure_ascii=False, default=str).replace("</", "<\\/")
    return _PAGE.replace("__DATA__", data_json)


_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DataCore Catalog</title>
<style>
  :root{--bg:#0f1419;--panel:#161c24;--panel2:#1d2530;--line:#2a3440;--txt:#e6edf3;
    --muted:#8b98a5;--accent:#3fb6ff;--accent2:#7ee787;--warn:#f0883e;--bad:#ff6b6b;--chip:#243140;}
  @media (prefers-color-scheme: light){:root{--bg:#f6f8fa;--panel:#fff;--panel2:#f0f3f6;--line:#d8dee4;
    --txt:#1f2328;--muted:#636c76;--accent:#0969da;--accent2:#1a7f37;--warn:#bc4c00;--bad:#cf222e;--chip:#eaeef2;}}
  *{box-sizing:border-box}
  body{margin:0;font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--txt)}
  header{padding:20px 24px;border-bottom:1px solid var(--line);background:var(--panel)}
  header h1{margin:0;font-size:18px}
  header .sub{color:var(--muted);font-size:12px;margin-top:4px}
  .tabs{display:flex;gap:2px;padding:0 16px;background:var(--panel);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5;flex-wrap:wrap}
  .tab{padding:11px 16px;cursor:pointer;color:var(--muted);border-bottom:2px solid transparent;font-weight:600}
  .tab:hover{color:var(--txt)} .tab.active{color:var(--accent);border-bottom-color:var(--accent)}
  main{padding:22px;max-width:1180px;margin:0 auto}
  .view{display:none} .view.active{display:block}
  input.search{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--txt);margin-bottom:14px;font-size:14px}
  .chip{display:inline-block;padding:2px 8px;border-radius:999px;background:var(--chip);color:var(--muted);font-size:11px;margin:2px 4px 2px 0;white-space:nowrap}
  .chip.key{color:var(--accent)} .chip.ok{color:var(--accent2)} .chip.warn{color:var(--warn)}
  details.dom{border:1px solid var(--line);border-radius:10px;margin-bottom:10px;background:var(--panel);overflow:hidden}
  details.dom>summary{padding:12px 14px;font-weight:700;font-size:15px;cursor:pointer;list-style:none}
  details.prod{margin:0 0 0 18px;border-left:2px solid var(--line)}
  details.prod>summary{padding:8px 14px;cursor:pointer;font-weight:600;list-style:none}
  summary::-webkit-details-marker{display:none}
  summary:before{content:"\25B8";color:var(--muted);margin-right:8px;display:inline-block;transition:transform .15s}
  details[open]>summary:before{transform:rotate(90deg)}
  .ds-row{margin:0 0 0 36px;padding:7px 12px;border-left:2px solid var(--line)}
  .ds-row .id{color:var(--muted);font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}
  .ds-row .d{color:var(--muted);font-size:12.5px;margin-top:2px}
  .count{color:var(--muted);font-weight:500;font-size:12px}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}
  .card{border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:14px}
  .card h3{margin:0 0 2px;font-size:15px}
  .card .id{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;color:var(--muted)}
  .card p{color:var(--muted);font-size:13px;margin:8px 0 0}
  .card p.vi{font-style:italic}
  table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px}
  th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
  th{color:var(--muted);font-weight:600}
  .mono{font-family:ui-monospace,Menlo,Consolas,monospace}
  .stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;margin-bottom:18px}
  .stat{border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:16px}
  .stat .n{font-size:28px;font-weight:700} .stat .l{color:var(--muted);font-size:12px;margin-top:2px}
  .bar{height:8px;border-radius:6px;background:var(--panel2);overflow:hidden}
  .bar>i{display:block;height:100%;background:var(--accent)}
  .section{border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:16px;margin-bottom:16px}
  .section h2{margin:0 0 10px;font-size:14px}
  .muted{color:var(--muted)}
</style>
</head>
<body>
<header>
  <h1>DataCore Catalog</h1>
  <div class="sub">Live snapshot from <span class="mono" id="src"></span>. Generated <span id="gen"></span>.</div>
</header>
<nav class="tabs">
  <div class="tab active" data-view="taxonomy">Taxonomy</div>
  <div class="tab" data-view="datasets">Datasets</div>
  <div class="tab" data-view="dashboard">Dashboard</div>
  <div class="tab" data-view="schemas">Schemas</div>
</nav>
<main>
  <section id="taxonomy" class="view active">
    <input class="search" id="taxSearch" placeholder="Filter domains, products, datasets...">
    <div id="taxTree"></div>
  </section>
  <section id="datasets" class="view">
    <input class="search" id="dsSearch" placeholder="Filter datasets by name, code, domain, product...">
    <div class="grid" id="cards"></div>
  </section>
  <section id="dashboard" class="view"><div id="dash"></div></section>
  <section id="schemas" class="view"><div id="schemaDocs"></div></section>
</main>
<script>
const DATA=__DATA__;
const C=DATA.catalog;
const esc=s=>(s==null?"":String(s)).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));
document.getElementById("src").textContent=C.source||"";
document.getElementById("gen").textContent=C.generatedAtIct||C.generatedAtUtc||"";
const chip=(t,c)=>`<span class="chip ${c||''}">${esc(t)}</span>`;

document.querySelectorAll(".tab").forEach(t=>t.onclick=()=>{
  document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
  document.querySelectorAll(".view").forEach(x=>x.classList.remove("active"));
  t.classList.add("active");document.getElementById(t.dataset.view).classList.add("active");
});

function eachProduct(fn){for(const dt of C.domainTypes){const node=C.domains[dt];(node.products||[]).forEach(p=>fn(dt,node,p));}}

/* taxonomy */
function renderTax(){
  let h="";
  for(const dt of C.domainTypes){
    const node=C.domains[dt];const prods=node.products||[];
    const ds=prods.reduce((a,p)=>a+(p.datasets||[]).length,0);
    h+=`<details class="dom" open><summary>${esc(node.label||dt)} <span class="count">${prods.length} product(s), ${ds} dataset(s)</span></summary>`;
    if(!prods.length) h+=`<div class="ds-row muted">No published products.</div>`;
    for(const p of prods){
      h+=`<details class="prod" open><summary>${esc(p.name)} <span class="count">${(p.datasets||[]).length} dataset(s)</span></summary>`;
      for(const d of (p.datasets||[])){
        h+=`<div class="ds-row"><strong>${esc(d.name)}</strong> <span class="id">${esc(d.code||"")}</span>`
          +(d.description?`<div class="d">${esc(d.description)}</div>`:"")+`</div>`;
      }
      h+=`</details>`;
    }
    h+=`</details>`;
  }
  document.getElementById("taxTree").innerHTML=h;
}
document.getElementById("taxSearch").addEventListener("input",e=>{
  const q=e.target.value.toLowerCase();
  document.querySelectorAll("#taxTree .ds-row").forEach(r=>{r.style.display=(!q||r.textContent.toLowerCase().includes(q))?"":"none";});
  document.querySelectorAll("#taxTree details.prod").forEach(p=>{const any=[...p.querySelectorAll(".ds-row")].some(r=>r.style.display!=="none");p.style.display=(!q||any||p.textContent.toLowerCase().includes(q))?"":"none";if(q&&any)p.open=true;});
  document.querySelectorAll("#taxTree details.dom").forEach(d=>{const any=[...d.querySelectorAll("details.prod")].some(p=>p.style.display!=="none");d.style.display=(!q||any||d.textContent.toLowerCase().includes(q))?"":"none";if(q&&any)d.open=true;});
});

/* dataset cards */
function renderCards(){
  let cards=[];
  eachProduct((dt,node,p)=>{(p.datasets||[]).forEach(d=>{
    const search=(d.name+" "+d.code+" "+node.label+" "+p.name).toLowerCase();
    cards.push(`<div class="card" data-search="${esc(search)}">
      <h3>${esc(d.name)}</h3><div class="id">${esc(d.code||"")}</div>
      <div style="margin:6px 0">${chip(node.label)} ${chip(p.name)}</div>
      ${d.description?`<p>${esc(d.description)}</p>`:""}
      ${d.descriptionVi?`<p class="vi">${esc(d.descriptionVi)}</p>`:""}
    </div>`);
  });});
  document.getElementById("cards").innerHTML=cards.join("")||"<p class='muted'>No datasets.</p>";
}
document.getElementById("dsSearch").addEventListener("input",e=>{
  const q=e.target.value.toLowerCase();
  document.querySelectorAll("#cards .card").forEach(c=>{c.style.display=(!q||c.dataset.search.includes(q))?"":"none";});
});

/* dashboard */
function renderDash(){
  const perDomain=C.domainTypes.map(dt=>{const n=C.domains[dt];const ds=(n.products||[]).reduce((a,p)=>a+(p.datasets||[]).length,0);return{label:n.label||dt,products:(n.products||[]).length,datasets:ds};});
  const stat=(n,l)=>`<div class="stat"><div class="n">${esc(n)}</div><div class="l">${esc(l)}</div></div>`;
  let h=`<div class="stats">${stat(C.domainTypes.length,"Domains")}${stat(C.productsTotal,"Products")}${stat(C.datasetsTotal,"Datasets")}${stat(perDomain.filter(d=>d.products===0).length,"Empty domains")}</div>`;
  const empty=perDomain.filter(d=>d.products===0).map(d=>d.label);
  if(empty.length) h+=`<div class="section"><h2>Empty domains</h2><p>${empty.map(e=>chip(e,"warn")).join("")} <span class="muted">listed on the site but no published products yet.</span></p></div>`;
  const max=Math.max(1,...perDomain.map(d=>d.datasets));
  h+=`<div class="section"><h2>Products and datasets per domain</h2><table><thead><tr><th>Domain</th><th>Products</th><th>Datasets</th></tr></thead><tbody>`;
  for(const d of perDomain){h+=`<tr><td>${esc(d.label)}</td><td>${d.products}</td><td><div style="display:flex;align-items:center;gap:8px"><div class="bar" style="flex:1"><i style="width:${Math.round(100*d.datasets/max)}%"></i></div>${d.datasets}</div></td></tr>`;}
  h+=`</tbody></table></div>`;
  h+=`<div class="section"><h2>Freshness</h2><p class="muted">Snapshot generated ${esc(C.generatedAtIct||C.generatedAtUtc||"")} from ${esc(C.source||"the catalog API")}. Refreshed monthly by CI.</p></div>`;
  document.getElementById("dash").innerHTML=h;
}

/* schema docs */
function renderSchemas(){
  const labels={domain:"Domain",product:"Product",dataset:"Dataset",column:"Column"};
  let h=`<p class="muted">These are the catalog-spec JSON Schemas (the contract for catalog YAML). Catalog content above is fetched live from datacore.vn.</p>`;
  for(const key of ["domain","product","dataset","column"]){
    const rows=DATA.schemas[key];if(!rows)continue;
    h+=`<div class="section"><h2>${labels[key]} schema <span class="muted">(${key}.schema.json)</span></h2><table><thead><tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr></thead><tbody>`;
    for(const r of rows){h+=`<tr><td class="mono">${esc(r.name)}</td><td class="mono">${esc(r.type)}</td><td>${r.required?chip("required","key"):'<span class="muted">optional</span>'}</td><td>${esc(r.description)}</td></tr>`;}
    h+=`</tbody></table></div>`;
  }
  document.getElementById("schemaDocs").innerHTML=h;
}

renderTax();renderCards();renderDash();renderSchemas();
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="site")
    args = ap.parse_args()

    if not CATALOG_JSON.exists():
        print(f"ERROR: {CATALOG_JSON} not found. Run scripts/fetch_catalog.py first.",
              file=sys.stderr)
        return 1

    catalog = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
    schemas = load_schemas()
    html_out = render(catalog, schemas)

    out_dir = (REPO_ROOT / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html_out, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    print(f"Wrote {out_dir/'index.html'}")
    print(f"  {len(catalog['domains'])} domains, {catalog['productsTotal']} products, "
          f"{catalog['datasetsTotal']} datasets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
