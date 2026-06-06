.PHONY: install validate fetch site

install:
	pip install -r requirements.txt

validate:
	python scripts/validate_all.py

fetch:
	python scripts/fetch_catalog.py --out catalog

site:
	python scripts/build_site.py --out site
