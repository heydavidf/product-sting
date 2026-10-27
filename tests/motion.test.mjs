// Tests for skills/product-sting/engine/motion.js (run: node --test tests/*.test.mjs).
// motion.js is a browser script that defines globals, so it is loaded into a vm context as the page would load it.
// The expected values come from a numerical simulation of the spring equation, not from the formulas under test:
//   x'' = w^2 (target - x) - 2 zeta w x',  w = 2 pi f,  starting at rest.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const source = fs.readFileSync(path.join(here, "..", "skills", "product-sting", "engine", "motion.js"), "utf8");
const context = vm.createContext({});
vm.runInContext(source, context, { filename: "motion.js" });
const { spring, SPRINGS, track, follow, life, show, mix, easeOut } = vm.runInContext(
  "({ spring, SPRINGS, track, follow, life, show, mix, easeOut })",
  context,
);

// Fourth-order Runge-Kutta over one stretch with a constant target. Lands exactly on `duration`.
function integrate(state, target, { f, zeta }, duration, step = 2e-4) {
  if (duration <= 0) return state;
  const w = 2 * Math.PI * f;
  const n = Math.max(1, Math.ceil(duration / step));
  const h = duration / n;
  let [x, v] = state;
  const acc = (x1, v1) => w * w * (target - x1) - 2 * zeta * w * v1;
  for (let i = 0; i < n; i++) {
    const k1x = v, k1v = acc(x, v);
    const k2x = v + (h / 2) * k1v, k2v = acc(x + (h / 2) * k1x, v + (h / 2) * k1v);
    const k3x = v + (h / 2) * k2v, k3v = acc(x + (h / 2) * k2x, v + (h / 2) * k2v);
    const k4x = v + h * k3v, k4v = acc(x + h * k3x, v + h * k3v);
    x += (h / 6) * (k1x + 2 * k2x + 2 * k3x + k4x);
    v += (h / 6) * (k1v + 2 * k2v + 2 * k3v + k4v);
  }
  return [x, v];
}

// A value at rest at v0 whose target changes at each key time: the physical meaning of track() with one spring.
function simulateTrack(t, v0, keys, cfg) {
  const changes = keys.filter(([at]) => at < t).sort((a, b) => a[0] - b[0]);
  let state = [v0, 0], target = v0, now = 0;
  for (const [at, next] of changes) {
    if (at > now) { state = integrate(state, target, cfg, at - now); now = at; }
    target = next;
  }
  return integrate(state, target, cfg, t - now)[0];
}

const TIMES = [0.01, 0.05, 0.1, 0.2, 0.35, 0.5, 0.8, 1.2, 2.0];

test("spring() matches the simulated step response for every preset", () => {
  for (const [name, cfg] of Object.entries(SPRINGS)) {
    for (const dt of TIMES) {
      const expected = simulateTrack(dt, 0, [[0, 1]], cfg);
      assert.ok(Math.abs(spring(dt, cfg) - expected) < 1e-7, `${name} at ${dt}s: ${spring(dt, cfg)} vs ${expected}`);
    }
  }
});

test("spring() is 0 before it starts, defaults to the def preset and settles at 1", () => {
  assert.equal(spring(0), 0);
  assert.equal(spring(-0.5, SPRINGS.punchy), 0);
  for (const dt of TIMES) assert.equal(spring(dt), spring(dt, SPRINGS.def));
  assert.ok(Math.abs(spring(5) - 1) < 1e-6);
  assert.ok(Math.abs(spring(10, SPRINGS.calm) - 1) < 1e-6);
});

test("an underdamped spring peaks at the textbook overshoot; zeta 1 never overshoots", () => {
  for (const cfg of [SPRINGS.punchy, SPRINGS.def, SPRINGS.snappy]) {
    const w = 2 * Math.PI * cfg.f, wd = w * Math.sqrt(1 - cfg.zeta ** 2);
    const peakTime = Math.PI / wd;
    const expectedPeak = 1 + Math.exp((-cfg.zeta * Math.PI) / Math.sqrt(1 - cfg.zeta ** 2));
    assert.ok(Math.abs(spring(peakTime, cfg) - expectedPeak) < 1e-9);
  }
  for (const cfg of [SPRINGS.swiss, SPRINGS.calm]) {
    for (let dt = 0; dt < 4; dt += 0.01) assert.ok(spring(dt, cfg) <= 1);
  }
});

test("zeta above 1 is treated as critically damped (current behaviour)", () => {
  for (const dt of TIMES) assert.equal(spring(dt, { f: 2, zeta: 1.4 }), spring(dt, { f: 2, zeta: 1 }));
});

