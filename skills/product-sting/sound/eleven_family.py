# SPDX-License-Identifier: MIT
# Copyright (c) 2026 David Finnegan. Part of product-sting, https://github.com/heydavidf/product-sting
"""Optional: generate a brand sound family and music-bed candidates with the ElevenLabs API. The bundled CC0 libraries need none of this.

  ../_sound/.venv/bin/python ../_sound/eleven_family.py credits
  ../_sound/.venv/bin/python ../_sound/eleven_family.py sfx   --spec sound/family.json --out sound/family-<brand>
  ../_sound/.venv/bin/python ../_sound/eleven_family.py music --prompt-file sound/bed.txt --out music --prefix bed --n 3 --ms 20000

spec (family.json): {"room": ", close microphone, completely dry, no reverb, single event, clean start and end",
                     "roles": {role: [prompt, seconds, variants], ...}, "split": [roles whose takes should be cut into single events]}
Write the room once and vary only the object: that is what makes the family sound like one brand.

API key: read from the ELEVENLABS_API_KEY environment variable (export ELEVENLABS_API_KEY=... in your own shell). It is never
read from or written to a file in the skill or the piece.

Cost: every call spends credits on the user's own ElevenLabs plan. Get the user's OK on the estimate first.
  Sound effects: ElevenLabs' cost page (read 15 October 2026) gave 40 credits per second when a duration is set; this script
  prints that ceiling for the spec before it starts. Three families made in October 2026 measured between about 2 and 25 credits
  per requested second on the plan counter, which lags one call and counts anything else spending from the same plan.
  Music: about 300 credits per 20-second candidate (October 2026). Three candidates is a sensible first run.
  Check ElevenLabs' current prices before a large run; they change.

Licence: generated sounds and music are covered by the user's ElevenLabs plan terms (paid plans included a commercial licence in
October 2026). The family's LICENSE.md and manifest.json record the prompts and the date; the piece's SOUND.md records the bed.

Output (sfx): one WAV per take (roles in "split" cut into single events at silences), each trimmed and peak-normalised to -8 dBFS
(the Coldframe level) with its loudest moment measured as peakMs, plus raw/ (the takes before splitting), manifest.json and
LICENSE.md. soundpass.py reads the folder with {"lib": "<folder>", "role": "<role>"}. Output (music): the MP3 candidates and a JSON
report with measured tempo, steadiness and crest factor, so you can pick by numbers.

Known API behaviour (October 2026): "single event" prompts often come back as clusters (hence "split"); the music model ignored the
asked tempo in two of its first five takes (generate several and measure; asking for a shaker on every beat helped in the next six); pcm_48000 sound
effects arrive as interleaved 16-bit stereo, which decode() downmixes, and check_length() stops the run if a take is not the
length asked for, before more credits are spent.
"""

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request

import librosa
import numpy as np
import soundfile as sf

BASE = "https://api.elevenlabs.io/v1"
SR = 48000
# The sound-effects endpoint sends pcm_* as headerless 16-bit interleaved stereo.
PCM_CHANNELS = 2
CEILING_CREDITS_PER_S = 40  # ElevenLabs' published sound-effect rate when a duration is set (read 15 October 2026)


def _key():
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not k:
        raise SystemExit(
            "Set ELEVENLABS_API_KEY in your environment first (export ELEVENLABS_API_KEY=<your key>). "
            "The key is never read from a file in this folder."
        )
    return k


def post(path, body, fmt=None):
    url = f"{BASE}{path}" + (f"?output_format={fmt}" if fmt else "")
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"xi-api-key": _key(), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.read(), dict(r.headers), None
    except urllib.error.HTTPError as e:
        return None, {}, f"HTTP {e.code}: {e.read()[:300].decode(errors='replace')}"


def credits():
    req = urllib.request.Request(
        f"{BASE}/user/subscription", headers={"xi-api-key": _key()}
    )
    j = json.load(urllib.request.urlopen(req, timeout=30))
    return j["character_limit"] - j["character_count"]


