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
| 2:35–3:00 | **Big Data Lab** tab. Point at the log-scale chart and the "when to use which" card. | "Big Data part: the same aggregation in Pandas, MapReduce and Spark, all real measurements, and all three produce identical KPIs. Look at the curve shapes: from 10 thousand to 10 million rows Spark on Parquet only goes from 22 to 26 seconds, because most of its time is a fixed JVM start-up, while MapReduce grows twenty-fold. Parquet makes Pandas three times faster at 10 million. On one machine Pandas wins; once the data outgrows RAM or moves to a cluster, Spark's flat cost is why you reach for it." |

Fallback if Gemini is rate-limited: set `MOCK_CHAT=1` in `.env`, restart `make app`. The offline router calls the same tools, so the charts are identical; only the prose is simpler.

## Launch ("brag") video

The finished 48-second launch video lives in `brag-output/`:

- `brag.mp4`: 1920×1080, 30 fps, −16 LUFS, poster baked into frame 0
- `brag.jpg`: the poster (the +11.4% answer frame)
- `brag-plan.md`: angle, storyboard and audio cues
- `share-copy.txt`: a caption ready to post
- `composition/`: the HyperFrames source

App footage in it was recorded with `MOCK_CHAT=1` (no Gemini calls) by `brag-output/work/record.mjs`. To re-render after an edit:

```bash
cd brag-output/composition && npx --yes hyperframes@0.9.55 render -o ../work/render.mp4
```

To put it in the README as an inline player, drag `brag.mp4` into a GitHub issue comment, copy the `https://github.com/user-attachments/assets/…` link, and paste it over the placeholder line in the README's "Launch video" section.

Screenshots for thumbnails are in `docs/screens/` (`make shots` regenerates them); the README banner is `docs/media/banner.png` (`node brag-output/work/banner.mjs`).
