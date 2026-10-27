// product-sting motion helpers. Every value is a pure function of time: no timers, no counters, no Math.random().
// Load with <script src="../_engine/motion.js"></script>; everything below is a global.
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, k) => a + (b - a) * k;
const win = (t, a, b) => clamp((t - a) / (b - a));
const easeOut = (k) => 1 - Math.pow(1 - k, 3);
const easeInOut = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);

// Closed-form damped spring step response, 0 -> 1. zeta < 1 overshoots a little; zeta >= 1 never does.
function spring(dt, { f = 2.2, zeta = 0.86 } = {}) {
  if (dt <= 0) return 0;
  const w = 2 * Math.PI * f;
  if (zeta >= 1) return 1 - Math.exp(-w * dt) * (1 + w * dt); // critically damped
  const wd = w * Math.sqrt(1 - zeta * zeta);
  return 1 - Math.exp(-zeta * w * dt) * (Math.cos(wd * dt) + ((zeta * w) / wd) * Math.sin(wd * dt));
}
// Presets. snappy = UI controls, def = cards, heavy = type and logos, swiss = hard no-overshoot brands,
// punchy = energetic brands (visible overshoot), calm = slow and soothing. Tune f/zeta to the brand.
const SPRINGS = {
  snappy: { f: 3.2, zeta: 0.82 }, def: { f: 2.2, zeta: 0.86 }, heavy: { f: 1.6, zeta: 0.95 },
  swiss: { f: 3.0, zeta: 1 }, punchy: { f: 3.6, zeta: 0.62 }, calm: { f: 0.9, zeta: 1 },
};
// A value that changes target many times = start + one spring per change: [[time, target, cfg?], ...]
// Targets are fixed numbers. For a target that moves, use follow() below.
function track(t, v0, keys, cfg = SPRINGS.def) {
  let v = v0, prev = v0;
  for (const [at, target, c] of keys) { v += (target - prev) * spring(t - at, c || cfg); prev = target; }
  return v;
}
// track() for a target that moves while it is chased (a slot on a card that is still rising, a spot on an image that slides).
// v0 and each target may be a number, an array such as [x, y, w, h, r], or a function of t that returns one.
// Same sum as track(), with every target read at time t: still a pure function of t, and once a key's spring has settled
// the value rides on that target exactly. Keys: [time, target, cfg?, lag?].
//   cfg "step" jumps at once instead of springing: use it only while the element is invisible (size 0 or off-screen).
//   lag (seconds) delays items 2 and up of an array (size, radius), so a dot travels first and grows after.
function follow(t, v0, keys, cfg = SPRINGS.def) {
  const read = (x) => (typeof x === "function" ? x(t) : x);
  const start = read(v0), list = Array.isArray(start);
  let prev = list ? start : [start];
  const v = prev.slice();
  for (const [at, target, c, lag = 0] of keys) {
    const next = list ? read(target) : [read(target)];
    for (let j = 0; j < v.length; j++) {
      const dt = t - at - (j >= 2 ? lag : 0);
      v[j] += (next[j] - prev[j]) * (c === "step" ? +(dt >= 0) : spring(dt, c || cfg));
    }
    prev = next;
  }
  return list ? v : v[0];
}
// Opacity window: fade in from a, out from b, each with its own short fade.
const life = (t, a, b, fin = 0.18, fout = 0.12) =>
  t < a || t > b + fout ? 0 : Math.min(easeOut(win(t, a, a + fin)), 1 - win(t, b, b + fout));
const show = (el, o) => { el.style.opacity = o; el.style.visibility = o <= 0.001 ? "hidden" : "visible"; };
const mix = (a, b, k, space = "oklab") => `color-mix(in ${space}, ${b} ${(clamp(k) * 100).toFixed(1)}%, ${a})`;
