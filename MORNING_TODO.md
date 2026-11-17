# Good morning: Budget Pilot status

## 1. What's done

- **Env:** conda env `budget-pilot` created (Python 3.11, OpenJDK 17, Node 22, pyspark 4.2, mrjob 0.7.4, google-genai, scipy, pyarrow, plotly, faker). Nothing was installed system-wide, and the Project 3 folder was only read.
- **Data:** `data/generate.py` is vectorised and chunked to Parquet, with realistic per-platform CTR/CVR/CPC, audience skew, seasonality and diminishing returns. I generated **10K (+CSV) and 100K** rows.
- **KPI engine:** `engine/kpis.py` covers CTR, CPC, CPM, CPA, CVR, ROAS, profit and AOV, using safe division.
- **Optimizer:** `engine/optimizer.py` fits `a·log(1+s/b)` per platform with curve_fit, allocates by equal marginal ROAS within min/max caps, supports audience filters, and gives a 100× bootstrap band, uplift vs current and equal split, and a reason per platform. For Rs 1M it recommends Instagram 35%, Google 34%, TikTok 20.5%, Facebook 5.5% and YouTube 5%, with **+11.4% revenue vs the current mix** (90% band +9.4% to +14.6%).
- **Benchmark:** Pandas, MapReduce (mrjob local) and PySpark (local[*]) all ran at **10K and 100K, 3 runs each**, with real numbers in `bench/results.csv` and the README table. **All engines produced identical KPIs.** Spark works.
- **App:** FastAPI + Next.js with the same dark theme as Need Map Chat, and four pages: Chat (Gemini function calling with 4 tools and inline charts), Dashboard, Optimizer and Big Data Lab.
- **Gemini:** your `.env` key works. It was smoke-tested with about 6 calls, and the answers quoted only tool numbers.
- **Tests:** 25 pytest tests pass (KPI formulas, optimizer respects caps and sums to the budget, engines agree, API, mock chat). `eslint` and `next build` are clean. All pages returned HTTP 200 with no page errors, and the servers are stopped.
- **Docs:** `README.md`, `docs/DEMO_SCRIPT.md`, `docs/DECISIONS.md` (31 choices I made), `docs/REUSED.md` and screenshots in `docs/screens/`.

## 2. What needs you

1. **Run the full benchmark** (1M + 10M rows; generates the data first; probably 15–40 min):
   ```bash
   cd ~/projects/budget-pilot
   make bench                       # all sizes; or: make bench MAX_ROWS=1000000 to skip 10M
   ```
   This updates `bench/results.csv` and the README table automatically. If 10M is too heavy for your laptop, use `MAX_ROWS=1000000`. Big sizes are recorded as `timeout` after 600s per run, never invented; raise it with `conda run -n budget-pilot python bench/run_all.py --timeout 1200`.
2. **Look at the app:**
   ```bash
   make app                         # open http://localhost:3000  (Ctrl-C stops both servers)
   ```
3. **Record the demo** using `docs/DEMO_SCRIPT.md` (see section 5).
4. *(Optional)* After `make bench`, refresh the screenshots so the Lab page shows 1M/10M: `make shots` (uses system Chrome; makes 2–3 Gemini calls for the chat shot, or run `SHOT_CHAT=0 make shots`).
5. *(Optional)* Your `.env` was copied from Project 3 and still contains unused keys (`APIFY_TOKEN`, `DATASET`, …). They are harmless; I didn't edit it. `.env.example` lists what Budget Pilot uses.

## 3. Known issues and limits

- **Not run:** 1M/10M generation and benchmarks, as instructed. I measured the generator at 100K in 0.3s and streams chunks of 500K rows, so 10M should take under a minute and stay bounded in RAM. That is not tested yet.
- **Spark at small sizes** takes about 22s, of which about 12s is JVM start-up. That is real and explained on the Lab page, not a bug.
- The Optimizer and `optimize_budget` take about **3s** on first call (100 bootstrap refits). After that they are cached per argument set. Sliders are debounced.
- The donut's outside label for Instagram is clipped on narrower cards; the legend and tooltip show it.
- Gemini free-tier quotas: if chat says "quota exceeded", wait a minute or set `MOCK_CHAT=1` in `.env` and restart. The offline router calls the same tools.
- The data is synthetic (see README "Limitations"). Local Spark and mrjob are not a cluster.

## 4. Commands

```bash
cd ~/projects/budget-pilot
make app                 # run the app            → http://localhost:3000 (API on :8000)
make bench               # full benchmark 10K→10M → bench/results.csv + README table
make bench MAX_ROWS=1000000
make bench-small         # 10K + 100K only (~6 min)
make test                # pytest + lint
make data                # regenerate 10K/100K
make shots               # screenshots → docs/screens/
```

Without make: `conda run -n budget-pilot <command>`, e.g. `conda run -n budget-pilot python bench/run_all.py --max-rows 1000000`.

## 5. Recording checklist (details in `docs/DEMO_SCRIPT.md`)

- [ ] `make app`, then open http://localhost:3000 at 1440×900 with zoom at 100%.
- [ ] Warm up: open Optimizer once, ask one chat question, then click **New chat**.
- [ ] Follow the 3-minute table: 1M question → TikTok cap → Karachi 18-24 mobile → Google vs YouTube → Dashboard filter → Optimizer sliders → Big Data Lab.
- [ ] Leave about 15s between chat questions (Gemini rate limit).
- [ ] Fallback: `MOCK_CHAT=1` in `.env` if Gemini is throttled.
- [ ] Brag video: the 45-second shot list is at the bottom of `docs/DEMO_SCRIPT.md`.
