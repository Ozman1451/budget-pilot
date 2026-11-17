# Claude Code one-shot prompt — Project 2: "Budget Pilot"

> Paste everything below the line into Claude Code, started in a NEW empty folder
> (e.g. `~/projects/budget-pilot`). Replace `/home/ozmen/Downloads/BDA/projects/project3` with your Need Map Chat folder.

---

You are building **Budget Pilot**, a Big Data Analytics course project: a chat-first
Digital Advertising Budget Optimizer that answers management's question
**"Where should we spend the next Rs. 1,000,000?"** across Facebook, Instagram,
Google, TikTok and YouTube.

## 0. Reuse Project 3 first (do this before writing any code)
My previous project "Need Map Chat" is at `/home/ozmen/Downloads/BDA/projects/project3`. Read it first and REUSE:
- the same framework / app structure, styling, theme, layout and components
- the Gemini API chat layer (client setup, `.env` handling with `GEMINI_API_KEY`, system prompt
  pattern, tool/function-calling pattern, chat UI component)
- the synthetic data generator pattern, project layout, README style, and conda env setup style
Copy and adapt those files rather than rewriting. Tell me in one short list what you reused.

IMPORTANT: Need Map Chat is Instagram-comment specific. Reuse only its **plumbing** (app shell, theme,
chat UI, Gemini client + function-calling loop, env/config, README/docs structure). Do NOT copy any
Instagram/Apify scraping, comment data, text embeddings or clustering logic. The data, tools and pages
here are entirely new (ad-campaign performance across 5 platforms). Replace Project 3's chat tools and
system prompt with the ones defined in section 6.

## 1. Environment
- Create a dedicated conda env `budget-pilot` (Python 3.11). Put ALL packages in it, nothing system-wide.
- Provide `environment.yml`. Needed extras beyond Project 3: `pyspark` (+ `openjdk=17` from conda-forge),
  `mrjob`, `pyarrow`, `scipy`, `plotly`, `faker`.
- No local LLMs. AI only via Gemini API.

## 2. Synthetic data (`data/generate.py`)
Columns: `date, campaign, platform, impressions, clicks, spend, conversions, revenue, age, gender, city, device`.
- Cities: Lahore, Karachi, Islamabad, Rawalpindi, Faisalabad, Multan, Peshawar. Currency: PKR.
- Age bands 18-24, 25-34, 35-44, 45-54, 55+; gender M/F; device mobile/desktop/tablet.
- 12 months of dates, ~40 campaigns with realistic names (e.g. "Eid Sale – Retargeting", "Winter Launch – Awareness").
- Make it REALISTIC, not uniform random: each platform has its own CTR, CVR, CPC and audience skew
  (TikTok → young/mobile, Google → high intent/high CVR, YouTube → cheap impressions/low CVR, etc.),
  seasonality (Eid, 11.11, Black Friday spikes), and **diminishing returns**: revenue grows like
  `a * log(1 + spend/b)` per platform so the optimizer has something real to find.
- CLI: `python data/generate.py --rows 10000|100000|1000000|10000000`, written in chunks to **Parquet**
  (also CSV for the 10K file). Vectorized NumPy, must make 10M rows in reasonable time without blowing RAM.

## 3. KPI engine (`engine/kpis.py`)
CTR, CPC, CPA, conversion rate, ROAS, revenue, profit, by platform / campaign / city / age / gender /
device / month. Safe division (no inf/NaN in output).

## 4. Big Data benchmark (`bench/`) — REAL measurements only
Compute the same platform-level KPI aggregation three ways and time it at 10K, 100K, 1M, 10M rows:
1. **Pandas** (`bench/pandas_job.py`)
2. **MapReduce** with `mrjob` running in local mode (`bench/mr_job.py`) — mapper emits
   `(platform, [impressions, clicks, spend, conversions, revenue])`, combiner + reducer sum, KPIs computed after.
3. **PySpark** local mode (`bench/spark_job.py`)
- `bench/run_all.py` runs all sizes × engines, 3 runs each, records median wall time + peak memory to
  `bench/results.csv`. If an engine fails or exceeds a timeout at a size, record it as `failed/timeout`
  — never invent numbers. Verify all three engines produce identical KPI values (assert, tolerance 1e-6).
- Allow `--max-rows` so I can skip 10M if my laptop struggles.

## 5. Budget Recommendation Engine (`engine/optimizer.py`)
- Fit a diminishing-returns response curve per platform (`revenue = a*log(1+spend/b)`, scipy `curve_fit`)
  on daily spend vs revenue.
- Allocate a given budget (default Rs. 1,000,000) to maximize predicted revenue using marginal-ROAS
  greedy allocation or `scipy.optimize` with constraints: min/max % per platform (user-adjustable),
  optional target audience filter (e.g. city=Lahore, age 18-24).
