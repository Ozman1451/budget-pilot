# Brag Plan: Budget Pilot

## What is it (one sentence)
A chat-first ad-budget optimizer: a marketing manager asks "Where should the next Rs. 1,000,000 go?" and Budget Pilot fits a diminishing-returns curve per platform (Facebook, Instagram, Google, TikTok, YouTube) on 12 months of campaign data, then re-splits the budget so every platform's *next* rupee earns the same.

## Who it's for / what it does for them
Pakistani marketing teams spending in PKR across five platforms and seven cities. It replaces "repeat last month's split" with a split that predicts **+11.4% revenue from the same Rs 1M** (90% band +9.4% to +14.6%), and explains every move in plain words.

## What sets it apart
- It optimizes the **marginal** return (the next rupee), not average ROAS. That is the whole idea, so the video explains it visually.
- The LLM never does maths: chat routes to Python tools; every number on screen is tool output.
- Real Big Data angle: the same KPI job in Pandas, MapReduce and PySpark, measured up to 10,000,000 rows, with identical KPIs.

## Most impressive claim (all verified from the code, `work/export_data.py`)
"Today Google's next rupee returns 3.72× and YouTube's returns 1.36×. Move money until every platform's next rupee returns 2.42×: +11.4% revenue, same budget."

## The angle
**"Every rupee should go where the next one earns most."** The film follows one Rs 1,000,000 budget: it arrives, we see why spending flattens, we watch the money move until the platforms balance, then the real app does it in one chat message.

## Hook (first 2–3 s)
A huge mono **Rs 1,000,000** rolls up from zero. Five platform pills drop in under it on half-beats with poker-chip sounds, like chips being placed on a table. Then the line lands: *Where should it go?* ("go?" in the magenta→saffron gradient).

## Highlights
1. **Every platform flattens:** the five *real* fitted response curves (a·log(1+spend/b), parameters from `engine/optimizer.py`) draw themselves, with a dashed marker at Rs 300K: "The 300,000th rupee earns less than the first."
2. **How it decides (the optimizer explained):** bars show each platform's return on its next rupee at today's split (Google 3.72×, Instagram 2.93×, TikTok 2.50×, Facebook 1.80×, YouTube 1.36×). Caption: "Move money until they're equal". The bars slide to **2.42×** (YouTube stops at its 5% floor, 1.70×). The formula sits underneath in mono.
3. **The real app:** a recorded chat. The chip "Where should the next Rs. 1M go?" is clicked, the tool runs, and the donut and current-vs-recommended bars render.
4. **The answer:** "Same Rs 1,000,000. New split." Bars move from today's share to the recommended share (Instagram 21→35%, Google 14→34%, TikTok 18→20.5%, Facebook 31→5.5%, YouTube 16→5%), then **+11.4% revenue** lands with the 90% band and ROAS 2.85× → 3.18×.
5. **Depth montage** (real recordings, cropped): TikTok capped at 10% (costs only 0.7%); Karachi · 18–24 · mobile (TikTok jumps to 52%); the Dashboard heatmap (7 cities × 5 platforms).
6. **Scale:** "Benchmarked up to 10,000,000 rows". Bars for Pandas+Parquet 2.1s, Pandas 7.3s, Spark+Parquet 26.0s, Spark 43.7s, MapReduce 135.5s (`bench/results.csv`), then "Identical KPIs from all three engines".

