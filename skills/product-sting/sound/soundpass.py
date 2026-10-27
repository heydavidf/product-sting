# SPDX-License-Identifier: MIT
# Copyright (c) 2026 David Finnegan. Part of product-sting, https://github.com/heydavidf/product-sting
"""Measured sound pass for product-sting pieces: a silent MP4 and a cue list in, a measured MP4 with sound and its proof out.

It places real recorded sounds with variation (never the same take twice in a row, playback rate 0.96 to 1.04, gain +-1.5 dB),
leads each cue by 0.03 s, peak-aligns whooshes, tiles sustained textures with fades, builds a bar-aligned loop bed from the
user's own music (or searches a long track for the best start), ducks the bed under key moments, exports the MP4, measures it
with ffmpeg's ebur128 filter, adjusts within a limiting cap, and writes proof: a waveform plot per cue, an overview, the loop
seam, and SOUND.md (music source and licence, the measurements, the cues, and the moments for a person to check on headphones).
It also writes a second cut with the audio eased out over the last 1.4 s ("-post") for single play on phones and social.
The model running this cannot hear: nothing here is a quality claim, only measurements and a list of moments to check.

Command line (from the piece folder, with the virtual environment made from requirements.txt):

  ../_sound/.venv/bin/python ../_sound/soundpass.py --video out/<slug>.mp4 --cues cues.json --out out/sound

cues.json (paths in it are relative to the cues.json file; see templates/cues.json in the skill):
  {"name": "<slug>", "tag": "v1",
   "family": {"press": {"lib": "coldframe", "role": "click-firm"},          bundled Coldframe library, by role
              "tick":  {"lib": "barty-bart", "category": "tick"},           bundled Barty-Bart library, by category
              "tap":   {"lib": "sound/family-brand", "role": "tap", "maxms": 150},  a family made by eleven_family.py
              "own":   {"files": ["sound/my-click.wav"]}},                  your own files
   "cues": [{"t": 0.9, "fam": "press", "db": -2, "who": "you", "desc": "presses Start"}, ...],
   "music": "music/track.mp3" or null, "music_source": "...", "music_license": "...", "sfx_credit": "...",
   "checks": ["0.9s press: ...", ...],
   "options": {"target_lufs": -16, "max_tp": -2, "post_fade": 1.4, "bed_mode": "loop", "bpm": 120, "ducks": [[a, b, db, pre, post]], ...}}

Cue keys: t (visual time, s), fam (family name), db (gain), who ("you" | "product" | "world", for plot colours), desc;
  optional peak_align (start early so the loudest moment lands on t), rate (playback rate before variation), maxlen (s),
  until (end time: a sustained texture tiled from t to until with fades, no rate variation), fin, fout (fade seconds), exact (no lead).

Python use (a piece script):  import soundpass as sp; fam = sp.coldframe({"press": "click-firm"}); sp.run(video, cues, fam, out, ...)
"""

import argparse
import json
import os
import random
import re
import subprocess

import librosa
import matplotlib
import numpy as np
import soundfile as sf

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "lib")  # the bundled CC0 libraries, next to this file
LEVEL_DBFS = -8.0  # Coldframe files are level-matched to about this peak; other sources are trimmed to it
run_cmd = lambda c: subprocess.run(c, capture_output=True, text=True, check=False)


def load_family(lib, roles):
    """roles: {family: "role"} or {family: ("role", maxms)} against a folder whose manifest.json (eleven_family.py output) or
    library.json (Coldframe) lists {"roles": {role: {"variants": [{"file", "peakMs", "ms"}]}}}."""
    man_path = next(
        (
            os.path.join(lib, m)
            for m in ("manifest.json", "library.json")
            if os.path.exists(os.path.join(lib, m))
        ),
        None,
    )
    if not man_path:
        raise SystemExit(f"{lib}: no manifest.json or library.json")
    with open(man_path) as f:
        man = json.load(f)["roles"]
    fam = {}
    for name, spec in roles.items():
        role, maxms = (spec, None) if isinstance(spec, str) else spec
        if role not in man:
            raise SystemExit(
                f"family {name}: role {role} not in {man_path} (roles: {', '.join(sorted(man))})"
            )
        fam[name] = [
            {
                "path": os.path.join(lib, v["file"]),
                "peak": v["peakMs"] / 1000,
                "file": v["file"],
                "trim_db": 0.0,
            }
            for v in man[role]["variants"]
            if not maxms or v["ms"] <= maxms
        ]
        if not fam[name]:
            raise SystemExit(
                f"family {name}: no variants of role {role} under {maxms} ms"
            )
    return fam


