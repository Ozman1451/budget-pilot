# Decisions log (unattended build)

Choices made without asking, with the reason for each.

## Environment
1. **conda env `budget-pilot`, Python 3.11, from conda-forge**, includes `openjdk=17` (Spark 4.x needs Java 17+) and
   `nodejs=22` so the frontend toolchain also lives inside the env. `mrjob`, `google-genai` and `playwright` come from pip
   inside the env (`environment.yml`).
2. **Commands use `conda run -n budget-pilot …`** (Makefile `RUN`), so nothing depends on `conda activate` or `~/.bashrc`.
3. Your `.env` (copied from Project 3) contains `DATASET=synthetic`. To avoid that collision, the app setting is named
   **`BP_DATASET`**. I did **not** edit `.env`.

## Data
4. **Period 2025-11-01 → 2026-10-31** (12 full months before today), so it covers 11.11, White Friday, 12.12, Ramadan/Eid ul
   Fitr (≈20 Mar 2026), Eid ul Adha (≈27 May 2026) and 14 August.
5. **Business scale ≈ Rs 33K/day (≈ Rs 1M/month)**, so "the next Rs 1M" is about a month of spend and the optimizer stays
   inside the range of the data instead of extrapolating.
6. **Rows are breakdown rows of the same business**: more `--rows` means finer granularity, the same daily totals. This keeps
   all sizes comparable and lets the benchmark scale without changing the story.
7. Generator writes **whole platform-days per chunk** (default 500K rows), so in-day normalisation is exact and RAM stays
   bounded at 10M. Strings are written as Parquet dictionary columns. CSV is written by default only for ≤10K rows; the
   benchmark creates CSVs for other sizes on demand (chunked).
8. True response parameters were tuned so the current mix (FB 32%, IG 22%, Google 14%, TikTok 17%, YouTube 15%) is
   clearly sub-optimal (~10% uplift available). Otherwise the demo would show a ~1% change and nothing to talk about.
9. Did **not** generate 1M/10M datasets (as instructed). Generation speed measured: 100K rows in 0.3s.

## KPIs / optimizer
10. **Profit = revenue − ad spend** (media profit); there is no COGS in the schema.
11. **Horizon 30 days** by default (adjustable 7–90 in the UI, `horizon_days` in the tool).
12. **Default caps: min 5%, max 60% per platform**, so no platform is switched off entirely or gets everything.
13. **Allocation by KKT water-filling** (equal marginal ROAS, bisection on λ) rather than generic `scipy.optimize.minimize`.
    It is exact for this concave separable problem, sums to the budget to the rupee, and is fast enough for 100 bootstrap
    re-optimisations.
14. **Audience filters rescale the platform curve** by ROAS(audience)/ROAS(platform) instead of fitting a curve on the
    filtered daily data, which is too thin and would be extrapolated 10–30× beyond its range.
15. Bootstrap: 100 iterations for `optimize_budget` / Optimizer page (~3s on 100K rows, cached per argument set).
    `compare_scenarios` uses 50 per scenario to keep chat responsive.

## Benchmark
16. **Main comparison uses the same CSV input for all three engines** (mrjob can only read text). Pandas and Spark are also
    timed on Parquet as extra lines, to show the columnar-format effect.
17. **Wall time measured outside the process** (subprocess launch → exit), so Spark's JVM start-up and mrjob's process
    spawning count. Job-internal compute time and Spark start-up are recorded separately.
18. **Peak memory = sampled RSS (every 50 ms) of the whole process tree**, including the JVM and mrjob worker processes.
19. Timeout 600s per run (`--timeout`). A failure or timeout is recorded and the remaining runs for that engine/size are skipped.
20. `run_all.py` **merges** into `bench/results.csv` by (engine, rows), so `make bench` later adds 1M/10M rows without losing
    the 10K/100K ones.
21. I ran the benchmark a second time with nothing else running, because my first run overlapped an `npm install`. The final
    numbers in the README come from the clean run.

## App
22. **Same stack as Project 3**: FastAPI backend (:8000) + Next.js 15 frontend (:3000), ECharts, framer-motion, dark theme.
23. Four routes: `/` Chat (home), `/dashboard`, `/optimizer`, `/lab`. The chat thread is kept in a React provider, so
    switching tabs doesn't lose it.
24. Charts render **inline under each chat answer**. Project 3 used a side canvas; the spec asks for inline.
25. A fifth prompt chip was added ("How did Spark compare to Pandas and MapReduce?") to show `get_benchmark` from chat.
26. Default dataset for the app: **100K** rows (loads in <1s; the 10M file would need ~1–2 GB of RAM in Pandas).
27. Gemini model: `GEMINI_CHAT_MODEL` from your `.env` (`gemini-3.6-flash`); default in code is the same.
28. `MOCK_CHAT=1` gives an offline keyword router that calls the same tools. Used by tests, and useful if Gemini is
    rate-limited while recording.
29. "When to use which" text on the Lab page is **generated from the measured numbers by rules** (no LLM), so it can't
    claim something the data doesn't show (e.g. it says Parquet made no difference at 100K because it didn't).

## Testing / screenshots
30. Tests never call Gemini (mock router). Gemini was smoke-tested a few times (≈6 calls total) via `/api/chat` and the chat
    screenshot.
31. Screenshots use `playwright-core` (already a Project 3 dev dependency) with the **system Google Chrome**, so no browser
    download and no sudo.
