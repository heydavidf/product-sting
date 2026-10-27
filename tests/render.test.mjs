// Tests for skills/product-sting/engine/render.mjs that need no browser and no ffmpeg (run: node --test tests/*.test.mjs).
// Each test copies render.mjs into a throwaway folder next to a stand-in "playwright" package and puts a stand-in
// "ffmpeg" first on PATH. Both write what they were asked to do to a log, so the tests check the real script's
// flag parsing, frame times, page URL, browser options and temporary folder without rendering anything.
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const renderSource = path.join(here, "..", "skills", "product-sting", "engine", "render.mjs");

const FAKE_PLAYWRIGHT = `
import fs from "node:fs";
const log = (entry) => fs.appendFileSync(process.env.FAKE_LOG, JSON.stringify(entry) + "\\n");
export const chromium = {
  async launch(options) {
    log({ ev: "launch", options, TMPDIR: process.env.TMPDIR, TMP: process.env.TMP, TEMP: process.env.TEMP,
          PLAYWRIGHT_BROWSERS_PATH: process.env.PLAYWRIGHT_BROWSERS_PATH });
    if (process.env.FAKE_NO_BROWSER) throw new Error("browserType.launch: Executable does not exist\\nline 2\\nline 3\\nline 4 not shown");
    let url = "";
    const fakeWindow = { DUR: Number(process.env.FAKE_DUR || 6), seek: (t) => log({ ev: "seek", t }) };
    const page = {
      on() {},
      async goto(u) { url = u; log({ ev: "goto", url: u }); },
      async waitForFunction() {},
      async evaluate(fn, arg) {
        const saved = [globalThis.window, globalThis.location];
        globalThis.window = fakeWindow;
        globalThis.location = { search: new URL(url).search };
        try { return fn(arg); } finally { [globalThis.window, globalThis.location] = saved; }
      },
      async screenshot() { return Buffer.from("FAKEPNG!"); },
    };
    return {
      async newPage(options) { log({ ev: "newPage", options }); return page; },
      async close() { log({ ev: "close" }); },
    };
  },
};
`;

// Stand-in ffmpeg: records its arguments, the frames waiting in an image sequence and the bytes piped in,
// then writes the output file (the last argument).
const FAKE_FFMPEG = `#!/usr/bin/env node
const fs = require("node:fs");
const path = require("node:path");
const args = process.argv.slice(2);
const input = args[args.indexOf("-i") + 1];
const entry = { ev: "ffmpeg", args };
if (input && input.includes("%03d")) entry.frames = fs.readdirSync(path.dirname(input)).sort();
const finish = () => {
  fs.appendFileSync(process.env.FAKE_LOG, JSON.stringify(entry) + "\\n");
  fs.writeFileSync(args[args.length - 1], "fake output");
};
if (input === "-") {
  let bytes = 0;
  process.stdin.on("data", (d) => { bytes += d.length; });
  process.stdin.on("end", () => { entry.stdinBytes = bytes; finish(); });
} else finish();
`;

function setup({ pageDir = "piece" } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "render-test-"));
  const engine = path.join(root, "engine");
  fs.mkdirSync(path.join(engine, "node_modules", "playwright"), { recursive: true });
  fs.copyFileSync(renderSource, path.join(engine, "render.mjs"));
  fs.writeFileSync(path.join(engine, "node_modules", "playwright", "package.json"),
    JSON.stringify({ name: "playwright", type: "module", main: "index.js" }));
  fs.writeFileSync(path.join(engine, "node_modules", "playwright", "index.js"), FAKE_PLAYWRIGHT);
  const bin = path.join(root, "bin");
  fs.mkdirSync(bin);
  fs.writeFileSync(path.join(bin, "ffmpeg"), FAKE_FFMPEG, { mode: 0o755 });
  const piece = path.join(root, pageDir);
  fs.mkdirSync(piece, { recursive: true });
  fs.writeFileSync(path.join(piece, "index.html"), "<!doctype html><title>not loaded by the stand-in</title>");
  return { root, engine, bin, piece, log: path.join(root, "log.jsonl") };
}

function render(fx, args, env = {}) {
  // NO_COLOR, without FORCE_COLOR, keeps Node from colouring the numbers render.mjs prints (an agent's shell may set it).
  const childEnv = { ...process.env, PATH: fx.bin + path.delimiter + process.env.PATH, FAKE_LOG: fx.log, NO_COLOR: "1", ...env };
  for (const k of ["PLAYWRIGHT_BROWSERS_PATH", "CHROME_PATH", "FAKE_NO_BROWSER", "FAKE_DUR", "FORCE_COLOR"]) {
    if (!(k in env)) delete childEnv[k];
  }
  fs.rmSync(fx.log, { force: true });
  const r = spawnSync(process.execPath, [path.join(fx.engine, "render.mjs"), ...args], { cwd: fx.piece, env: childEnv, encoding: "utf8" });
  const events = fs.existsSync(fx.log) ? fs.readFileSync(fx.log, "utf8").trim().split("\n").map((l) => JSON.parse(l)) : [];
  return { ...r, events, seeks: events.filter((e) => e.ev === "seek").map((e) => e.t), ffmpeg: events.find((e) => e.ev === "ffmpeg") };
}