def coldframe(roles):
    """Families from the bundled Coldframe library (CC0): roles such as click-soft, click-firm, tick, key, key-enter, toggle-on,
    toggle-off, select, drop, pop, confirm, error, open, close, whoosh, impact-soft, impact. See lib/coldframe/library.json."""
    return load_family(os.path.join(LIB, "coldframe"), roles)


def _peak(path):
    """(time of the loudest 10 ms in s, peak level in dBFS) of a file."""
    a = _load(path)
    win = int(0.01 * SR)
    sm = np.convolve(a**2, np.ones(win) / win, "same")
    return float(np.argmax(sm) / SR), float(20 * np.log10(np.abs(a).max() + 1e-9))


def add_file(fam, name, path, peak=None, trim_db=None):
    """Add one file to a family. Peak time and level trim are measured unless given (trimmed to LEVEL_DBFS peak)."""
    pk, lvl = _peak(path) if peak is None or trim_db is None else (peak, 0.0)
    fam.setdefault(name, []).append(
        {
            "path": path,
            "peak": pk if peak is None else peak,
            "file": os.path.basename(path),
            "trim_db": (LEVEL_DBFS - lvl) if trim_db is None else trim_db,
        }
    )


def bartybart(categories, maxms=None):
    """Families from the bundled Barty-Bart library (CC0): {family: category}, categories such as whoosh, click, pop, riser,
    impact, tick, ding, transition, typing, ui-blip, glitch, ambience. Its files peak near 0 dBFS, so each is trimmed to the
    Coldframe level. See lib/barty-bart/manifest.json (only bundled files are used; nothing is ever downloaded)."""
    bb = os.path.join(LIB, "barty-bart")
    with open(os.path.join(bb, "manifest.json")) as f:
        man = json.load(f)
    fam = {}
    entries = [
        e
        for e in man["default_kit"] + man["bundled"]
        if e.get("file") and e.get("bundled", True)
    ]  # kit first, then alternates
    for name, cat in categories.items():
        for e in entries:
            if e["category"] != cat:
                continue
            path = os.path.join(bb, e["file"])
            if (
                maxms
                and (
                    e["duration_s"]
                    if "duration_s" in e
                    else librosa.get_duration(path=path)
                )
                * 1000
                > maxms
            ):
                continue
            add_file(fam, name, path)
        if name not in fam:
            raise SystemExit(
                f"family {name}: no bundled Barty-Bart files in category {cat}"
            )
    return fam


def _load(p):
    a, _sr = librosa.load(p, sr=SR, mono=True)
    return a.astype(np.float32)


def _rate(a, rate):
    n = int(len(a) / rate)
    return np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(
        np.float32
    )


def _measure(p, mono=False):
    o = run_cmd(
        ["ffmpeg", "-nostats", "-i", p]
        + (["-ac", "1"] if mono else [])
        + ["-af", "ebur128=peak=true", "-f", "null", "-"]
    ).stderr
    return float(re.findall(r"I:\s+([-\d.]+) LUFS", o)[-1]), float(
        re.findall(r"Peak:\s+([-\d.]+) dBFS", o)[-1]
    )


