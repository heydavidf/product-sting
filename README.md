# Product Sting

An agent skill that turns a brand guide plus product screens into a short, on-brand motion piece: a **seamless product loop** (one shape morphing through your product's key states, never cut) or a **logo sting**. It is for people who have a product with an existing brand and want an 8 to 14 second loop for a landing page, README, feed post or deck, or a 2 to 5 second logo reveal.

It works spec-first: you approve a beat-by-beat state list before any animation is written. It then builds a single HTML page where every frame is a pure function of time, reviews and scores its own frames, fixes the worst ones, and renders an MP4 with motion blur, in as many aspect ratios as you need from one page.

Sound is optional and measured: recorded CC0 sound effects (two libraries are bundled), your own music track as a bed, loudness measured on the exported MP4, a seamless cut and an eased-out cut for single play, and a short list of timestamps for you to check on headphones, because the agent cannot hear. No API keys or paid services are needed. ElevenLabs is an optional extra for a generated brand sound family, with your own key and credits.

## Install

```sh
gh skill install heydavidf/product-sting product-sting --agent claude-code --scope user
```

This needs the GitHub CLI with its `gh skill` command (a preview feature; tested with gh 2.100.0). Use `--agent codex`, `--agent grok` or another supported agent instead of `claude-code`, or leave `--agent` out to be asked. `--scope user` makes the skill available in every project; leave it out to install into the current project only.

Without `gh skill`, copy the skill folder into your agent's skills folder by hand. For Claude Code:

```sh
git clone https://github.com/heydavidf/product-sting.git
mkdir -p ~/.claude/skills
cp -R product-sting/skills/product-sting ~/.claude/skills/
```

Everything the skill needs is inside `skills/product-sting/`. The rest of this repository (tests, checks, this README) is for contributors.

**Update** with `gh skill update product-sting`. **Uninstall** by deleting the installed `product-sting` folder. Each project you used it in keeps its own `motion/` folder (the engine with its browser, the sound tools with their Python environment, and your pieces); delete `motion/_engine/` and `motion/_sound/` to free their disk space.

### Ask your agent

Copy this into your agent to install the skill and prove it works, without starting a piece:

```text
Install the product-sting skill from https://github.com/heydavidf/product-sting by following its README. Then, in this project, run the skill's preflight (Step 0 in its SKILL.md) and show me the smoke-test contact sheet. Do not start a piece, and do not change anything outside this project's motion/ folder.
```

Installing and the first render need no account and no paid service. The preflight downloads Playwright's headless Chromium into the project (about 100 MB). The optional ElevenLabs step spends credits on your own plan and only runs if you ask for it.

## Prerequisites

- **Node 20 or later and ffmpeg** for the picture (`brew install ffmpeg` on macOS, `sudo apt install ffmpeg` on Debian or Ubuntu). On first run the skill copies its engine into `./motion/_engine/` in your project and installs Playwright and its headless Chromium there, inside the project rather than a shared cache (about 100 MB to download and 200 MB on disk, one time). On Linux the browser also needs some system libraries; `npx playwright install-deps chromium`, run in `motion/_engine`, installs them (with sudo). The renderer's temporary files stay in the project too and are removed after each render.
- **Python 3.12 or later, for the sound step only.** When you ask for sound, the skill copies its sound tools into `./motion/_sound/` and installs the pinned packages (librosa, numpy, soundfile, matplotlib) into a virtual environment there (about 450 MB, one time). Without Python you still get the silent piece.
- **Optional:** an ElevenLabs API key in the `ELEVENLABS_API_KEY` environment variable, only for a generated brand sound family. It spends credits on your plan.
- **A brand source**: a DESIGN.md, tokens file, style guide, product URL or screenshots. The skill will not invent a brand.

## When to use

| Use when | Not for |
|---|---|
| An 8-14s product loop for a landing page, feed post or pitch deck, showing a real flow (capture, process, confirm) as one continuous morph | Narrated explainers, captions on footage, or 30s+ launch videos: use a general video framework such as HyperFrames or Remotion |
| A 2-5s logo or name sting for a brand that already has a guide | A brand that doesn't exist yet: run a brand or design-system process first, because this skill refuses to invent one |
| App micro-interaction videos (a press, a state change, a confirmation) for app stores or social | Cartoon or character animation |

## What it does

1. **Preflight**: checks Node and ffmpeg, copies the engine into `./motion/_engine/`, installs it with its browser, and renders three stills of a starter page to prove the renderer works. Python is checked only if you want sound.
2. **Brief**: asks only what you have not already said: mode (loop or sting), formats (16:9, 1:1, 4:5, 9:16), brand source, real assets, the story, sound.
3. **Brand read**: tokens, fonts (as local files, with their licence), the reserved accent colour, and **motion bans** from the brand guide, translated from still-interface rules into motion rules for your approval. Handles a logo that is only a typeset word and images that exist only inside screenshots (never shown above their captured size).
4. **Spec (approval gate)**: the shape, the "reads" (what the viewer must understand, in order), a minimum text size for where the piece will be seen, the camera (moving, or fixed when an asset must not be enlarged), a state list on a beat grid, a spring preset chosen for the brand, and a camera table per format. Nothing is animated until you approve it.
5. **Build**: one `seek(t)` HTML page from a working starter, using closed-form springs (including springs that follow a moving target), with the scene on a camera stage and HUD elements outside it.
6. **Review loop**: contact sheets of every beat, the same beats at the size they will be seen, frame strips of every fast moment, and a first-frame-equals-last-frame check by eye and by pixel difference. Each still and each strip is scored 1-10; the worst 3 are fixed each round until all score 8+ (capped at 4 rounds, with leftovers reported).
7. **Render**: a draft checked on frames pulled from the MP4, then a final with motion blur: 4 subframes, or 8 when a move is fast enough for 4 to show separate copies. The final is silent, ready for web heroes and READMEs.
8. **Sound (optional)**: three or four sound families from the bundled CC0 libraries, one reward sound as the loudest cue, your music track as a bed, each cue placed just before its visual, loudness measured on the exported MP4, per-cue waveform checks, a SOUND.md with the music's licence, and timestamps for you to check.
9. **Other formats**: the same page with its own camera table per aspect ratio, chosen by `?ar=` and rendered with `--q`. Never a crop.
10. **Handover**: MP4s, contact sheets, render commands, assets used, final scores, and the sound measurements.

## Example

A request in Claude Code (the brand guide and product are fictional):

```text
/product-sting loop for our report builder, brand guide in design/DESIGN.md, 16:9 for the landing page and 1:1 for social, with sound
```

After the brief and your approval of the state list, the run produces:

```
motion/
├── _engine/                 motion.js, render.mjs + Playwright
├── _sound/                  soundpass.py, CC0 sound libraries, .venv
└── report-builder-loop/
    ├── SPEC.md
    ├── index.html           one page, a camera table for 16:9 and one for 1:1
    ├── fonts/
    ├── music/               your track (its licence goes in SOUND.md)
    ├── cues.json
    ├── check/
    │   ├── beats.png        one still per state change
    │   ├── beats-seen.png   the same stills at the size they will be seen
    │   ├── beats-square.png
    │   ├── strip-open.png   every frame of the open morph
    │   ├── loop.png         first and last frame side by side
    │   ├── critique-1.md
    │   └── final.png
    ├── out/
    │   ├── report-builder-loop.mp4          silent, 16:9
    │   ├── report-builder-loop-square.mp4   silent, 1:1
    │   └── sound/
    │       ├── report-builder-loop-sound-v1.mp4        seamless loop
    │       ├── report-builder-loop-sound-v1-post.mp4   audio eased out for single play
    │       ├── SOUND.md                                measurements, cues, headphone checks
    │       └── overview.png, seam.png, checks/
    └── HANDOVER.md
```

The skill ships a starter page (a button that opens into a card marked "Example data", fills a progress bar and folds into a tick) and a CC0 cue list for it. Output from those, on a clean install (27 October 2026, Apple Silicon laptop; paths shortened):

```
$ node ../_engine/render.mjs --page=index.html --stills=0,0.9,1.5,2.5,3.6,4.3,5.2,5.9 --out=check/beats.png
wrote .../check/beats.png (8 frames: 0.00, 0.90, 1.50, 2.50, 3.60, 4.30, 5.20, 5.90)
$ node ../_engine/render.mjs --page=index.html --out=out/demo.mp4 --sub=4
wrote .../out/demo.mp4 180 frames x 4
$ node ../_engine/render.mjs --page=index.html --w=1080 --h=1080 --q=ar=square --out=out/demo-square.mp4 --sub=4
page query: ?ar=square
wrote .../out/demo-square.mp4 180 frames x 4
$ ../_sound/.venv/bin/python ../_sound/soundpass.py --video out/demo.mp4 --cues cues.json --out out/sound
- no music bed (effects only)
- pass 1: peak-normalised, gain +3.4 dB, limiter off -> -18.7 LUFS, true peak -2.3 dBTP
- pass 2: gain +6.1 dB, limiter ceiling 0.75 -> -19.7 LUFS, true peak -2.5 dBTP
- NOTE: 3.7 dB short of the -16 LUFS target with limiting capped at 5 dB; reported, not forced.
- single-play cut demo-sound-v1-post.mp4: audio eases out over the last 1.4s -> -19.7 LUFS, true peak -2.5 dBTP
- FINAL: -19.7 LUFS integrated, true peak -2.5 dBTP (demo-sound-v1.mp4, the seamless cut)
```

The 6-second 1920x1080 final with motion blur rendered in about 31 seconds. The sound pass took about 30 seconds the first time, while Python built its caches, and about 4 seconds after that. The starter cue list has no music bed, so it falls short of -16 LUFS and says so.

## What has been tested

- macOS on Apple Silicon, with Claude Code, Node 25, Python 3.14 and ffmpeg 9: installation with `gh skill install`, the preflight, the starter page's stills and MP4s, and the sound pass on the starter cue list. A fresh agent session also made a 12-second product loop for a brand it had not seen, from an installed copy.
- Ubuntu, in this repository's CI: the engine and sound tests, and a real render of the starter page with the preflight's install commands (plus `--with-deps`, which installs the browser's Linux system libraries).
- **Not tested:** Windows (the sound commands use `.venv/bin/python`, which is a macOS and Linux path), agents other than Claude Code, and the **ElevenLabs path**, which is documented but has not been exercised because no key was used in testing. Treat it as untested.

## Limitations

- The agent cannot hear. The sound pass measures loudness and shows waveforms; you judge the mix on headphones from the timestamps it gives you.
- Review scores are the agent's own judgement of its stills and strips, checked against the lessons in `reference/LESSONS.md`. You approve the spec and see the result; nothing else judges the picture.
- The engine's `package.json` asks for Playwright `^1.50.0`, so each project gets the newest 1.x release when you set it up. It is not pinned to a tested version.
- Fonts must be local files, and the skill needs a real brand source and real assets.

## What's inside

| Path | What |
|---|---|
| `skills/product-sting/SKILL.md` | The workflow |
| `skills/product-sting/engine/motion.js` | Springs (`spring`, `track`, `follow` for a moving target, presets), `life` windows, OKLab `mix` |
| `skills/product-sting/engine/render.mjs` | Contact sheets (`--stills`, sized with `--thumb` and `--cols`), frame strips (`--strip`), video with motion blur (`--sub`), part of a video (`--range`), and `--q` to pass a format query such as `ar=square` to the page. Uses the browser inside the engine folder and keeps its temporary files beside the page |
| `skills/product-sting/templates/` | Starter page (a wide and a square camera table), SPEC.md template, and a CC0 `cues.json` for the starter page |
| `skills/product-sting/sound/soundpass.py` | The measured sound pass: cue placement, music bed, loudness measured on the MP4, two cuts, proof plots, SOUND.md |
| `skills/product-sting/sound/eleven_family.py` | Optional ElevenLabs sound-family and music-bed generator (your key, your credits) |
| `skills/product-sting/sound/lib/` | Two CC0 sound libraries, Coldframe (37 sounds) and Barty-Bart (109), each with its licence file, manifest and upstream MIT licence |
| `skills/product-sting/sound/requirements.txt` | The sound step's Python packages, pinned |
| `skills/product-sting/reference/LESSONS.md` | 45 rules, each learned from a broken frame or mix in a real piece, or from a fresh agent's first run |
| `skills/product-sting/LICENSE`, `skills/product-sting/THIRD_PARTY_NOTICES.md` | Copies of the root files, so an installed copy carries its licence and the bundled sounds' notices |
| `tests/`, `.github/` | Tests and checks for contributors; not installed with the skill |

## Contributing and support

Questions and bug reports go in the repository's issues. To change the skill, read [AGENTS.md](AGENTS.md) (file map, the checks to run and the working rules, for people and their agents) and [CONTRIBUTING.md](CONTRIBUTING.md). Report security problems privately as described in [SECURITY.md](SECURITY.md). Changes are listed in [CHANGELOG.md](CHANGELOG.md).

## Credits

The bundled sounds come from the [Coldframe](https://github.com/Razee4315/coldframe) and [Barty-Bart motion-graphics](https://github.com/Barty-Bart/motion-graphics) libraries (Kenney and Freesound recordings, CC0). The measured sound pass follows the sound-pass method credited to Vox (@Voxyz_ai) in Barty-Bart's skill, with Coldframe's sound-design rules. The "one shape, never cut" format follows a public prompt by @twoclipping; the reads-and-contact-sheet review method follows John Heibel's [ClaudeAnimationBase](https://github.com/JohnHeibel/ClaudeAnimationBase) animation guide. Details and licences in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Licence

MIT for the skill's code and documents ([LICENSE](LICENSE)). The bundled sounds are CC0; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