const near = (a, b) => Math.abs(a - b) < 1e-9;
const cleanup = (fx) => fs.rmSync(fx.root, { recursive: true, force: true });

test("--q keeps everything after the first = and reaches the page as its query", (t) => {
  const fx = setup(); t.after(() => cleanup(fx));
  const r = render(fx, ["--page=index.html", "--q=ar=square", "--stills=0", "--out=check/a.png"]);
  assert.equal(r.status, 0, r.stderr);
  const goto = r.events.find((e) => e.ev === "goto");
  assert.equal(goto.url, pathToFileURL(path.join(fx.piece, "index.html")).href + "?ar=square");
  assert.match(r.stdout, /^page query: \?ar=square$/m);
  const r2 = render(fx, ["--page=index.html", "--q=?ar=square&x=1=2", "--stills=0", "--out=check/b.png"]);
  assert.equal(r2.status, 0, r2.stderr);
  assert.ok(r2.events.find((e) => e.ev === "goto").url.endsWith("index.html?ar=square&x=1=2"));
});

test("a page path containing = and spaces is read whole and opened as a file URL", (t) => {
  const fx = setup({ pageDir: path.join("my pieces", "a=b") }); t.after(() => cleanup(fx));
  const r = render(fx, ["--page=../a=b/index.html", "--stills=1", "--out=check/s.png"]);
  assert.equal(r.status, 0, r.stderr);
  const goto = r.events.find((e) => e.ev === "goto");
  assert.equal(goto.url, pathToFileURL(path.join(fx.piece, "index.html")).href);
  assert.ok(goto.url.includes("my%20pieces/a=b/index.html"));
  assert.ok(fs.existsSync(path.join(fx.piece, "check", "s.png")), "the output path is relative to the page");
});

test("--stills seeks each time once and tiles a contact sheet; --thumb and --cols set its size", (t) => {
  const fx = setup(); t.after(() => cleanup(fx));
  const r = render(fx, ["--page=index.html", "--stills=0,1.5,4.3", "--out=check/beats.png"]);
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(r.seeks, [0, 1.5, 4.3]);
  assert.deepEqual(r.ffmpeg.frames, ["000.png", "001.png", "002.png"]);
  assert.equal(r.ffmpeg.args[r.ffmpeg.args.indexOf("-vf") + 1], "scale=640:-1,tile=3x1");
  assert.match(r.stdout, /wrote .*beats\.png \(3 frames: 0\.00, 1\.50, 4\.30\)/);
  const times = "0,0.9,1.5,2.5,3.6,4.3,5.2,5.9";
  const r2 = render(fx, ["--page=index.html", `--stills=${times}`, "--thumb=880", "--cols=2", "--out=check/seen.png"]);
  assert.equal(r2.ffmpeg.args[r2.ffmpeg.args.indexOf("-vf") + 1], "scale=880:-1,tile=2x4");
});

test("a square viewport sets the page size and uses the narrow sheet defaults", (t) => {
  const fx = setup(); t.after(() => cleanup(fx));
  const r = render(fx, ["--page=index.html", "--w=1080", "--h=1080", "--scale=2", "--stills=0,1,2,3,4,5,6,7", "--out=check/sq.png"]);
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(r.events.find((e) => e.ev === "newPage").options, { viewport: { width: 1080, height: 1080 }, deviceScaleFactor: 2 });
  assert.equal(r.ffmpeg.args[r.ffmpeg.args.indexOf("-vf") + 1], "scale=300:-1,tile=6x2");
});

test("--strip seeks every frame between two times at 30 fps", (t) => {
  const fx = setup(); t.after(() => cleanup(fx));
  const r = render(fx, ["--page=index.html", "--strip=0.9,1.4", "--out=check/strip.png"]);
  assert.equal(r.status, 0, r.stderr);
  const expected = [];
  for (let f = 27; f <= 42; f++) expected.push(f / 30);
  assert.equal(r.seeks.length, 16);
  r.seeks.forEach((s, i) => assert.ok(near(s, expected[i])));
});

