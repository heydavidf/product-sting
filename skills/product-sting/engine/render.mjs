// SPDX-License-Identifier: MIT
// Copyright (c) 2026 David Finnegan. Part of product-sting, https://github.com/heydavidf/product-sting
// product-sting renderer: a seek(t) page -> Playwright screenshots -> ffmpeg.
// The page must define window.seek(t), window.DUR (seconds) and set window.__ready = true once fonts and images are loaded.
//
//   Beat stills (contact sheet):  node render.mjs --page=../my-loop/index.html --stills=0,1.5,3 --out=check/beats.png
//   Seen size: --thumb is each image's width in the sheet, --cols the columns. A README sheet: --thumb=880 --cols=2.
//   Full-size still (one time, at the frame's own width):  node render.mjs --page=... --stills=1.5 --thumb=1920 --out=check/full-1.5.png
//   Strip (every frame between two times, for fast moments):  node render.mjs --page=... --strip=4.2,4.6 --out=check/strip.png
//   Draft video:   node render.mjs --page=... --out=out/draft.mp4
//   Final video:   node render.mjs --page=... --out=out/final.mp4 --sub=4     (4 subframes blended = motion blur; 8 for fast moves)
//   Part of a video, to check one move:  --range=1.0,1.6 (seconds; default the whole piece)
//
// Size: --w/--h are the CSS viewport, --scale the device pixel ratio. A 9:16 phone frame = --w=375 --h=667 --scale=2.88.
// Formats: --q is appended to the page URL as a query string, so one page can hold a camera table per aspect ratio:
//   node render.mjs --page=... --w=1080 --h=1080 --q=ar=square --stills=0,1.5,3 --out=check/beats-square.png
// Flags are --key=value and are split on the first "=" only, so a value may itself contain "=" (as --q=ar=square does).
// Output dimensions are forced even (odd heights can hang the H.264 encoder).
// Browser: Playwright's headless Chromium installed inside the engine folder
//   (PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install --only-shell chromium).
// This script sets PLAYWRIGHT_BROWSERS_PATH=0 itself when it is unset, so render commands need nothing extra.
// Or set CHROME_PATH to any Chrome binary.
// Temporary files (sheet frames, the browser's profile) go in a .tmp/ folder next to the page, removed when the run ends,
// so nothing is written to the system temp folder.
import { spawn, execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const arg = (k, d) => {
  const a = process.argv.find((x) => x.startsWith(`--${k}=`));
  const v = a ? a.slice(k.length + 3) : "";  // everything after the first "="
  return v === "" ? d : v;
};
const pagePath = path.resolve(arg("page", "index.html")), base = path.dirname(pagePath);
const out = path.resolve(base, arg("out", "out/video.mp4")), fps = +arg("fps", 30), sub = +arg("sub", 1);
const W = +arg("w", 1920), H = +arg("h", 1080), S = +arg("scale", 1), query = arg("q", "").replace(/^\?/, "");
fs.mkdirSync(path.dirname(out), { recursive: true });

// One temp folder per run inside <page folder>/.tmp/, so parallel renders never share one. Removed on exit.
const tmpRoot = path.join(base, ".tmp");
fs.mkdirSync(tmpRoot, { recursive: true });
const tmp = fs.mkdtempSync(path.join(tmpRoot, "run-"));
process.on("exit", () => {
  fs.rmSync(tmp, { recursive: true, force: true });
  try { fs.rmdirSync(tmpRoot); } catch { /* another render is still using .tmp/ */ }
});
for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => process.exit(130));
for (const k of ["TMPDIR", "TMP", "TEMP"]) process.env[k] = tmp;   // Playwright and Chromium put their profile here
process.env.PLAYWRIGHT_BROWSERS_PATH ??= "0";                       // must be set before Playwright loads
const { chromium } = await import("playwright");

const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}).catch((e) => {
  console.error(e.message.split("\n").slice(0, 3).join("\n"));
  console.error("No browser. From motion/_engine run: PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install --only-shell chromium (or set CHROME_PATH).");
  process.exit(1);
});
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: S });
page.on("pageerror", (e) => console.error("PAGE ERROR:", e.message));
await page.goto(pathToFileURL(pagePath).href + (query ? "?" + query : ""));
await page.waitForFunction(() => window.__ready === true, null, { timeout: 30000 });
if (query) console.log("page query:", await page.evaluate(() => location.search));
const shot = async (t) => { await page.evaluate((t) => window.seek(t), t); return page.screenshot({ type: "png" }); };

let times = null;
if (arg("stills")) times = arg("stills").split(",").map(Number);
if (arg("strip")) {
  const [a, b] = arg("strip").split(",").map(Number);
  times = []; for (let f = Math.round(a * fps); f <= Math.round(b * fps); f++) times.push(f / fps);
}

if (times) {
  const dir = path.join(tmp, "frames");
  fs.mkdirSync(dir);
  for (const [i, t] of times.entries()) fs.writeFileSync(`${dir}/${String(i).padStart(3, "0")}.png`, await shot(t));
  const cols = +arg("cols", Math.min(times.length, W > H ? 4 : 6)), tw = +arg("thumb", W > H ? 640 : 300);
  execFileSync("ffmpeg", ["-v", "error", "-y", "-framerate", "1", "-i", `${dir}/%03d.png`, "-vf", `scale=${tw}:-1,tile=${cols}x${Math.ceil(times.length / cols)}`, "-frames:v", "1", out]);
  console.log("wrote", out, `(${times.length} frames: ${times.map((t) => t.toFixed(2)).join(", ")})`);
} else {
  const dur = await page.evaluate(() => window.DUR);
  const [from, to] = arg("range") ? arg("range").split(",").map(Number) : [0, dur];
  const f0 = Math.round(from * fps), f1 = Math.round(to * fps);
  const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(fps * sub), "-i", "-",
    "-vf", [sub > 1 ? `tmix=frames=${sub}:weights=1,select='not(mod(n\\,${sub}))',setpts=N/${fps}/TB` : null, "scale=trunc(iw/2)*2:trunc(ih/2)*2"].filter(Boolean).join(","),
    "-r", String(fps), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", out], { stdio: ["pipe", "inherit", "inherit"] });
  let dead = false; ff.on("close", (c) => { if (c) { dead = true; console.error("ffmpeg exited with", c); process.exit(1); } });
  for (let f = f0; f < f1 && !dead; f++) for (let s = 0; s < sub; s++) {
    // Subframes span half a frame (a 180-degree shutter). A full-frame shutter smears text.
    const buf = await shot((f + (0.5 * (s - (sub - 1))) / sub) / fps);
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
  }
  ff.stdin.end(); await new Promise((r) => ff.on("close", r));
  console.log("wrote", out, f1 - f0, "frames x", sub);
}
await browser.close();