def run(
    video,
    cues,
    family,
    out,
    music=None,
    bed_mode="loop",
    bed_phase="auto",
    bpm=120.0,
    music_db=-6.0,
    bed_compress=True,
    ducks=(),
    hard_beats=(),
    target_lufs=-16.0,
    max_tp=-2.0,
    max_limiting=5.0,
    post_fade=1.4,
    tag="v1",
    seed=11,
    lead=0.03,
    name="piece",
    music_source="",
    music_license="",
    sfx_credit="",
    checks=(),
    fps=30,
    colors=None,
):
    os.makedirs(f"{out}/checks", exist_ok=True)
    random.seed(seed)
    dur = float(
        run_cmd(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                video,
            ]
        ).stdout
    )
    colors = colors or {"you": "#2f6fed", "product": "#1d1d1f", "world": "#c2410c"}
    last = {}

    def variant(fam):
        if fam not in family:
            raise SystemExit(
                f"cue family {fam} is not defined (families: {', '.join(sorted(family))})"
            )
        pool = family[fam]
        choices = [v for v in pool if v["path"] != last.get(fam)] or pool
        v = random.choice(choices)
        last[fam] = v["path"]
        return v

    # ---- place the cues
    cues = sorted(cues, key=lambda c: c["t"])
    mix = np.zeros(int((dur + 1) * SR), dtype=np.float32)
    placed = []
    for i, c in enumerate(cues):
        v = variant(c["fam"])
        a = _load(v["path"])
        if c.get(
            "until"
        ):  # sustained texture: tile to cover t..until with fades, no pitch variation
            need = int((c["until"] - c["t"]) * SR)
            a = np.tile(a, int(np.ceil(need / len(a))) + 1)[:need].copy()
            fi, fo = int(c.get("fin", 0.5) * SR), int(c.get("fout", 0.8) * SR)
            a[:fi] *= np.linspace(0, 1, fi)
            a[-fo:] *= np.linspace(1, 0, fo)
            rate = 1.0
        else:
            rate = c.get("rate", 1.0) * random.uniform(0.96, 1.04)
            a = _rate(a, rate)
            if c.get("maxlen") and len(a) > int(c["maxlen"] * SR):
                a = a[: int(c["maxlen"] * SR)].copy()
                f = int(0.06 * SR)
                a[-f:] *= np.linspace(1, 0, f)
        g = (
            c["db"]
            + (0 if c.get("until") else random.uniform(-1.5, 1.5))
            + v.get("trim_db", 0.0)
        )
        a = a * 10 ** (g / 20)
        peak = (v["peak"] / rate) if c.get("peak_align") else 0.0
        start = c["t"] - (0 if c.get("exact") or c.get("until") else lead) - peak
        s = int(max(0, start) * SR)
        n = min(len(a), len(mix) - s)
        mix[s : s + n] += a[:n]
        placed.append(
            {
                "i": i,
                "t": c["t"],
                "start": round(start, 3),
                "fam": c["fam"],
                "who": c.get("who", "you"),
                "file": os.path.basename(v["path"]),
                "db": round(g, 1),
                "rate": round(rate, 3),
                "desc": c["desc"],
            }
        )

    # ---- music bed (the user's own track; never stored in the skill)
    log = []
    if music:
        music_in = music
        if bed_compress:
            music_in = f"{out}/bed_mastered.wav"
            r = run_cmd(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-i",
                    music,
                    "-ac",
                    "1",
                    "-ar",
                    str(SR),
                    "-af",
                    "acompressor=threshold=-20dB:ratio=3:attack=8:release=180:makeup=2,alimiter=limit=0.891:level=true:attack=3:release=80",
                    music_in,
                ]
            )
            if r.returncode:
                raise SystemExit(r.stderr)
        y, _ = librosa.load(music_in, sr=SR, mono=True)
        beat = 60 / bpm
        bar = 4 * beat
        XF = 0.25
        if bed_mode == "search":
            tempo, bf = librosa.beat.beat_track(y=y, sr=SR, start_bpm=bpm)
            beats = librosa.frames_to_time(bf, sr=SR)
            best = None
            for s0 in np.arange(0.0, len(y) / SR - dur - 1, 0.01):
                e = sum(min(abs((beats - s0) - t)) for t in hard_beats)
                if best is None or e < best[0]:
                    best = (e, s0)
            mstart = float(best[1])
            resid = {t: float(min(abs((beats - mstart) - t))) for t in hard_beats}
            bed = y[int(mstart * SR) : int(mstart * SR) + len(mix)].copy()
            if len(bed) < len(mix):
                bed = np.pad(bed, (0, len(mix) - len(bed)))
            log.append(
                f"search bed: librosa tempo {float(np.atleast_1d(tempo)[0]):.1f}, start {mstart:.3f}s, beat-to-cue error "
                + ", ".join(f"{t:.2f}s={r * 1000:.0f}ms" for t, r in resid.items())
            )
        else:
            if bed_phase == "auto":
                tempo, bf = librosa.beat.beat_track(y=y, sr=SR, start_bpm=bpm)
                beats = librosa.frames_to_time(bf, sr=SR)
                k = np.arange(len(beats))
                slope, icpt = np.polyfit(k, beats, 1)
                real_bpm = 60 / slope
                stretch = slope * bpm / 60
                if abs(stretch - 1) > 0.0005:
                    y = librosa.effects.time_stretch(y, rate=stretch)
                    icpt = icpt / stretch
                phase = float(icpt % beat)
                note = f"detected {real_bpm:.2f} BPM, stretched x{stretch:.4f}"
            else:
                phase = 0.0
                note = f"assumed {bpm:.0f} BPM from a downbeat at 0 (no beat detection: bed has no percussion)"
            mstart = phase + bar * int(np.ceil((XF + 0.05 - phase) / bar))
            if mstart + dur + 0.1 > len(y) / SR:
                raise SystemExit("bed too short for a bar-aligned loop")
            s = int(mstart * SR)
            bed = y[s : s + len(mix)].copy()
            if len(bed) < len(mix):
                bed = np.pad(bed, (0, len(mix) - len(bed)))
            n = int(XF * SR)
            w = np.sin(np.linspace(0, np.pi / 2, n)) ** 2
            e = int(dur * SR)
            bed[e - n : e] = bed[e - n : e] * (1 - w) + y[s - n : s] * w
            bed[e:] = 0
            grid = np.arange(0, dur + 1, beat / 2)
            resid = {t: float(min(abs(grid - t))) for t in hard_beats}
            log.append(
                f"loop bed: {note}; start {mstart:.3f}s on a bar boundary; {dur:.1f}s = {dur / bar:.2f} bars; seam crossfade {XF * 1000:.0f} ms into the natural lead-in; "
                "grid error "
                + ", ".join(f"{t:.2f}s={r * 1000:.0f}ms" for t, r in resid.items())
            )
        env = np.ones(len(bed), dtype=np.float32)
        tt = np.arange(len(bed)) / SR

        def ramp(a, b, f, to):
            m = (tt >= a) & (tt < b)
            env[m] *= 10 ** ((f + (to - f) * (tt[m] - a) / (b - a)) / 20)

        for (
            a,
            b,
            db,
            pre,
            post,
        ) in ducks:  # duck the bed by db between a and b, with pre/post ramps
            ramp(a - pre, a, 0, db)
            env[(tt >= a) & (tt < b)] *= 10 ** (db / 20)
            ramp(b, b + post, db, 0)
        if bed_mode == "search":
            env[tt < 0.5] *= tt[tt < 0.5] / 0.5
            fo = tt > dur - 0.9
            env[fo] *= np.clip((dur - tt[fo]) / 0.9, 0, 1)
        mix[: len(bed)] += bed * env * 10 ** (music_db / 20)
    else:
        log.append(
            "no music bed (effects only)"
            + ("; a piece over about 10 s wants one" if dur > 10 else "")
        )
    mix = mix[: int(dur * SR)]
    sf.write(f"{out}/mix_raw.wav", mix, SR)

    # ---- export, measure, adjust
    out_mp4 = f"{out}/{name}-sound-{tag}.mp4"

    def export(gain_db, limit):
        af = f"volume={gain_db}dB" + (
            f",alimiter=limit={limit}:level=false:attack=3:release=60" if limit else ""
        )
        r = run_cmd(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                video,
                "-i",
                f"{out}/mix_raw.wav",
                "-map",
                "0:v",
                "-map",
                "1:a",
                "-c:v",
                "copy",
                "-af",
                af,
                "-c:a",
                "aac",
                "-b:a",
                "256k",
                "-shortest",
                out_mp4,
            ]
        )
        if r.returncode:
            raise SystemExit(r.stderr)

    g = (max_tp - 0.5) - 20 * np.log10(np.abs(mix).max() + 1e-9)
    lim = None
    export(g, lim)
    I, P = _measure(out_mp4)
    log.append(
        f"pass 1: peak-normalised, gain {g:+.1f} dB, limiter off -> {I:.1f} LUFS, true peak {P:.1f} dBTP"
    )
    short = target_lufs - I
    if short > 0.5:
        g += min(short, max_limiting)
        lim = round(10 ** ((max_tp - 0.5) / 20), 3)
        for it in range(5):
            export(g, lim)
            I, P = _measure(out_mp4)
            log.append(
                f"pass {it + 2}: gain {g:+.1f} dB, limiter ceiling {lim} -> {I:.1f} LUFS, true peak {P:.1f} dBTP"
            )
            if P <= max_tp:
                break
            lim = round(lim * 10 ** ((max_tp - P - 0.3) / 20), 3)
        if target_lufs - I > 0.5:
            log.append(
                f"NOTE: {target_lufs - I:.1f} dB short of the {target_lufs:.0f} LUFS target with limiting capped at {max_limiting:.0f} dB; reported, not forced."
            )
    post = None
    if post_fade > 0:
        post = out_mp4.replace(".mp4", "-post.mp4")
        r = run_cmd(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                out_mp4,
                "-c:v",
                "copy",
                "-af",
                f"afade=t=out:st={dur - post_fade:.3f}:d={post_fade:.3f}:curve=esin",
                "-c:a",
                "aac",
                "-b:a",
                "256k",
                post,
            ]
        )
        if r.returncode:
            raise SystemExit(r.stderr)
        Ip, Pp = _measure(post)
        log.append(
            f"single-play cut {os.path.basename(post)}: audio eases out over the last {post_fade:.1f}s -> {Ip:.1f} LUFS, true peak {Pp:.1f} dBTP"
        )
    log.append(
        f"FINAL: {I:.1f} LUFS integrated, true peak {P:.1f} dBTP ({os.path.basename(out_mp4)}, the seamless cut)"
    )

    # ---- proof
    run_cmd(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            out_mp4,
            "-ac",
            "1",
            "-ar",
            str(SR),
            f"{out}/after.wav",
        ]
    )
    au, _ = librosa.load(f"{out}/after.wav", sr=SR, mono=True)
    for c in placed:
        for tgl, dt in (("a", -0.08), ("b", 0.12)):
            run_cmd(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-ss",
                    f"{max(0, c['t'] + dt):.3f}",
                    "-i",
                    out_mp4,
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=320:-1",
                    f"{out}/checks/_{tgl}.png",
                ]
            )
        _fig, ax = plt.subplots(
            1, 3, figsize=(12, 2.6), gridspec_kw={"width_ratios": [1, 1, 2]}
        )
        for j, tgl in enumerate("ab"):
            ax[j].imshow(plt.imread(f"{out}/checks/_{tgl}.png"))
            ax[j].axis("off")
            ax[j].set_title("before" if tgl == "a" else "after")
        s0, s1 = max(0, c["t"] - 0.4), min(dur, c["t"] + 0.6)
        seg = au[int(s0 * SR) : int(s1 * SR)]
        ax[2].plot(np.linspace(s0, s1, len(seg)), seg, lw=0.4)
        ax[2].axvline(c["t"], color="r")
        ax[2].set_ylim(-1, 1)
        ax[2].set_title(
            f"cue {c['i']} @ {c['t']:.2f}s [{c['who']}] {c['fam']} <- {c['file']} ({c['db']:+.1f} dB)",
            fontsize=8,
        )
        plt.tight_layout()
        plt.savefig(f"{out}/checks/cue-{c['i']:02d}.png", dpi=80)
        plt.close()
    for f in ("_a.png", "_b.png"):
        if os.path.exists(f"{out}/checks/{f}"):
            os.remove(f"{out}/checks/{f}")
    _fig, ax = plt.subplots(figsize=(19, 3))
    ax.plot(np.arange(len(au)) / SR, au, lw=0.3, color="#985015")
    for c in placed:
        ax.axvline(c["t"], color=colors.get(c["who"], "#888"), lw=0.6, alpha=0.6)
    ax.set_xlim(0, dur)
    ax.set_title("after.wav with cue lines")
    plt.tight_layout()
    plt.savefig(f"{out}/overview.png", dpi=90)
    plt.close()
    seam = np.concatenate([au[-int(1.0 * SR) :], au[: int(1.0 * SR)]])
    _fig, ax = plt.subplots(figsize=(12, 2.4))
    ax.plot(np.linspace(-1, 1, len(seam)), seam, lw=0.3, color="#985015")
    ax.axvline(0, color="r")
    ax.set_title("loop seam: last second -> first second")
    plt.tight_layout()
    plt.savefig(f"{out}/seam.png", dpi=90)
    plt.close()

    rep = (
        [
            f"# SOUND.md ({name}, {tag}, generated by soundpass.py)",
            "",
            f"Music: {music_source} ({music_license})" if music else "Music: none",
            f"Sound effects: {sfx_credit}",
            "",
            "## Log",
        ]
        + ["- " + l for l in log]
        + ["", "## Cues (visual time, who, family, file, gain)"]
        + [
            f"- {c['t']:.2f}s [{c['who']}] {c['fam']} <- {c['file']} ({c['db']:+.1f} dB, rate {c['rate']}) {c['desc']}"
            for c in placed
        ]
        + ["", "## Check these with headphones"]
        + ["- " + s for s in checks]
        + [
            "",
            "Not claiming it sounds good: the model cannot hear. Every number above is measured on the exported MP4.",
        ]
    )
    with open(f"{out}/SOUND.md", "w") as f:
        f.write("\n".join(rep) + "\n")
    print(
        "\n".join(
            l
            for l in rep
            if l.startswith("- ")
            and (
                "pass" in l
                or "bed" in l
                or "FINAL" in l
                or "NOTE" in l
                or "single" in l
            )
        )
    )
    return {"mp4": out_mp4, "post": post, "lufs": I, "tp": P, "log": log}


