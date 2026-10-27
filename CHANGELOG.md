# Changelog

## 1.0.0 (2026-10-27)

First public release, installed with `gh skill install heydavidf/product-sting product-sting`.

- The `product-sting` skill: preflight with a smoke render, brief, brand read with motion bans translated into motion rules, a spec with reads, a minimum text size for where the piece is seen and a beat-grid state list (the approval gate), a `seek(t)` page build, a scored review loop over beat stills, seen-size sheets and frame strips (capped at 4 rounds), a pixel-difference loop check, a draft checked on frames from the MP4, a motion-blurred final, other aspect ratios from one page with a camera table each, and a handover.
- Engine: `motion.js` (closed-form springs and presets, `track()` for a target that changes several times, `follow()` for a target that moves, `life()` windows, OKLab `mix()`) and `render.mjs` (contact sheets, frame strips, video with a 180-degree shutter, `--range` for one part, `--q` for a format query, flags split on the first `=`, the browser and temporary files kept inside the project).
- Sound: the measured sound pass (`sound/soundpass.py`) with two bundled CC0 libraries, Coldframe (37 sounds) and Barty-Bart (109); the user's own music as a bar-aligned bed, never stored in the skill and refused without a source and licence; loudness measured on the exported MP4; a seamless cut and an eased-out `-post` cut; waveform proofs and a SOUND.md with timestamps to check on headphones. Optional ElevenLabs generator (`sound/eleven_family.py`) with the user's own key and credits, documented but not exercised in testing.
- `reference/LESSONS.md`: 45 rules from real pieces and from a fresh agent's first run.
- Repository: tests for the engine and the sound tools, checks that run on every push, pull request and week (lint, tests, a real render of the starter page, dependency audits, the Agent Skills format, shell blocks in the docs, a tripwire, secrets and links), and contributor rules in `AGENTS.md`.
