# Sound tools

The measured sound pass for product-sting pieces. Only needed when a piece gets sound (SKILL.md Step 7); the picture steps never touch this folder.

| Path | What |
|---|---|
| `soundpass.py` | The pass: a silent MP4 and a `cues.json` in; out come the MP4 with sound (seamless loop), a `-post` cut with the audio eased out over the last 1.4 s for single play, a waveform plot per cue, an overview, the loop seam, and `SOUND.md` with the measured loudness |
| `eleven_family.py` | Optional. Generates a brand sound family or music-bed candidates with ElevenLabs, using your own key and credits |
| `requirements.txt` | The Python packages both scripts import, pinned. Needs Python 3.12 or later |
| `lib/coldframe/` | 37 CC0 UI sounds in 17 roles (clicks, keys, toggles, drops, pops, confirm, error, open, close, whoosh, impacts), level-matched, with `library.json` (peak time per file) and `LICENSE.md` (source per file) |
| `lib/barty-bart/` | 109 CC0 sounds in 12 categories (whoosh, click, pop, riser, impact, tick, ding, transition, typing, ui-blip, glitch, ambience) plus a six-sound default kit, with `manifest.json` and `LICENSES.md` (author and source per file) |

## Set up (once per project)

The skill copies this folder to `motion/_sound/` in your project and makes a virtual environment there, never inside the skill:

```bash
python3 -m venv motion/_sound/.venv
motion/_sound/.venv/bin/pip install -r motion/_sound/requirements.txt
```

## Run

From the piece folder:

```bash
../_sound/.venv/bin/python ../_sound/soundpass.py --video out/my-loop.mp4 --cues cues.json --out out/sound
```

`cues.json` names three or four sound families and lists the cues against the piece's state list; `templates/cues.json` in the skill is a working example for the starter page, and the docstring at the top of `soundpass.py` lists every key. A family comes from a bundled library (`{"lib": "coldframe", "role": "click-firm"}`, `{"lib": "barty-bart", "category": "tick"}`), from a folder made by `eleven_family.py`, or from your own files (`{"files": ["sound/my-click.wav"]}`).

## Music

No music is stored here. The user supplies a track for the bed; put it in the piece's own `music/` folder, and give `music`, `music_source` and `music_license` in `cues.json` so `SOUND.md` records where it came from. The pass refuses a bed without a source and licence. Do not commit a track whose licence forbids redistribution.

## ElevenLabs (optional)

`eleven_family.py` reads the key from the `ELEVENLABS_API_KEY` environment variable only. Every call spends credits on your plan: the script prints a ceiling estimate (40 credits per second of sound effect, ElevenLabs' published rate in October 2026) before it starts, and a 20-second music candidate cost about 300 credits in October 2026. Its docstring has the details and the known quirks of the API.

## Licences

Every bundled sound is CC0 1.0 (public domain dedication). The per-file sources are in each library's licence file and manifest; each library folder also carries its upstream MIT licence (`UPSTREAM-LICENSE.txt`), which covers its manifest and licence file, and the summary is in `THIRD_PARTY_NOTICES.md` in the skill's folder. The upstream Barty-Bart manifest also listed some Mixkit sounds as runtime downloads: those entries were removed from the copy here, and the pass never downloads anything.