## Outro / punchline
"Every rupee goes where the next one earns most." → Budget Pilot wordmark (the app's glowing dot) → "Rs 1M · 5 platforms · 7 cities · 10M rows" → "Built by Usman · Big Data Analytics course".

## User flow worth showing
Click a prompt chip → the tool trace runs → donut + bars + reasons table → Optimizer sliders and audience filters re-route live → Dashboard.

## Tone
- Preset: **polished**, the sibling of the Need Map film (same family look, its own track and rhythm).
- Creative direction: "a calm finance-desk explainer". Numbers are the heroes, motion is precise, nothing shouts.
- Pacing: long settled holds on anything with numbers; cuts on bar lines of the music.

## Format: landscape, 1920×1080, 30 fps
## Duration: 46.5 s (the user asked for a 40–45 s brag video in the Need Map style; the extra 1.5 s is the music fade on the wordmark)

## Visual identity (from `frontend/src/lib/theme.ts`, `globals.css`, `NavBar.tsx`)
- Background #0A0A0F · surface #12121A · border #23232F · text #EDEDF2 · muted #8A8A9A
- Accent gradient magenta #E94BA8 → saffron #F5A524 (one accent word per line)
- Platform colours exactly as in the app: Facebook #60A5FA · Instagram #E94BA8 · Google #F5A524 · TikTok #2DD4BF · YouTube #FF7A59
- Engine colours: Pandas #4CC9F0 · MapReduce #A78BFA · Spark #F5A524
- Fonts: Geist (display/body) and Geist Mono (all numbers), the app's own fonts
- Logo: the app's glowing gradient dot + "Budget Pilot"

## Data and honesty notes
- Every number in the video comes from the code: `work/export_data.py` runs `engine/optimizer.py` on `data/ads_100k.parquet` (the app's default dataset) and reads `bench/results.csv`, writing `composition/assets/data/bp.js`. Nothing is typed in by hand.
- The data is described as "12 months of campaign data". As requested, the video doesn't label it synthetic and doesn't present weaknesses.
- App footage was recorded with **`MOCK_CHAT=1`** (the offline router: the same Python tools, zero Gemini calls; the API log shows no Gemini requests). For the video only, the recorder hides the mock-mode prefix "Offline mode (MOCK_CHAT):", the chat footer's "offline router" label and the navbar's "synthetic" tag. The charts, numbers and reasons are untouched tool output.
- No personal data appears anywhere: the app shows only aggregates.

## Audio direction
- Music: `happy-beats-business-moves-vol-9` (Sascha Ende, ende.app, CC BY 4.0), 114 BPM. It's from the same series as Need Map's vol-12, but a brighter, steadier groove fits a finance tool.
- Beat grid measured from the audio (bundled cue preset, extended to 49 s with ffmpeg + numpy, about 10 ms error): **beat = 1.0706 + 0.52628·k s**. Bar lines at 2.12, 4.23, 6.33, 8.44, 10.54, 12.65, 14.75, 16.86, 18.96, 21.07, 23.17, 25.28, 27.38, 29.49, 31.59, 33.70, 35.80, 37.91, 40.01, 42.12, 44.22.
- Volume 0.34, fade-in 0.3 s, fade-out 2.4 s.
- Audio-reactive: the bass envelope (`assets/data/audio.js`) gently breathes the magenta/saffron background glow.
- SFX posture: sparse, warm, under the music (0.3–0.55):
  - poker-chip lays under the five platform pills: the budget is literally being placed
  - one soft impact when the curves settle
  - a warm `bong` when the bars balance at 2.42×
  - a UI click on the chat chip
  - a chip-stack when the money moves to the new split
  - a soft heavy impact on +11.4%
  - card slides on the three depth cards
  - one soft impact on the benchmark bars
  - a bell on the wordmark

## Storyboard (absolute seconds; every cut on a beat)

| # | Scene | Time | What happens | Audio |
|---|---|---|---|---|
| 1 | Hook | 0.00–5.28 | Mono label "next month's ad budget". **Rs 1,000,000** rolls up 0.15→1.07. Five platform pills on half-beats 1.59–2.65. "Where should it **go?**" blurs in word by word at 3.18 and holds 1.9 s. Everything blurs out by 5.2. | chip-lay ×5 |
| 2 | Every platform flattens | 5.28–10.54 | Title words blur in. The real curves draw on the beat (5.81→7.39) with coloured end labels. At 7.91 a dashed Rs 300K marker plus "The 300,000th rupee earns less than the first." Mono caption "Fitted on 365 days of spend → revenue, per platform". | soft impact at 7.39 |
| 3 | How it decides | 10.54–18.96 | "So Budget Pilot asks: where does the **next rupee** earn most?" Rows land at 12.65 with bars of today's next-rupee return (3.72×…1.36×). At 14.75 the caption becomes "Move money until they're equal" and the bars glide to 2.42× (YouTube to its 1.70× floor, tagged "5% floor") while the numbers count. At 16.86 a glowing 2.42× line appears with "2.42× everywhere". The formula fades in. | bong at 16.86 |
| 4 | The real app | 18.96–24.23 | Framed recording: empty chat → click "Where should the next Rs. 1M go?" → answer, donut and bars render. Chip: "The real app · ask in plain words". | click at 20.16 |
| 5 | The answer | 24.23–30.54 | "Same Rs 1,000,000. **New split.**" Five rows show today's share. At 25.80 the bars move to the recommended share. At 27.38, **+11.4% revenue** lands on the right with the 90% band and ROAS 2.85× → 3.18×. | chip-stack at 25.80, soft heavy at 27.38 |
| 6 | Depth | 30.54–36.86 | Three cropped real clips, 2.1 s each: "Cap TikTok at 10% · costs just 0.7%", "Karachi · 18–24 · mobile · TikTok jumps to 52%", "Dashboard · 12 months · 7 cities · 5 platforms". | card-slide ×3 |
| 7 | Scale | 36.86–41.07 | "Benchmarked up to **10,000,000** rows" (the counter rolls). Five engine bars grow on half-beats with their times. "Identical KPIs from Pandas, MapReduce and Spark ✓". | soft impact at 37.91 |
| 8 | Outro | 41.07–46.50 | "Every rupee goes where the **next one** earns most." Wordmark on the beat at 43.70, then the stats line and credit. Music fades. | bell at 43.67 |

**Poster (`brag.jpg`, baked into frame 0):** the settled answer frame (+11.4% with the new split), the most shareable single frame.
