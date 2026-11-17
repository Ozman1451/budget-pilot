# Reused from Project 3 (Need Map Chat)

Source: `/home/ozmen/Downloads/BDA/projects/project3` (read-only; nothing there was modified).
Only **plumbing** was reused. No Instagram/Apify scraping, comment data, embeddings, clustering, tagging or
cluster-naming code was copied.

| Budget Pilot file | Reused from Project 3 | What changed |
|---|---|---|
| `backend/app/llm.py` | `backend/app/llm.py` | Kept: shared google-genai client, tenacity retry on 429/5xx, daily-quota detection, sliding-window `RateGate`, `user/model/calls/responses_content` helpers, one-turn `chat()` with automatic function calling off (keeps Gemini thought signatures), offline mock router pattern. Dropped: comment generation, tagging, embeddings, cluster naming, post inference, disk cache. Added: `MissingKey` → banner. New keyword router for the 4 budget tools. |
| `backend/app/agent.py` | `backend/app/agent.py` | Same loop (MAX_STEPS, HISTORY, `compact()` of tool summaries, SSE events `tool_start/tool_result/text_delta/done/error`). New system prompt for budget questions. |
| `backend/app/main.py` | `backend/app/main.py` | Same FastAPI shape: `/api/health`, `/api/tool/{name}`, `/api/chat` SSE streaming, CORS. `/api/manifest` → `/api/meta`. |
| `backend/app/schemas.py` | `backend/app/schemas.py` | Same `ChartSpec` / `ToolResult` / `SSEEvent`; new chart types (bar, line, donut, heatmap, funnel, table, curves, text). |
| `backend/app/config.py` | `backend/app/config.py` | Same pydantic-settings `.env` pattern; new settings (`BP_DATASET`, `N_BOOT`, `MOCK_CHAT`). |
| `backend/app/tools.py` | `backend/app/tools.py` (pattern only) | Registry + `call_tool` arg validation + `ToolError` + `clean()` JSON sanitiser. All tools are new. |
| `frontend/` config | `package.json`, `package-lock.json`, `tsconfig.json`, `eslint.config.mjs`, `postcss.config.mjs`, `components.json`, `next.config.ts` | Same Next.js 15 / React 19 / Tailwind 4 / ECharts / framer-motion versions. |
| `frontend/src/app/globals.css`, `lib/theme.ts`, `lib/utils.ts` | same files | Same dark theme (#0A0A0F, magenta→saffron accent gradient, Geist fonts, ECharts tooltip/axis styles). Added fixed platform and engine colours. |
| `frontend/src/lib/api.ts` | same file | Same fetch + SSE parser; `getManifest` → `getMeta`. |
| `frontend/src/components/chat/*` | `Chat.tsx`, `MessageText.tsx`, `ToolTrace.tsx` | Same chat UI (gradient user bubble, animated tool trace, prompt chips, dots). Charts now render inline under each answer. New prompt chips, tool labels, API-key banner. |
| `frontend/src/components/Toast.tsx`, `Skeleton.tsx`, `charts/EChart.tsx` | same files | Unchanged. `KpiTiles`/`MetricsTable` were adapted into `KpiTiles`/`DataTable`. |
| `frontend/src/components/NavBar.tsx` | `TopBar.tsx` | Same header look (glowing dot, gradient title, segmented control). Now page tabs instead of brand filters. |
| `frontend/src/components/AppProvider.tsx` | `app/page.tsx` | The chat streaming state machine moved into a provider so the chat survives tab switches. |
| `frontend/scripts/shot.mjs` | `frontend/scripts/shot.mjs` | Same playwright-core + system Chrome approach; new pages. |
| `Makefile`, `README.md`, `.env.example`, `.gitignore` | same files (style) | Same target style and README structure; conda env `budget-pilot` via `conda run` instead of the `ccc` guard. |
| `tests/` | `backend/tests/conftest.py` (pattern) | Same offline approach: no network in tests, mock chat router. |

Not reused (on purpose): `pipeline/*` (Apify scraping, embeddings, clustering, tagging, naming), `artifacts/`, comment
data, `embeddings.py`, `store.py` clustering logic, sentence-transformers / torch / umap / scikit-learn deps.
