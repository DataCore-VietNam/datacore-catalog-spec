# datacore-catalog-spec

Open specification for the DataCore data catalog. Defines how **domains**,
**products**, **datasets**, and **columns** are described in YAML, plus JSON
Schemas to validate them.

This is what makes the catalog **community-contributable**: anyone can
describe a Vietnamese financial dataset in this format and submit it via PR.

## Taxonomy

```
domain        e.g., financial
  product     e.g., vn-equity
    dataset   e.g., equity.vn30.daily
      column  e.g., trade_date
```

## Schema files

- `schema/domain.schema.json` - top-level domain (Financial, Alternative,
  Economic, ESG, Reference, Real Estate). Required: `id`, `name`,
  `description`. Optional: `icon`, `tags`.
- `schema/product.schema.json` - a product within a domain (e.g., VN Equity,
  VN Macro). Required: `id`, `name`, `domain`, `description`. Optional:
  `vendor`, `coverage`, `tags`.
- `schema/dataset.schema.json` - a single dataset. Required: `id`, `name`,
  `domain`, `product`, `description`, `schema`. Optional includes `version`,
  `license`, `update_frequency`, `pii`, `coverage`, `cardinality`,
  `primary_key`, `time_column`, `partition_columns`, `tags`, `source`.
- `schema/column.schema.json` - a single column. Required: `name`, `type`.
  Optional: `description`, `nullable`, `unit`, `enum`, `format`, `examples`.

## Example

```yaml
# examples/equity-vn30-daily.yaml
id: equity.vn30.daily
name: VN30 Daily Prices
domain: financial
product: vn-equity
description: Daily OHLCV for VN30 index constituents.
license: proprietary
update_frequency: daily
coverage:
  start: "2012-02-06"
  end: rolling
  geographies: [VN]
schema:
  - name: trade_date
    type: date
    description: Trading date
  - name: ticker
    type: string
    description: HOSE ticker symbol
  - name: open
    type: float
  - name: close
    type: float
  - name: volume
    type: integer
```

See `examples/` for datasets across financial, alternative, economic, ESG, and
real estate domains. See `examples/domains/` and `examples/products/` for
domain/product definitions.

## Validate

Single file (schema auto-detected from path):

```bash
pip install -r requirements.txt
python scripts/validate.py examples/equity-vn30-daily.yaml
```

Override the detected schema explicitly:

```bash
python scripts/validate.py --type product examples/products/vn-equity.yaml
```

Validate every YAML under `examples/` (used by CI):

```bash
python scripts/validate_all.py
# or
make validate
```

## Schema versioning

The spec is currently at **v0.1**. While we're in `0.x`:

- **Patch bumps** (`0.1.0` → `0.1.1`) cover documentation and bug fixes.
- **Minor bumps** (`0.1.0` → `0.2.0`) may include backward-incompatible
  schema changes.
- Once we hit `1.0`, we follow strict semver and breaking changes will bump
  the major version.

The current spec version is recorded in `CHANGELOG.md`. Individual datasets
can also carry their own `version` field - bump it when the dataset's logical
schema changes in a breaking way.

## Why YAML

- **Human-readable.** Catalog entries are documentation as much as they are
  configuration. Anyone - analyst, PM, journalist - can read and edit them
  without learning a tool.
- **Diff-able in git.** Reviews on GitHub show meaningful per-field diffs
  rather than the noise of reformatted JSON.
- **Easy for non-engineers to contribute.** Submitting a new dataset is a
  matter of editing a text file and opening a PR - no API, no upload form,
  no proprietary client required.

JSON Schema runs underneath to keep things rigorous; YAML is just the
ergonomic surface.

## Contributing a dataset

1. Fork this repo
2. Add your YAML under `examples/` (or `examples/domains/` /
   `examples/products/` for those types)
3. Run `python scripts/validate.py path/to/your.yaml`
4. Submit a PR - CI will run `validate_all.py` on every PR

## Live catalog + site

The catalog shown on datacore.vn is pulled directly from the public demo API
(`gateway.datacore.vn/data/group`), so this repo never hand-maintains the
taxonomy:

```bash
python scripts/fetch_catalog.py --out catalog   # or: make fetch
# writes catalog/catalog.json + catalog/SNAPSHOT.md (domains > products > datasets, EN + VN)

python scripts/build_site.py --out site          # or: make site
# renders catalog/catalog.json into a self-contained site/index.html
```

`catalog/catalog.json` is the versioned snapshot of the real catalog. The site
(`Taxonomy`, `Datasets`, `Dashboard`, `Schemas` views) is generated from it.

Automation:

- `.github/workflows/refresh-catalog.yml` runs monthly (1st, 08:00 ICT) and on
  demand. It re-fetches the live catalog and commits `catalog/` if it changed.
- `.github/workflows/pages.yml` rebuilds and deploys the site to GitHub Pages on
  every push to `main` (including the monthly snapshot commit).

So the catalog stays in sync with datacore.vn with no manual step: the live API
is the single source of truth.

## License

MIT (the spec itself; datasets retain their own licenses)