test("a video covers the whole piece by default and keeps output dimensions even", (t) => {
  const fx = setup(); t.after(() => cleanup(fx));
  const r = render(fx, ["--page=index.html", "--out=out/draft.mp4"], { FAKE_DUR: "2" });
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.seeks.length, 60);
  r.seeks.forEach((s, i) => assert.ok(near(s, i / 30)));
  assert.equal(r.ffmpeg.stdinBytes, 60 * 8);
  const a = r.ffmpeg.args;
  assert.equal(a[a.indexOf("-framerate") + 1], "30");
  assert.equal(a[a.indexOf("-vf") + 1], "scale=trunc(iw/2)*2:trunc(ih/2)*2");
  assert.equal(a[a.indexOf("-r") + 1], "30");
  assert.match(r.stdout, /wrote .*draft\.mp4 60 frames x 1/);
});

test("--range renders only its frames, and --sub spreads subframes over the half frame before each", (t) => {
  const fx = setup(); t.after(() => cleanup(fx));
  const r = render(fx, ["--page=index.html", "--range=0.9,1.5", "--sub=4", "--out=check/blur.mp4"]);
  assert.equal(r.status, 0, r.stderr);
  const expected = [];
  for (let f = 27; f < 45; f++) for (const offset of [-0.375, -0.25, -0.125, 0]) expected.push((f + offset) / 30);
  assert.equal(r.seeks.length, 18 * 4);
  r.seeks.forEach((s, i) => assert.ok(near(s, expected[i]), `subframe ${i}: ${s} vs ${expected[i]}`));
  const a = r.ffmpeg.args;
  assert.equal(a[a.indexOf("-framerate") + 1], "120");
  assert.equal(a[a.indexOf("-vf") + 1], "tmix=frames=4:weights=1,select='not(mod(n\\,4))',setpts=N/30/TB,scale=trunc(iw/2)*2:trunc(ih/2)*2");
  assert.match(r.stdout, /18 frames x 4/);
});

test("temporary files go in .tmp/ beside the page, one folder per run, removed at the end", (t) => {
  const fx = setup(); t.after(() => cleanup(fx));
  const r = render(fx, ["--page=index.html", "--stills=0,1", "--out=check/t.png"]);
  assert.equal(r.status, 0, r.stderr);
  const launch = r.events.find((e) => e.ev === "launch");
  const tmpRoot = path.join(fx.piece, ".tmp");
  assert.equal(path.dirname(launch.TMPDIR), tmpRoot);
  assert.match(path.basename(launch.TMPDIR), /^run-/);
  assert.equal(launch.TMP, launch.TMPDIR);
  assert.equal(launch.TEMP, launch.TMPDIR);
  assert.equal(fs.existsSync(tmpRoot), false, ".tmp/ is removed when the run ends");
  fs.mkdirSync(path.join(tmpRoot, "run-other"), { recursive: true });
  const r2 = render(fx, ["--page=index.html", "--stills=0", "--out=check/t2.png"]);
  assert.equal(r2.status, 0, r2.stderr);
  assert.deepEqual(fs.readdirSync(tmpRoot), ["run-other"], "another render's folder is left alone");
});

test("the browser comes from the engine folder unless PLAYWRIGHT_BROWSERS_PATH or CHROME_PATH says otherwise", (t) => {
  const fx = setup(); t.after(() => cleanup(fx));
  const launch = (r) => r.events.find((e) => e.ev === "launch");
  const a = render(fx, ["--page=index.html", "--stills=0", "--out=check/a.png"]);
  assert.equal(launch(a).PLAYWRIGHT_BROWSERS_PATH, "0");
  assert.deepEqual(launch(a).options, {});
  const b = render(fx, ["--page=index.html", "--stills=0", "--out=check/b.png"], { PLAYWRIGHT_BROWSERS_PATH: "/opt/browsers" });
  assert.equal(launch(b).PLAYWRIGHT_BROWSERS_PATH, "/opt/browsers");
  const c = render(fx, ["--page=index.html", "--stills=0", "--out=check/c.png"], { CHROME_PATH: "/opt/chrome/chrome" });
  assert.deepEqual(launch(c).options, { executablePath: "/opt/chrome/chrome" });
});

test("a missing browser prints the install command, exits 1 and still removes its temporary folder", (t) => {
  const fx = setup(); t.after(() => cleanup(fx));
  const r = render(fx, ["--page=index.html", "--stills=0", "--out=check/x.png"], { FAKE_NO_BROWSER: "1" });
  assert.equal(r.status, 1);
  assert.match(r.stderr, /No browser\. From motion\/_engine run: PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install --only-shell chromium \(or set CHROME_PATH\)\./);
  assert.ok(r.stderr.includes("line 3") && !r.stderr.includes("line 4 not shown"), "only the first three lines of the error");
  assert.equal(fs.existsSync(path.join(fx.piece, ".tmp")), false);
});
