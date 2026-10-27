---
name: product-sting
description: "Turn a brand guide plus product screens into a short, on-brand motion piece: a seamless product loop (8-14s, one shape that morphs through the product's key states, never cut) or a logo sting (2-5s). Writes a beat-by-beat spec for approval, builds a single seek(t) HTML page with closed-form springs, reviews its own beat stills and fixes the worst frames, renders MP4 with motion blur in one or more aspect ratios, and can add a measured sound pass (bundled CC0 recorded effects, the user's own music bed, loudness measured on the MP4). Use when the user wants a product demo loop, UI morph animation, app micro-interaction video, logo sting, or social motion piece for a product with an existing brand. SKIP when - the user wants narration, captions on footage, a long (30s+) launch video or explainer, or a cartoon; use a general video framework for those."
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, WebFetch
---

# Product Sting

You are making a short motion piece for a product. You do not make video directly: you write a web page where every frame is a pure function of time (`window.seek(t)`), then a headless browser captures the frames and ffmpeg turns them into an MP4.

The prompt is about 10% of the result. The rest is the setup this skill enforces: a real brand reference, a beat-by-beat spec the user approves, springs tuned to the brand, and a loop where you look at your own frames and fix them before rendering.

**Two modes:**
- **Loop** (default): 8-14s, seamless. One shape, never cut: a single element morphs through the product's key states (for example a button becomes a card becomes a confirmation, then back). Last frame equals the first.
- **Sting**: 2-5s, a logo or name reveal that ends on a hold. Heavy springs, no overshoot on type.