test("track() matches a simulated spring whose target changes several times", () => {
  const keys = [[1.0, 880], [3.5, 180], [4.8, 260]];
  for (const cfg of [SPRINGS.def, SPRINGS.heavy, SPRINGS.punchy]) {
    for (const t of [0, 0.5, 1.0, 1.3, 2.0, 3.5, 3.7, 4.0, 4.8, 5.0, 5.9]) {
      const expected = simulateTrack(t, 260, keys, cfg);
      const got = track(t, 260, keys, cfg);
      assert.ok(Math.abs(got - expected) < 1e-5, `t=${t}: ${got} vs ${expected}`);
    }
  }
});

test("track() with a spring per key is the sum of one simulated step per change", () => {
  const keys = [[1.0, 880, SPRINGS.def], [3.5, 180, SPRINGS.def], [4.8, 260, SPRINGS.heavy]];
  for (const t of [0.5, 1.2, 3.6, 4.0, 5.0, 5.9]) {
    let expected = 260, prev = 260;
    for (const [at, target, cfg] of keys) {
      expected += (target - prev) * simulateTrack(t - at, 0, [[0, 1]], cfg);
      prev = target;
    }
    assert.ok(Math.abs(track(t, 260, keys) - expected) < 1e-5);
  }
});

test("track() never jumps at a key time", () => {
  const keys = [[1.0, 880], [3.5, 180], [4.8, 260]];
  for (const [at] of keys) {
    assert.ok(Math.abs(track(at + 1e-6, 260, keys) - track(at - 1e-6, 260, keys)) < 1e-3);
  }
});

test("follow() equals track() for fixed numbers and for each item of an array", () => {
  const keys = [[0.5, 40, SPRINGS.snappy], [2.0, -10]];
  for (const t of [0, 0.6, 1.0, 2.2, 3.0]) {
    assert.equal(follow(t, 0, keys), track(t, 0, keys));
  }
  const start = [100, 200, 0, 0], a = [400, 300, 80, 80], b = [900, 500, 120, 60];
  const arrayKeys = [[0.5, a], [2.0, b]];
  for (const t of [0.4, 0.7, 1.5, 2.3, 4.0]) {
    const got = follow(t, start, arrayKeys);
    for (let j = 0; j < 4; j++) {
      const expected = track(t, start[j], [[0.5, a[j]], [2.0, b[j]]]);
      assert.ok(Math.abs(got[j] - expected) < 1e-12);
    }
  }
});

test("follow() reads a moving target at time t and rides on it once the spring has settled", () => {
  const rising = (t) => 1000 - 120 * t;
  for (const t of [0.2, 0.6, 1.1]) {
    const expected = 0 + (rising(t) - 0) * simulateTrack(t - 0.1, 0, [[0, 1]], SPRINGS.def);
    assert.ok(Math.abs(follow(t, 0, [[0.1, rising]]) - expected) < 1e-5);
  }
  for (const t of [4, 5, 6]) assert.ok(Math.abs(follow(t, 0, [[0.1, rising]]) - rising(t)) < 1e-6);
});

test('follow() with "step" jumps at once, and a lag delays size behind position', () => {
  const jumped = (t) => follow(t, [0, 0, 10, 10], [[1.0, [500, 300, 40, 40], "step"]]);
  assert.deepEqual(jumped(0.999), [0, 0, 10, 10]);
  assert.deepEqual(jumped(1.0), [500, 300, 40, 40]);
  const plain = (t) => follow(t, [0, 0, 0, 0], [[0.5, [600, 200, 90, 90]]]);
  const lagged = (t) => follow(t, [0, 0, 0, 0], [[0.5, [600, 200, 90, 90], undefined, 0.12]]);
  for (const t of [0.55, 0.62, 0.8, 1.2]) {
    const p = plain(t), l = lagged(t), earlier = plain(t - 0.12);
    assert.equal(l[0], p[0]);
    assert.equal(l[1], p[1]);
    assert.ok(Math.abs(l[2] - earlier[2]) < 1e-12 && Math.abs(l[3] - earlier[3]) < 1e-12);
  }
});

test("life() fades in from a, holds, fades out from b and is 0 outside", () => {
  assert.equal(life(0.9, 1, 3), 0);
  assert.equal(life(3.2, 1, 3, 0.18, 0.12), 0);
  assert.equal(life(2, 1, 3), 1);
  assert.ok(Math.abs(life(1.09, 1, 3, 0.18, 0.12) - easeOut(0.5)) < 1e-12);
  assert.ok(Math.abs(life(3.06, 1, 3, 0.18, 0.12) - 0.5) < 1e-9);
});

test("show() hides an element at zero opacity, and mix() writes an OKLab color-mix", () => {
  const el = { style: {} };
  show(el, 0);
  assert.deepEqual(el.style, { opacity: 0, visibility: "hidden" });
  show(el, 0.4);
  assert.deepEqual(el.style, { opacity: 0.4, visibility: "visible" });
  assert.equal(mix("red", "blue", 0.25), "color-mix(in oklab, blue 25.0%, red)");
  assert.equal(mix("red", "blue", 1.7), "color-mix(in oklab, blue 100.0%, red)");
});
