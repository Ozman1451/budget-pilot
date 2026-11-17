// npm run shot — headless screenshots of every page → ../docs/screens/*.png (pattern reused from Need Map Chat).
// Starts the backend (uvicorn) and `next start` if they are not already up, uses system Chrome
// (CHROME_PATH or channel "chrome") so no browser download / sudo is needed, then stops what it started.
// SHOT_CHAT=0 skips the chat screenshot (which makes 2–3 Gemini calls unless MOCK_CHAT=1).
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const FRONT = join(dirname(fileURLToPath(import.meta.url)), "..");
const ROOT = join(FRONT, "..");
const API = "http://127.0.0.1:8000";
const WEB = "http://localhost:3000"; // must match the backend CORS origin
const OUT = join(ROOT, "docs", "screens");
const procs = [];
let browser;

const up = (url) => fetch(url).then((r) => r.ok, () => false);

async function waitFor(url, ms = 120_000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    if (await up(url)) return;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`timeout waiting for ${url}`);
}

function start(cmd, args, cwd, env = {}) {
  const p = spawn(cmd, args, { cwd, env: { ...process.env, ...env }, stdio: "ignore", detached: true });
  procs.push(p);
}

function cleanup() {
  for (const p of procs) {
    try {
      process.kill(-p.pid, "SIGTERM");
    } catch {}
  }
}

async function settle(page, selector, ms = 1800) {
  await page.waitForSelector(selector, { timeout: 90_000 });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(ms);
}

async function main() {
  if (!(await up(`${API}/api/health`))) start("uvicorn", ["app.main:app", "--port", "8000", "--app-dir", "backend"], ROOT);
  if (!(await up(WEB))) start("npx", ["next", "start", "--port", "3000"], FRONT);
  await waitFor(`${API}/api/health`);
  await waitFor(WEB);
  console.log("servers up");
  mkdirSync(OUT, { recursive: true });

  browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : { channel: "chrome" });
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));

  // the app scrolls inside <main>, so use tall viewports instead of fullPage
  const tall = (h) => page.setViewportSize({ width: 1440, height: h });
  await tall(1900);
  await page.goto(`${WEB}/dashboard`);
  await settle(page, '[data-testid="chart-heatmap"]');
  await page.screenshot({ path: join(OUT, "dashboard.png"), });
  console.log("dashboard.png");

  await tall(2150);
  await page.goto(`${WEB}/optimizer`);
  await settle(page, '[data-testid="chart-curves"]', 2500);
  await page.screenshot({ path: join(OUT, "optimizer.png"), });
  console.log("optimizer.png");

  await tall(1750);
  await page.goto(`${WEB}/lab`);
  await settle(page, '[data-testid="chart-table"], [data-testid="chart-text"]');
  await page.screenshot({ path: join(OUT, "lab.png"), });
  console.log("lab.png");

  await tall(960);
  await page.goto(`${WEB}/`);
  await settle(page, '[data-testid="prompt-chip"]', 800);
  await page.screenshot({ path: join(OUT, "chat-empty.png") });
  console.log("chat-empty.png");

  if (process.env.SHOT_CHAT !== "0") {
    await page.click('[data-testid="prompt-chip"] >> nth=0');
    await page.waitForFunction(
      () => {
        const m = [...document.querySelectorAll('[data-testid="assistant-msg"]')].at(-1);
        return m && m.querySelector('[data-testid="answer-text"]') && !m.querySelector(".animate-spin");
      },
      null,
      { timeout: 180_000 },
    );
    await page.waitForTimeout(2500);
    await tall(2100);
    await page.waitForTimeout(800);
    await page.screenshot({ path: join(OUT, "chat.png"), });
    console.log("chat.png");
  }

  if (errors.length) console.log("page errors:\n" + errors.join("\n"));
  else console.log("no page errors");
}

main()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(async () => {
    await browser?.close();
    cleanup();
  });