**This skill's folder.** The engine, templates, sound tools and lessons live in this skill's own folder: the directory that holds this SKILL.md (Claude Code shows it as the skill's base directory). The commands below write it as `$SKILL_DIR`. Shell variables may not carry from one command to the next, so either put the absolute path in its place or set it at the start of the same command (`SKILL_DIR="/absolute/path/to/product-sting"; ...`).

Read `$SKILL_DIR/reference/LESSONS.md` before Step 2. It is the checklist for every review pass.

**Work at high effort for a new piece.** Fixes and re-renders are fine at normal effort.

## Output location

All work goes in the user's project, never inside this skill's folder:

```
./motion/
├── _engine/            shared renderer (copied once, Step 0)
├── _sound/             shared sound pass, CC0 libraries and its .venv (copied once, Step 7, only if sound is wanted)
└── <piece-slug>/
    ├── SPEC.md         the approved spec
    ├── index.html      the seek(t) page, with a camera table per format
    ├── fonts/          local woff2 files
    ├── assets/         logo SVG, screenshots
    ├── music/          the user's music track, if any (never stored in the skill)
    ├── cues.json       sound cue list (optional)
    ├── check/          contact sheets, strips, critique notes; check/ref/ holds working crops of the inputs
    ├── out/            rendered MP4s; out/sound/ holds the sound pass and its SOUND.md
    └── HANDOVER.md     what was made and how to re-render
```

If the user names another output folder, use it instead of `./motion/`.

## Step 0: Preflight (blocking)

Run these and stop with a clear message if any fail:

1. `node --version` must be 20 or later (the current Playwright needs it).
2. `ffmpeg -version` and `ffprobe -version` must work. If missing, tell the user how to install ffmpeg for their OS (macOS: `brew install ffmpeg`; Debian/Ubuntu: `sudo apt install ffmpeg`; Windows: `winget install ffmpeg`) and stop. Do not try to render without it.
3. Set up the engine once per project. If `./motion/_engine/render.mjs` does not exist, run (with `$SKILL_DIR` filled in):
   ```bash
   mkdir -p motion/_engine
   cp "$SKILL_DIR/engine/"* motion/_engine/
   (cd motion/_engine && npm install && PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install --only-shell chromium)
   ```
   `PLAYWRIGHT_BROWSERS_PATH=0` puts the browser inside the project, in `motion/_engine/node_modules/`, instead of a shared folder in the user's home. `--only-shell` fetches only the headless browser the renderer uses (about 100 MB to download, about 200 MB on disk, once), not the full Chromium as well. `render.mjs` looks there by itself, so render commands need nothing extra. If the install fails but a local Chrome exists, the renderer accepts `CHROME_PATH=/path/to/chrome`. Tell the user which one you used.
4. **Smoke-test the renderer** before writing any code. Render three stills of the starter page, look at the sheet with Read (a blue button, a white card, a tick), then delete `motion/_smoke/`:
   ```bash
   mkdir -p motion/_smoke
   cp "$SKILL_DIR/templates/index.html" motion/_smoke/
   (cd motion/_smoke && node ../_engine/render.mjs --page=index.html --stills=0,1.5,4.3 --out=smoke.png)
   ```
   The renderer keeps its temporary files (sheet frames, the browser's profile) in a `.tmp/` folder next to the page and removes it when it finishes, so nothing is written to the system temp folder.
5. **For the sound step only:** Python 3.12 or later (`python3 --version`). The picture never needs Python. If the user wants sound and Python is missing or older, say so plainly and offer the piece without sound (or with sound once they install Python); do not block the rest. Its packages are installed in Step 7, not here.

## Step 1: Brief

Ask only for what the user has not already given, and list back what they did give so they can correct it. Use AskUserQuestion, in one round. It takes at most four questions per call, so when more than four are open, send two calls back to back.

- **Mode:** loop or sting.
- **Format:** 16:9, 1:1, 4:5 or 9:16 (one or several), and where it will be seen (feed, landing hero, deck).
- **Brand source:** a DESIGN.md, CSS tokens file, style guide, product URL or screenshots. **Required.** If none exists, stop and ask for one: never invent a brand.
- **Real assets:** logo SVG (or the font it is set in, when the logo is only a typeset word), product screenshots, fonts.
- **The story:** which 3-5 product moments matter (for a loop), or the line or logo to land (for a sting).
- **Sound:** none (a silent MP4, right for web heroes and READMEs that play muted), or the measured sound pass: recorded CC0 effects from the bundled libraries, plus a music track the user supplies (wanted for anything over about 10s). A generated brand family via ElevenLabs is an extra option only if the user has their own API key and agrees to spend credits.

## Step 2: Read the brand

1. Read the brand source. Extract colour tokens, fonts, corner radii, and what the accent colour is reserved for.
2. **Look for motion bans** (banned motifs, "no bounce", "no ornamental motion", "no gradients"). Record them in the spec. Every later idea must respect them. Look for sound rules too (for example "no celebration": then the piece has no reward sound).
3. **Translate static rules into motion rules.** Most guides are written for a still interface, so decide what each rule means in motion and write that in the spec, where the user approves it. For example:
   - "No opacity tricks" or "colours stay fully opaque": colour enters and leaves by size or position (growing, sliding, folding, cropping), never by a fade. Text may still fade.
   - "No shadows": delete the starter page's `box-shadow`.
   - "No blur" or "no glass": interface effects such as backdrop blur. The renderer's motion blur stays unless the user says otherwise; say so in the spec.
   - A stated interaction timing (for example "state changes take 200ms") becomes the timing of text fades.
4. Fonts must be local files. If the brand uses a Google font, install it inside the project, copy the `.woff2` files for the weights you use and the package's `LICENSE` file into `<piece>/fonts/`, then delete `motion/_fonts-tmp/`. The files land in `motion/_fonts-tmp/node_modules/@fontsource/inter/files/` for this example (use `@fontsource-variable/<font>` for a variable font):
   ```bash
   npm install --prefix motion/_fonts-tmp @fontsource/inter
   ```
   If the font is commercial and unavailable, ask the user for the files or agree a fallback.
5. **A logo that is only a word.** If there is no logo file and the logo is the name set in the brand font, set it from the font with the guide's weight and letter-spacing, and confirm that with the user.
6. **Assets cut from screenshots.** When an image exists only inside a screenshot, crop it at the captured size and never show it larger, camera zoom included (Step 3). ffmpeg is enough to crop, and to sample one pixel's colour (the second line prints three hex bytes, such as `82 90 93`):
   ```bash
   ffmpeg -v error -i path/to/screen.png -vf crop=640:400:120:300 assets/artwork.png
   ffmpeg -v error -i path/to/screen.png -vf crop=1:1:240:150 -f rawvideo -pix_fmt rgb24 - | od -An -tx1
   ```
   Check the sampling once against a colour the guide or the screen states. Keep slices and working crops in `check/ref/`; only what the page uses goes in `assets/`.
7. **Inputs the guide mentions but the user did not supply** (a fonts folder, a tokens file, mock data, a running app): ask for them once, then proceed with what exists and note in the spec what was missing.
8. If a product URL is the only source, fetch it and pull tokens from what you can see, then confirm them with the user.

## Step 3: Spec (approval gate)

1. Copy `$SKILL_DIR/templates/SPEC.md` to `motion/<piece-slug>/SPEC.md` and fill every section.
2. Write the **reads**: in order, what the viewer must understand, each with time to be found and understood. Never overlap two important reads.
3. **Text size for where it plays.** Anything the viewer must read needs about 14 px as seen. In the frame's own pixels (measured on a full-size still), that means at least:

   | Where it plays | Frame width | Seen at about | Important text in the frame, at least |
   |---|---|---|---|
   | GitHub README | 1920 | 880 px | 30 px |
   | Landing page hero, desktop | 1920 | 1200 px | 22 px |
   | Phone feed, 1:1 or 4:5 | 1080 | 390 px | 40 px |
   | Phone full screen, 9:16 | 1080 | 390 px | 40 px (14 px on the 375 px page) |
   | Phone feed, 16:9 | 1920 | 390 px | 70 px, too large for most stories: make a 1:1 or 4:5 for feeds |

   Secondary text can be about three quarters of that. Anywhere else: 14 px × frame width ÷ seen width. The seen widths are starting assumptions; confirm them on the seen-size sheet. Write the destination and the minimum in the spec; Step 5 checks it on a sheet at the seen width.
4. **Camera.** A push-in toward the action is the usual fix for small text (the starter pushes in to 1.12). When an asset must not be shown above its captured size (a crop from a screenshot, a low-resolution image), use a **fixed camera** instead: zoom 1 and no moves (`moves: []`), with the layout sized for reading. Name the choice in the spec.
5. **When a true-to-product element cannot be legible at the seen size** (a printed card's small print, a dense table), do not enlarge it or fake its text. Let the viewer read its key content large first, then show the element as a whole object whose small print is texture. Say so in the spec.
6. Write the **state list** on a beat grid (120 BPM = 0.5s beats unless the user has a track). Each state change lands on a beat. For a loop, the last row is "identical to frame 0".
7. Choose the **spring preset** with a reason tied to the brand (see `SPRINGS` in `engine/motion.js`).
8. If there is more than one format, fill the **Formats** table: one camera table per aspect ratio (Step 8).
9. **Show the user the shape, reads and state list. Wait for their OK before writing any animation code.** Apply their changes to SPEC.md first.

## Step 4: Build the page

1. Copy `$SKILL_DIR/templates/index.html` to `motion/<piece-slug>/index.html` as the starting point. It is a working example of every pattern: one morphing shape, `track()` for multi-target springs, `life()` windows for content layers, OKLab colour blends, a cursor with anticipation, a closing loop, and a camera with one table per aspect ratio (`CAMERAS`, picked by `?ar=`). For a piece with many states, expect to replace most of it; keep the `#stage` and HUD split, `CAMERAS`, `seek`, `DUR` and the `__ready` block.
2. Replace its tokens, fonts, content and timeline with the spec. The scene lives in `#stage`, a 1920x1080 layout that only the camera moves; HUD elements (logo mark, captions, labels) go outside `#stage`. Viewport sizes: 1920x1080 for 16:9, 1080x1080 for 1:1, 1080x1350 for 4:5, 375x667 at scale 2.88 for 9:16.
3. **A target that moves while it is chased** (a slot on a card that is still rising, a spot on an image that is sliding) needs `follow()` from `motion.js` instead of `track()`. Its targets may be functions of `t`, a `"step"` key jumps at once (only while the element is invisible), and a lag on a key lets `[x, y, w, h]` travel first and grow after, so flying shapes do not pile up. The comment above `follow()` shows the key format.
4. Rules the page must follow:
   - `window.seek(t)` sets every style from `t`. No CSS transitions or animations, no timers, no state carried between frames, no unseeded randomness.
   - `window.DUR` is the length in seconds. `window.__ready = true` only after fonts and images have loaded: `document.fonts.load()` for each weight the piece uses (a weight first used mid-piece can otherwise arrive late), `decode()` for each image, then `document.fonts.ready`. The starter's `__ready` block does this; list the brand's weights in `FONT_FACES`.
   - Use real assets (inline the logo SVG). Mark example data on screen when the content is not real.
   - Page variables must not reuse helper names from `motion.js` (`clamp`, `lerp`, `win`, `easeOut`, `easeInOut`, `spring`, `SPRINGS`, `track`, `follow`, `life`, `show`, `mix`).

## Step 5: Review loop (beat stills and strips, then fix)

Run from `motion/<piece-slug>/`. The times below are the starter page's; use your state list's. For other formats add `--w`, `--h`, `--scale` and `--q` (Step 8).

Render one still per state change as a contact sheet, the same stills at the size they will be seen, a full-size still of each state with small text, and every frame of each fast moment (morphs, presses, reveals) as a strip. `--thumb` is each image's width in the sheet and `--cols` the number of columns: use the seen width from Step 3 for the seen-size sheet, the frame's own width (1920, or 1080 for the other formats) for a full-size still, and `--thumb=480 --cols=6` for a strip longer than about half a second.

```bash
node ../_engine/render.mjs --page=index.html --stills=0,0.9,1.5,2.5,3.6,4.3,5.2,5.9 --out=check/beats.png
node ../_engine/render.mjs --page=index.html --stills=0,0.9,1.5,2.5,3.6,4.3,5.2,5.9 --thumb=880 --cols=2 --out=check/beats-seen.png
node ../_engine/render.mjs --page=index.html --stills=2.5 --thumb=1920 --out=check/full-2.5.png
node ../_engine/render.mjs --page=index.html --strip=0.9,1.4 --out=check/strip-open.png
```

In loop mode, check that the last frame equals the first, by eye side by side and by pixel difference on the full-size pair. The pair is `0` and `DUR - 1/30` (5.967 for a 6s piece). The last command prints the difference in decibels: `average:inf` means identical. Above about 60 is a tiny difference, such as a few pixels one shade off from a spring still settling by a hair (the starter page scores 100), but a 2 or 3 pixel dot also scores there, so look at the side-by-side to be sure. Anything lower means something has not returned to its first state.

```bash
node ../_engine/render.mjs --page=index.html --stills=0,5.967 --out=check/loop.png
node ../_engine/render.mjs --page=index.html --stills=0 --thumb=1920 --out=check/seam-a.png
node ../_engine/render.mjs --page=index.html --stills=5.967 --thumb=1920 --out=check/seam-b.png
ffmpeg -hide_banner -i check/seam-a.png -i check/seam-b.png -lavfi psnr -f null - 2>&1 | grep PSNR
```

Then **look at every image** with Read and critique against the spec and `reference/LESSONS.md`:

1. Score each beat still 1-10 on: the read is clear, text is legible at the size it will be seen (judge that on the seen-size sheet and the full-size stills, not the 640 px sheet), brand fit (tokens, bans, reserved accent), and nothing clips or overlaps.
2. Score each strip too, on its worst frame. Pile-ups, crossings, text outliving its container and clipping mostly happen in motion, between the held states.
3. Write `check/critique-<round>.md` in this shape:
   ```markdown
   # Critique, round 1
   ## Beat stills
   | t (s) | State | Read | Legible as seen | Brand | Clip/overlap | Score | Note |
   ## Strip findings
   | From-to (s) | Strip | What goes wrong | Score | Note |
   ## The 3 worst problems (stills or strips) and the fix for each
   ```
4. Fix the 3 worst, re-render the affected stills and strips, and score again.
5. Stop when every still and every strip scores 8 or more, or after **4 rounds**. If you hit the cap, list the problems still open in the handover; do not claim the piece passed.

Render the hardest 2-4 seconds first if the piece is long; full renders are slow and stills are cheap.

## Step 6: Render

A quick draft first (replace `my-loop` with the piece's slug). Check it on frames pulled from the MP4, one a second: only these show the encode itself, its fonts, colours and timing.

```bash
node ../_engine/render.mjs --page=index.html --out=out/my-loop-draft.mp4
ffmpeg -v error -i out/my-loop-draft.mp4 -vf fps=1,scale=640:-1,tile=4x4 -frames:v 1 -y check/draft-frames.png
```

**Motion blur.** The final blends subframes over half a frame (`--sub`), 4 by default. On a fast move, 4 subframes leave 3 to 4 separate copies instead of a smear (paused, a caption looks doubled). Find the fastest move: a spring move of D px at frequency f peaks at about D × f ÷ 12 px per frame (a 900 px slide on the default spring, about 165; a fifth more for the `punchy` preset). If any move exceeds about 60 px per frame, use `--sub=8`, which doubles the render time. Check that move alone first: render just that part with `--range` and pull a frame from it at full size (here the frame at 1.2s, 0.3s into the part):

```bash
node ../_engine/render.mjs --page=index.html --range=0.9,1.5 --sub=8 --out=check/blur-test.mp4
ffmpeg -v error -ss 0.3 -i check/blur-test.mp4 -frames:v 1 -y check/blur-test.png
```

Look at the frame with Read: moving edges and text should be a smear, not stacked copies. The copies sit about speed ÷ (2 × sub) px apart, so even at 8 a move above about 120 px per frame still steps faintly (the starter's cursor, at about 180, does): slow that move, or accept it on a small element. Then render the final, with `--sub=8` if the check found a move over 60 px per frame:

```bash
node ../_engine/render.mjs --page=index.html --out=out/my-loop.mp4 --sub=4
```

Pull the fastest-move frame from the final MP4 the same way and look at it once more; page stills have no motion blur, so only the MP4 shows it. Render a final contact sheet (`check/final.png`) from stills across the piece and look at it. In loop mode, the exact check is the page-still pair in Step 5. If that pair passed, a lower figure on the MP4's own first and last frames is H.264 compression (47 and 61 dB on the two pieces measured so far), not a seam; do not use the MP4 figure on its own, because a small real seam scores in the same range. The final MP4 is silent; keep it, because web heroes and READMEs play muted.

## Step 7: Sound (optional): the measured pass

Never synthesise the soundtrack. The pass places real recorded sounds, measures the result on the exported MP4, and hands the user moments to check, because you cannot hear. Read the Sound rules in `reference/LESSONS.md` (22 to 32) first.

1. **Set up once per project** (Python 3.12+ from Step 0). If `./motion/_sound/soundpass.py` does not exist, run (with `$SKILL_DIR` filled in):
   ```bash
   mkdir -p motion/_sound
   cp -R "$SKILL_DIR/sound/"* motion/_sound/
   python3 -m venv motion/_sound/.venv
   motion/_sound/.venv/bin/pip install -r motion/_sound/requirements.txt
   ```
   This copies about 3.6 MB of CC0 sounds and installs librosa and its dependencies into `motion/_sound/.venv` (a few hundred MB, once, with a network download).
2. **Choose three or four families from one brand.** From the bundled libraries: Coldframe roles (`click-soft`, `click-firm`, `tick`, `key`, `key-enter`, `toggle-on`, `toggle-off`, `select`, `drop`, `pop`, `confirm`, `error`, `open`, `close`, `whoosh`, `impact-soft`, `impact`; see `lib/coldframe/library.json`) and Barty-Bart categories (`whoosh`, `click`, `pop`, `riser`, `impact`, `tick`, `ding`, `transition`, `typing`, `ui-blip`, `glitch`, `ambience`; see `lib/barty-bart/manifest.json`). Pick **one reward sound** (usually `confirm`) and make it the loudest cue, unless the brand rules out celebration.
3. **Music bed.** Never stored in the skill. Ask the user for a track and its licence, put it in `motion/<piece-slug>/music/`, and record `music`, `music_source` and `music_license` in `cues.json` (the pass refuses a bed without them). Any piece over about 10s wants one. If the user has none, ship the effects-only cut and say so in the handover.
4. **Write `motion/<piece-slug>/cues.json`** from the state list. Start from `$SKILL_DIR/templates/cues.json` (a working CC0 cue list for the starter page). Each cue has the visual time `t`; the pass leads it by 0.03s. Give whooshes `"peak_align": true` so their loudest moment lands on the fastest frame of the move, and sustained textures (rain, footsteps, ambience) `"until": <end time>` with `fin`/`fout` fades instead of rate variation. Write about five `checks`: timestamps and what the user should listen for.
5. **Run the pass** from the piece folder (replace `my-loop` with the slug):
   ```bash
   ../_sound/.venv/bin/python ../_sound/soundpass.py --video out/my-loop.mp4 --cues cues.json --out out/sound
   ```
   It writes `out/sound/<name>-sound-<tag>.mp4` (the seamless loop), `out/sound/<name>-sound-<tag>-post.mp4` (audio eased out over the last 1.4s, for single play on phones and social), `out/sound/SOUND.md`, `overview.png`, `seam.png` and `checks/cue-NN.png`.
6. **Read the measurements** it prints and SOUND.md: the target is about -16 LUFS integrated with the true peak at or below -2 dBTP. If it reports a shortfall (sparse effects over a soft bed), report it; do not force it with more limiting.
7. **Look** at `overview.png`, `seam.png` and the cue checks with Read: each cue's waveform should start at its red line. Then give the user the checks list from SOUND.md to play on headphones. Never say the mix sounds good: it is unheard by you.

**Optional: a generated brand family (ElevenLabs).** Only with the user's own key and their OK on the cost. The key comes from the `ELEVENLABS_API_KEY` environment variable, never a file. Sound effects can cost up to 40 credits per second requested (ElevenLabs' published rate in October 2026; the script prints this ceiling for the spec before it starts), and a 20-second music candidate cost about 300 credits. Write `sound/family.json` (one shared "room" phrase, then a prompt, length in seconds and number of takes per role, as in the docstring of `eleven_family.py`), then:

```bash
../_sound/.venv/bin/python ../_sound/eleven_family.py sfx --spec sound/family.json --out sound/family-brand
../_sound/.venv/bin/python ../_sound/eleven_family.py music --prompt-file sound/bed.txt --out music --prefix bed --n 3
```

Use the family in `cues.json` with `{"lib": "sound/family-brand", "role": "<role>"}`. Pick the bed from the measured tempo and steadiness in `music/bed.json`, and record "ElevenLabs Music, generated <date>" and the user's plan licence as its source and licence.

## Step 8: Other formats (if asked): one page, a camera table per aspect ratio

**Never crop** a rendered video into another aspect ratio. Use the `?ar=` method:

1. The page keeps one layout in `#stage` and a camera table per aspect ratio in `CAMERAS` (the starter has `wide` and `square`). Each table gives the viewport size, the opening framing `[x, y, zoom]` and the moves `[time, x, y, zoom]`. The page reads `?ar=` (default `wide`) and sets `data-ar` on the root, so CSS can resize the body and move HUD elements per format.
2. Design the new table for the new frame: on a square, fit the content's width on wide shots and push in less (the frame is already tight). **The opening framing must equal the closing one**, or the loop no longer closes.
3. Keep HUD elements outside `#stage`. Give the query its own variable names (the starter uses `QUERY` and `AR`); never one that a page helper already uses, such as `q` or `win`.
4. Render each format with its viewport size and `--q`, which the renderer appends to the page URL (it prints `page query: ?ar=square` to confirm). `--cols` sets the contact sheet's columns. Use the same `--sub` as the wide final:
   ```bash
   node ../_engine/render.mjs --page=index.html --w=1080 --h=1080 --q=ar=square --stills=0,0.9,1.5,2.5,3.6,4.3,5.2,5.9 --cols=4 --out=check/beats-square.png
   node ../_engine/render.mjs --page=index.html --w=1080 --h=1080 --q=ar=square --stills=0,5.967 --out=check/loop-square.png
   node ../_engine/render.mjs --page=index.html --w=1080 --h=1080 --q=ar=square --out=out/my-loop-square.mp4 --sub=4
   ```
5. Each format gets its own stills check and loop check (Step 5). The timing is shared, so the same `cues.json` works: run the sound pass again on the new MP4 with its own `--out` folder (for example `out/sound-square`).

## Step 9: Handover

Write `motion/<piece-slug>/HANDOVER.md` and summarise it to the user:

- The files made (MP4s per format, contact sheets) with paths.
- The exact render commands, including `--w/--h/--q` per format and the `--sub` used (when it is 8, the fastest move's speed in px per frame).
- Assets and fonts used, and where they came from.
- Final critique scores, and any problems still open if the review loop hit its cap.
- If sound: both cuts (seamless and `-post`), the measured LUFS and true peak, the music track's source and licence, any loudness shortfall, and the headphone checks. Say plainly that the mix has not been heard by you.

Show the user `check/final.png` and point them to the MP4.

## Rules

- Never invent brand colours, logos or product claims. Ask.
- Never skip the spec approval in Step 3.
- Never write inside this skill's own folder; it may be read-only. Engines, virtual environments, downloads, temporary files and outputs go in the user's project (the browser in `motion/_engine/`, font downloads in `motion/_fonts-tmp/`, the renderer's frames in `.tmp/` beside the page), never in the system temp folder or a shared cache.
- Never report the piece as finished without having looked at the rendered stills.
- Never store a music track in the skill, or commit one whose licence forbids redistribution.
- Never put an API key in a file; ElevenLabs reads `ELEVENLABS_API_KEY` from the environment.
