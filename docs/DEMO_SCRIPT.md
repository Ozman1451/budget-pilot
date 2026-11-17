# Demo script: Budget Pilot

## Before you record

```bash
make app                       # wait for "Ready" from Next.js; open http://localhost:3000
```

- Browser at 1440×900, dark OS theme, zoom 100%, bookmarks bar hidden.
- Warm the cache: open **Optimizer** once and wait for the curves to load. The first optimizer call takes ~3s; later calls are cached.
- Ask one throwaway chat question so Gemini is warm, then click **New chat**.
- Gemini rate limit is set by `GEMINI_RPM` in `.env`. Leave about 15s between chat questions.

## 3-minute screen recording

| Time | What to click / type | What to say |
|---|---|---|
| 0:00–0:15 | Chat page, empty state visible | "Management asks one question: where should the next one million rupees of ad spend go across Facebook, Instagram, Google, TikTok and YouTube? Budget Pilot answers it in chat." |
| 0:15–0:45 | Click chip **"Where should the next Rs. 1M go?"**. Point at the tool trace, then the donut, the bar chart and the reasons table. | "Gemini doesn't compute anything. It calls my optimizer tool. Every number here comes from Python: I fit a diminishing-returns curve per platform and split the budget so every platform's next rupee earns the same. It moves money from Facebook and YouTube to Instagram and Google, about 11% more revenue than the current mix, and it gives a 90% bootstrap band instead of fake precision." |
| 0:45–1:05 | Click chip **"What if TikTok is capped at 10%?"** | "What-if scenarios: capping TikTok costs under one percent; the optimizer re-routes to Instagram and Google." |
| 1:05–1:25 | Type **"Best platform for Karachi 18-24 on mobile?"** | "Audience targeting: for young mobile users in Karachi, TikTok and Instagram convert far better, so the split changes completely." |
| 1:25–1:40 | Type **"Why is Google better than YouTube?"** | "Google's clicks are expensive but high-intent; YouTube is cheap reach that rarely converts. Its first-rupee ROAS is below everyone else's marginal ROAS." |
| 1:40–2:05 | **Dashboard** tab. Change *All cities* → **Karachi**, then clear. Hover the heatmap. | "The dashboard: 12 months, KPI cards, platform comparison, ROAS trend, city-by-platform heatmap and the funnel. Every filter recomputes from the raw rows." |
| 2:05–2:35 | **Optimizer** tab. Drag **TikTok max** to 10%, then **YouTube min** to 15%. Point at the donut animating and the ● markers moving on the curves. | "Here management can play: budget, min and max per platform. Each curve flattens; the dot is where we stop spending, at the point where the extra rupee stops paying." |
| 2:35–3:00 | **Big Data Lab** tab. Point at the log-scale chart and the "when to use which" card. | "Big Data part: the same aggregation in Pandas, MapReduce and Spark, all real measurements, and all three produce identical KPIs. At this size Pandas wins and Spark's JVM start-up dominates; at 10 million rows the picture changes. That's when to reach for Spark." |

Fallback if Gemini is rate-limited: set `MOCK_CHAT=1` in `.env`, restart `make app`. The offline router calls the same tools, so the charts are identical; only the prose is simpler.

## 45-second "brag video" shot list

| # | Duration | Shot | On-screen text / VO |
|---|---|---|---|
| 1 | 0–4s | Black → Budget Pilot logo dot glowing, title types in | "Where should the next Rs. 1,000,000 go?" |
| 2 | 4–10s | Chat: chip clicked, tool trace ticks green, donut spins in | "Ask in plain words." |
| 3 | 10–16s | Close-up of the reasons table + "+11% vs current mix · 90% band" | "Every number from Python, not the LLM." |
| 4 | 16–23s | Optimizer: drag the TikTok max slider; donut and curve dots animate | "Diminishing returns, fitted per platform." |
| 5 | 23–29s | Dashboard: scroll from KPI cards to the heatmap | "12 months · 5 platforms · 7 cities." |
| 6 | 29–37s | Big Data Lab: log-scale chart draws in; highlight "KPIs identical: yes" | "Pandas vs MapReduce vs Spark: real benchmarks." |
| 7 | 37–45s | Back to chat with the full answer; logo + "Budget Pilot · FastAPI · Gemini · PySpark · Next.js" | "Budget Pilot." |

Screenshots for thumbnails are in `docs/screens/` (`make shots` regenerates them).