- Output: % and PKR per platform, predicted revenue, predicted ROAS, uplift vs. "current mix" and vs.
  "equal split", and a plain-language reason per platform.
- Also a bootstrap confidence band (resample days, refit, ~100 iterations) so it shows a range, not fake precision.

## 6. App (same framework/theme as Project 3)
Pages/tabs:
1. **Chat (home)** — Gemini chat as the main interface, with function-calling tools:
   `get_kpis(filters, group_by)`, `optimize_budget(budget, min_pct, max_pct, filters)`,
   `compare_scenarios(...)`, `get_benchmark()`. Answers must come from tool results, include small inline
   charts/tables. Suggested prompt chips: "Where should the next Rs. 1M go?", "What if TikTok is capped at 10%?",
   "Best platform for Karachi 18-24 on mobile?", "Why is Google better than YouTube?".
2. **Dashboard** — KPI cards, platform comparison, ROAS trend by month, city × platform heatmap, funnel
   (impressions → clicks → conversions).
3. **Optimizer** — budget input, min/max sliders per platform, animated donut of the allocation,
   response-curve chart per platform with the chosen spend point marked, current vs. recommended bar chart.
4. **Big Data Lab** — benchmark results: log-scale line chart time vs. rows for Pandas / MapReduce / Spark,
   memory chart, table, and a short auto-written "when to use which" explanation.
- Polished dark theme matching Project 3, smooth transitions, loading states, no broken empty states.

## 7. Deliverables
- `README.md`: title + one-line pitch, problem, screenshots placeholders (`docs/screens/*.png`),
  architecture diagram (Mermaid), data schema, KPI formulas, optimizer method, benchmark table
  (filled from `bench/results.csv` by a script `bench/to_readme.py`), setup (conda) and run commands,
  limitations (synthetic data, local Spark ≠ cluster), future work.
- `Makefile` or `run.sh` with: `setup`, `data`, `bench`, `app`.
- `docs/DEMO_SCRIPT.md`: a 3-minute screen-recording script (what to click, what to type in chat, what to say)
  and a 45-second "brag video" shot list.
- Small tests: KPI formulas, optimizer respects constraints and sums to budget, engines agree.

## 8. Working rules
- Build it end to end in one go; run the generator at 10K/100K, run the tests, launch the app once
  and fix errors before telling me you're done. Leave 1M/10M + full benchmark for me to run via `make bench`.
- Don't ask me questions unless blocked; make sensible choices and list them at the end.
- Finish with: what you reused from Project 3, exact commands to run, and anything I must fill in (API key).

## 9. UNATTENDED RUN — I am asleep, nobody will answer
- Never stop to ask me anything and never end your turn until sections 1-8 are done or truly blocked. For every choice, pick the sensible default and log it in `docs/DECISIONS.md`.
- Safety: only write inside this project folder. The Project 3 folder is READ-ONLY: never modify, move or delete anything there. No sudo, no apt, no system-wide installs, no editing ~/.bashrc or global configs, no git push, no deleting anything outside this folder. All packages go into conda env `budget-pilot`; use `conda run -n budget-pilot ...` if `conda activate` doesn't work in your shell.
- Reuse filter: after reading Project 3, write what you reused to `docs/REUSED.md`. Reuse plumbing only. Never copy Instagram, Apify, scraping, embeddings or clustering code.
- API key: if `.env` has GEMINI_API_KEY, use it. If it's missing, create `.env.example`, build everything anyway, make the chat show a clear "Add GEMINI_API_KEY" banner instead of crashing, and add it to MORNING_TODO. Never print the key in logs or files. Keep Gemini test calls to a few smoke tests (rate limits).
- Errors: when something fails, read the error, fix it, and retry with up to 3 different approaches. If it still fails, isolate it (skip that piece, keep everything else working) and record it in MORNING_TODO with the error and what you tried. Never fake results or hardcode benchmark numbers.
- Spark/Java: install openjdk via conda inside the env. If Spark still won't run, keep Pandas + MapReduce working, show Spark as "not run" in the app, and add it to MORNING_TODO.
- Heavy runs: generate only the 10K and 100K datasets and benchmark only those sizes, so the README has real numbers. Do NOT generate 1M/10M; leave `make bench` for me. If any single command runs over ~15 minutes, kill it and use a smaller size.
- App testing: start the app in the background only to smoke-test it (main pages return HTTP 200, no errors in logs), then stop it. Never leave a blocking server running.
- Screenshots: if you can, take headless screenshots of each page (e.g. Playwright inside the conda env) into `docs/screens/`. If it needs sudo or fails, skip it and add a TODO.
- When finished, write `MORNING_TODO.md` in the project root containing: (1) what's done, (2) numbered list of what needs me, with copy-paste commands, (3) known issues, (4) commands to run the app and the full benchmark, (5) a recording checklist pointing to `docs/DEMO_SCRIPT.md`. This is the first file I'll read.