def family_from_spec(spec, base):
    """Build the families named in a cues.json "family" block. base = the folder that relative paths start from."""
    fam = {}
    for name, f in spec.items():
        if "files" in f:
            for p in f["files"]:
                add_file(fam, name, os.path.join(base, p))
        elif f.get("lib") == "coldframe":
            fam.update(coldframe({name: (f["role"], f.get("maxms"))}))
        elif f.get("lib") == "barty-bart":
            fam.update(bartybart({name: f["category"]}, f.get("maxms")))
        elif f.get("lib"):
            fam.update(
                load_family(
                    os.path.join(base, f["lib"]), {name: (f["role"], f.get("maxms"))}
                )
            )
        else:
            raise SystemExit(f"family {name}: give lib + role/category, or files")
    return fam


def main():
    ap = argparse.ArgumentParser(
        description="Measured sound pass: silent MP4 + cues.json -> MP4 with sound, a -post cut, proof and SOUND.md."
    )
    ap.add_argument(
        "--video", required=True, help="the silent render, e.g. out/<slug>.mp4"
    )
    ap.add_argument(
        "--cues",
        required=True,
        help="cues.json (see the module docstring and templates/cues.json)",
    )
    ap.add_argument("--out", required=True, help="output folder, e.g. out/sound")
    ap.add_argument("--music", help="override the music file named in cues.json")
    ap.add_argument(
        "--tag", help="override the tag in cues.json (names the output files)"
    )
    A = ap.parse_args()
    with open(A.cues) as f:
        spec = json.load(f)
    base = os.path.dirname(os.path.abspath(A.cues))
    music = A.music or (
        os.path.join(base, spec["music"]) if spec.get("music") else None
    )
    if music and not (spec.get("music_source") and spec.get("music_license")):
        raise SystemExit(
            "cues.json: a music bed needs music_source and music_license, so SOUND.md records where the track came from"
        )
    run(
        A.video,
        spec["cues"],
        family_from_spec(spec["family"], base),
        A.out,
        music=music,
        name=spec.get("name", "piece"),
        tag=A.tag or spec.get("tag", "v1"),
        music_source=spec.get("music_source", ""),
        music_license=spec.get("music_license", ""),
        sfx_credit=spec.get("sfx_credit", ""),
        checks=spec.get("checks", []),
        **spec.get("options", {}),
    )


if __name__ == "__main__":
    main()
