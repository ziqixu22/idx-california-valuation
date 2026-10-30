# Sacramento Residential Valuation & Pricing Intelligence — foundation

Independent public-data reproduction inspired by an IDX Exchange business scenario. **Phase 0 is NO-GO for model work.** The official ArcGIS HTML describes a 2015–2018 sales layer; live JSON counts, transaction semantics, and reuse rights remain unverified. No model or present-day valuation claim is made.

## Roadmap

| Phase | Deliverable | Gate / risk |
|---|---|---|
| 0 | Source audit, provenance, GO/NO-GO | Live counts, label meaning, lawful reuse; blocked here |
| 1 | CLI, pagination, Bronze/Silver interfaces, fixtures, CI | Mock tests and reproducible audit; full ingestion gated |
| 2–4 | Point-in-time Gold, temporal baselines, GBDT | Only after Phase 0 GO; leakage and temporal drift |
| 5–8 | DL benchmark, SHAP/comps, intervals, review queue | Same frozen test; no causal SHAP claims |
| 9 | Causal feasibility | Credible preperiod/control required; optional NO-GO |
| 10–12 | Demo, randomized study, release | Study needs actual participants; claims require evidence |

## Run

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). From this directory:

The current environment installs only audit/Parquet tooling. GeoPandas, modeling, PyTorch, MLflow, and FastAPI enter the lockfile with their dependent phases.

```bash
uv sync --extra dev
uv run idxavm audit-data
uv run --extra dev pytest -q
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
```

`audit-data` exits 2 and writes `reports/data_audit.{json,md}` if the API is unavailable. It makes a full, paginated scan only when reachable. The output contains aggregate counts and metadata hash, not individual parcel records. `uv run idxavm ingest --source sacramento --reuse-approved` is deliberately blocked unless the audit is complete, its reviewed decision is GO, and the operator has verified lawful bulk reuse. Bronze snapshots and Silver Parquet are ignored by Git; Gold awaits Phase 2. Do not use the flag as a substitute for actual permission.

## Decisions

The official layer uses `INDICATED_SALES_PRICE`, a string whose market-price semantics are unproven; assessed values and Zillow Prize `logerror` are not substitute labels. County assessor materials state market comparable sales collected by the assessor are confidential. See [audit](reports/data_audit.md), [data sources](docs/data_sources.md), and [phase status](PHASE_STATUS.md). All fixture rows are **SYNTHETIC**.

