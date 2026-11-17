# Budget Pilot — every command runs inside the conda env `budget-pilot` (no activation needed).
SHELL := /bin/bash
ENV   ?= budget-pilot
RUN   := conda run --no-capture-output -n $(ENV)
MAX_ROWS ?=
RUNS  ?= 3

.PHONY: setup data data-big bench bench-small readme app backend frontend test lint build verify shots clean-big

setup:            ## create/update the conda env + install frontend packages (local node_modules)
	conda env update -n $(ENV) -f environment.yml --prune || conda env create -f environment.yml
	cd frontend && $(RUN) npm install --no-audit --no-fund
	@test -f .env || (cp .env.example .env && echo "created .env from .env.example — add GEMINI_API_KEY")

data:             ## 10K (+CSV) and 100K rows
	$(RUN) python data/generate.py --rows 10000
	$(RUN) python data/generate.py --rows 100000

data-big:         ## 1M and 10M rows (Parquet, chunked)
	$(RUN) python data/generate.py --rows 1000000
	$(RUN) python data/generate.py --rows 10000000

bench:            ## full benchmark: 10K → 10M (make bench MAX_ROWS=1000000 to skip 10M)
	$(RUN) python bench/run_all.py --runs $(RUNS) $(if $(MAX_ROWS),--max-rows $(MAX_ROWS),)
	$(RUN) python bench/to_readme.py

bench-small:      ## 10K + 100K only
	$(RUN) python bench/run_all.py --runs $(RUNS) --max-rows 100000
	$(RUN) python bench/to_readme.py

readme:           ## refresh the benchmark table in README.md from bench/results.csv
	$(RUN) python bench/to_readme.py

app:              ## backend :8000 + frontend :3000 (Ctrl-C stops both)
	trap 'kill 0' EXIT; \
	$(RUN) uvicorn app.main:app --port 8000 --app-dir backend & \
	(cd frontend && $(RUN) npm run dev -- --port 3000) & \
	wait

backend:
	$(RUN) uvicorn app.main:app --reload --port 8000 --app-dir backend

frontend:
	cd frontend && $(RUN) npm run dev -- --port 3000

test:             ## pytest (KPIs, optimizer constraints, engines agree, API) + frontend lint
	$(RUN) python -m pytest
	cd frontend && $(RUN) npm run lint

build:
	cd frontend && $(RUN) npm run build

verify: test build

shots:            ## headless screenshots of every page → docs/screens/ (uses system Chrome)
	cd frontend && $(RUN) npm run shot

clean-big:        ## delete the 1M/10M data files
	rm -f data/ads_1m.* data/ads_10m.*
