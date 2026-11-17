# Good morning: Budget Pilot status

## 1. What's done

- **Env:** conda env `budget-pilot` created (Python 3.11, OpenJDK 17, Node 22, pyspark 4.2, mrjob 0.7.4, google-genai, scipy, pyarrow, plotly, faker). Nothing was installed system-wide, and the Project 3 folder was only read.
- **Data:** `data/generate.py` is vectorised and chunked to Parquet, with realistic per-platform CTR/CVR/CPC, audience skew, seasonality and diminishing returns. I generated **10K (+CSV) and 100K** rows.
- **KPI engine:** `engine/kpis.py` covers CTR, CPC, CPM, CPA, CVR, ROAS, profit and AOV, using safe division.
- **Optimizer:** `engine/optimizer.py` fits `a·log(1+s/b)` per platform with curve_fit, allocates by equal marginal ROAS within min/max caps, supports audience filters, and gives a 100× bootstrap band, uplift vs current and equal split, and a reason per platform. For Rs 1M it recommends Instagram 35%, Google 34%, TikTok 20.5%, Facebook 5.5% and YouTube 5%, with **+11.4% revenue vs the current mix** (90% band +9.4% to +14.6%).
- **Benchmark:** Pandas, MapReduce (mrjob local) and PySpark (local[*]) ran at **10K, 100K, 1M and 10M rows, 3 runs each** (CSV + Parquet), with real numbers in `bench/results.csv` and the README table. **All engines produced identical KPIs at every size.** At 10M: Pandas+Parquet 2.1s, Spark+Parquet 26.0s, MapReduce 135.5s.
- **App:** FastAPI + Next.js with the same dark theme as Need Map Chat, and four pages: Chat (Gemini function calling with 4 tools and inline charts), Dashboard, Optimizer and Big Data Lab.
- **Gemini:** your `.env` key works. It was smoke-tested with about 6 calls, and the answers quoted only tool numbers.
- **Tests:** 25 pytest tests pass (KPI formulas, optimizer respects caps and sums to the budget, engines agree, API, mock chat). `eslint` and `next build` are clean. All pages returned HTTP 200 with no page errors, and the servers are stopped.
- **Docs:** `README.md`, `docs/DEMO_SCRIPT.md`, `docs/DECISIONS.md` (31 choices I made), `docs/REUSED.md` and screenshots in `docs/screens/`. · README banner `docs/media/banner.png` · launch video in `brag-output/` (48 s, footage recorded with MOCK_CHAT=1).

## 2. What needs you

1. ~~Full benchmark (1M + 10M)~~: **done.** All 20 runs passed and every engine agrees; the README table and the Lab page are updated.
2. **Review the launch video** in `brag-output/`: `brag.mp4` (48 s), `brag.jpg` (poster), `brag-plan.md`, `share-copy.txt`. When you're happy:
   - Drag `brag-output/brag.mp4` into a GitHub issue comment, copy the `https://github.com/user-attachments/assets/…` link, and paste it over the placeholder line under "▶️ Launch video" in `README.md`. Delete the "coming soon" line.
   - Push it:
     ```bash
     cd ~/projects/budget-pilot
     git add brag-output README.md && git commit -m "Add launch video" && git push
     ```
     (`brag-output/work/`, the raw frames and caches, is git-ignored.)
3. **Look at the app:**
   ```bash
   make app                         # open http://localhost:3000  (Ctrl-C stops both servers)
   ```
4. *(Optional)* Make the repo public: `gh repo edit Ozman1451/budget-pilot --visibility public --accept-visibility-change-consequences`
5. *(Optional)* Your `.env` still has unused Project 3 keys (`APIFY_TOKEN`, `DATASET`, …). They're harmless; I didn't edit it.

## 3. Known issues and limits

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