def decode(raw, fmt, channels=PCM_CHANNELS):
    if fmt.startswith("pcm_"):
        a = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
        if channels > 1:
            a = a[: len(a) // channels * channels].reshape(-1, channels).mean(1)
        return a, int(fmt.split("_")[1])
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(raw)
        p = f.name
    try:
        a, sr = librosa.load(p, sr=None, mono=True)
    finally:
        os.remove(p)
    return a, sr


def check_length(a, sr, seconds, what):
    """Stop the run if a take is not the length asked for: a changed channel layout shows up here before credits are spent on the rest."""
    if seconds is None:
        return
    got = len(a) / sr
    if abs(got - seconds) > max(0.05, 0.15 * seconds):
        raise SystemExit(
            f"{what}: asked for {seconds:.2f} s, decoded {got:.2f} s. If it is about double or half, the PCM channel layout "
            f"changed: fix PCM_CHANNELS in eleven_family.py (compare one take in pcm_48000 and mp3) before generating more."
        )


def norm_trim(a, sr):
    if sr != SR:
        a = librosa.resample(a, orig_sr=sr, target_sr=SR)
    ms = lambda x: max(1, int(x * SR))
    win = ms(0.005)
    env = np.sqrt(np.convolve(a**2, np.ones(win) / win, "same"))
    mx = env.max() + 1e-9
    on = int(np.argmax(env > mx * 0.03))
    a = a[max(0, on - ms(0.005)) :]
    env = env[max(0, on - ms(0.005)) :]
    keep = np.where(env > mx * 0.005)[0]
    a = a[: min(len(a), keep[-1] + ms(0.03))].copy()
    f = ms(0.01)
    fi = 48
    a[-f:] *= np.linspace(1, 0, f)
    a[:fi] *= np.linspace(0, 1, fi)
    a = a / (np.abs(a).max() + 1e-9) * 10 ** (-8 / 20)
    sm = np.convolve(a**2, np.ones(int(0.01 * SR)) / int(0.01 * SR), "same")
    return a, int(np.argmax(sm) / SR * 1000)


def split_events(a, sr):
    ms = lambda x: max(1, int(x * sr))
    win = ms(0.005)
    env = np.sqrt(np.convolve(a**2, np.ones(win) / win, "same"))
    mx = env.max() + 1e-9
    idx = np.where(env > mx * 0.03)[0]
    segs = []
    s = p = idx[0]
    for i in idx[1:]:
        if i - p > ms(0.06):
            segs.append((s, p))
            s = i
        p = i
    segs.append((s, p))
    return [
        a[max(0, s - ms(0.005)) : min(len(a), e + ms(0.08))]
        for s, e in segs
        if env[s : e + 1].max() >= mx * 0.25 and (e - s) >= ms(0.02)
    ]


def gen_sfx(spec, out, influence=0.5):
    os.makedirs(os.path.join(out, "raw"), exist_ok=True)
    room = spec.get("room", "")
    split = set(spec.get("split", []))
    secs = sum(d * n for (_, d, n) in spec["roles"].values())
    print(
        f"requested {secs:.1f} s of sound effects in {sum(n for (_, _, n) in spec['roles'].values())} takes: "
        f"up to {secs * CEILING_CREDITS_PER_S:.0f} credits at the published {CEILING_CREDITS_PER_S} credits per second"
    )
    man = {
        "source": "ElevenLabs Sound Effects API (eleven_text_to_sound_v2), generated "
        + time.strftime("%Y-%m-%d")
        + " on the user's ElevenLabs plan; use is governed by that plan's terms.",
        "levels": "peak-normalised to -8 dBFS, trimmed; roles in 'split' were cut into single events at silences",
        "room": room,
        "split": sorted(split),
        "roles": {},
    }
    c0 = credits()
    print(f"credits before: {c0}")
    for role, (prompt, d, n) in spec["roles"].items():
        full = prompt + room
        man["roles"][role] = {"prompt": full, "variants": []}
        for k in range(n):
            raw = err = None
            for fmt in ("pcm_48000", "mp3_44100_192", "mp3_44100_128"):
                raw, _hdr, err = post(
                    "/sound-generation",
                    {
                        "text": full,
                        "duration_seconds": d,
                        "prompt_influence": influence,
                    },
                    fmt,
                )
                if raw:
                    break
            if not raw:
                print(f"  {role} #{k + 1}: FAILED {err}")
                continue
            a, sr = decode(raw, fmt)
            sf.write(os.path.join(out, "raw", f"{role}-{k + 1}.wav"), a, sr)
            check_length(a, sr, d, f"{role} #{k + 1} ({fmt})")
            parts = split_events(a, sr) if role in split else [a]
            for j, seg in enumerate(parts):
                seg, pk = norm_trim(seg, sr)
                f = f"{role}-{k + 1}" + (f"-e{j + 1}" if role in split else "") + ".wav"
                sf.write(os.path.join(out, f), seg, SR)
                man["roles"][role]["variants"].append(
                    {"file": f, "peakMs": pk, "ms": int(len(seg) / SR * 1000)}
                )
            print(
                f"  {role} #{k + 1}: {len(parts)} event(s), {[int(len(x) / sr * 1000) for x in parts]} ms raw"
            )
            time.sleep(0.3)
    c1 = credits()
    man["credits_used"] = c0 - c1
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(man, f, indent=1)
    with open(os.path.join(out, "LICENSE.md"), "w") as f:
        f.write(
            "# ElevenLabs generated sound effects\n\nGenerated "
            + time.strftime("%Y-%m-%d")
            + " with the ElevenLabs Sound Effects API on the user's own plan. Use is governed by that plan's terms (check that it includes a commercial licence before publishing). Prompts are in manifest.json.\n"
        )
    print(f"credits used: {c0 - c1} (the counter lags one call), left: {c1}")


def gen_music(prompt, out, prefix, n, ms):
    os.makedirs(out, exist_ok=True)
    c0 = credits()
    rep = {"prompt": prompt, "candidates": []}
    print(f"credits before: {c0}")
    for k in range(n):
        raw = err = None
        for model in ("music_v2_5", "music_v2", "music_v1"):
            raw, _hdr, err = post(
                "/music",
                {
                    "prompt": prompt,
                    "music_length_ms": ms,
                    "model_id": model,
                    "force_instrumental": True,
                },
            )
            if raw:
                break
        if not raw:
            print(f"  {prefix} {k + 1}: FAILED {err}")
            continue
        f = f"{prefix}-{k + 1}.mp3"
        with open(os.path.join(out, f), "wb") as fh:
            fh.write(raw)
        y, _sr = librosa.load(os.path.join(out, f), sr=SR, mono=True)
        tempo, bf = librosa.beat.beat_track(y=y, sr=SR, start_bpm=120)
        beats = librosa.frames_to_time(bf, sr=SR)
        per = float(np.median(np.diff(beats))) if len(beats) > 2 else 0
        rms = librosa.feature.rms(y=y)[0]
        crest = 20 * np.log10(np.abs(y).max() / (np.sqrt(np.mean(y**2)) + 1e-9))
        rep["candidates"].append(
            {
                "file": f,
                "model": model,
                "seconds": round(len(y) / SR, 2),
                "tempo": round(float(np.atleast_1d(tempo)[0]), 1),
                "beat_period": round(per, 4),
                "rms_cv": round(float(np.std(rms) / (np.mean(rms) + 1e-9)), 3),
                "crest_db": round(float(crest), 1),
            }
        )
        print(
            f"  {prefix}-{k + 1}: {model} {len(y) / SR:.1f}s tempo {float(np.atleast_1d(tempo)[0]):.1f} period {per:.3f}s rms-cv {rep['candidates'][-1]['rms_cv']} crest {crest:.1f} dB"
        )
    c1 = credits()
    rep["credits_used_counter"] = c0 - c1
    with open(os.path.join(out, f"{prefix}.json"), "w") as fh:
        json.dump(rep, fh, indent=1)
    print(f"credits counter: {c0} -> {c1} (lags one call)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Optional ElevenLabs family and bed generator (needs ELEVENLABS_API_KEY; spends credits)."
    )
    ap.add_argument("cmd", choices=["sfx", "music", "credits"])
    ap.add_argument("--spec")
    ap.add_argument("--out")
    ap.add_argument("--prompt-file")
    ap.add_argument("--prefix", default="bed")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--ms", type=int, default=20000)
    ap.add_argument("--influence", type=float, default=0.5)
    A = ap.parse_args()
    if A.cmd == "credits":
        print(credits())
        sys.exit(0)
    if not A.out:
        ap.error("--out is required for sfx and music")
    if A.cmd == "sfx":
        with open(A.spec) as fh:
            gen_sfx(json.load(fh), A.out, A.influence)
    else:
        with open(A.prompt_file) as fh:
            prompt = fh.read().strip()
        gen_music(prompt, A.out, A.prefix, A.n, A.ms)
