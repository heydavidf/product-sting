"""Tests for skills/product-sting/sound/soundpass.py (run: python -m unittest discover -s tests -v).

They check the decisions the pass makes (where each cue lands in the mix, how loud, the level trim, the
licence refusal, the loudness passes) with synthetic sounds and stand-in ffmpeg, librosa and matplotlib.
The expected values follow the rules written in soundpass.py's docstring and SKILL.md Step 7, replaying the
seeded random choices independently.
"""

import contextlib
import io
import itertools
import json
import math
import os
import random
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np
from helpers import SKILL, SOUND, load_script

SR = 48000


def fake_run_cmd(duration):
    """Stand-in for soundpass.run_cmd: ffprobe reports the duration, every ffmpeg call succeeds."""

    def run(cmd):
        if cmd[0] == "ffprobe":
            return SimpleNamespace(stdout=f"{duration}\n", stderr="", returncode=0)
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    return run


class RunHarness:
    """Runs soundpass.run() with synthetic sounds and records the mix it writes."""

    def __init__(self, test, sounds, duration=6.0, measures=None):
        self.sp = load_script("soundpass.py", "soundpass_under_test")
        self.sounds = sounds
        self.written = {}
        self.out = tempfile.mkdtemp()
        test.addCleanup(shutil.rmtree, self.out, True)
        sp = self.sp
        sp._load = lambda path: self.sounds[os.path.basename(path)].copy()
        sp.run_cmd = fake_run_cmd(duration)
        sp._measure = mock.MagicMock(
            side_effect=measures or [(-16.2, -2.4), (-16.3, -2.5)]
        )
        sp.sf.write.side_effect = lambda path, data, sr: self.written.__setitem__(
            os.path.basename(path), np.array(data)
        )
        sp.librosa.load.return_value = (
            np.zeros(int(duration * SR), dtype=np.float32),
            SR,
        )
        sp.plt.subplots.side_effect = lambda *a, **k: (
            mock.MagicMock(),
            mock.MagicMock(),
        )

    def run(self, cues, family, **options):
        with contextlib.redirect_stdout(io.StringIO()):
            result = self.sp.run("piece.mp4", cues, family, self.out, **options)
        with open(os.path.join(self.out, "SOUND.md")) as f:
            self.sound_md = f.read()
        return result


def replay(cues, family, seed=11):
    """The seeded choices the pass makes, in its order: a take (never the last one used), a rate, a gain."""
    rng = random.Random(seed)
    last, plan = {}, []
    for c in sorted(cues, key=lambda c: c["t"]):
        pool = family[c["fam"]]
        v = rng.choice([v for v in pool if v["path"] != last.get(c["fam"])] or pool)
        last[c["fam"]] = v["path"]
        if c.get("until"):
            rate, jitter = 1.0, 0.0
        else:
            rate = c.get("rate", 1.0) * rng.uniform(0.96, 1.04)
            jitter = rng.uniform(-1.5, 1.5)
        plan.append(
            {
                "cue": c,
                "take": v,
                "rate": rate,
                "gain_db": c["db"] + jitter + v.get("trim_db", 0.0),
            }
        )
    return plan


def take(name, peak=0.0, trim_db=0.0):
    return {"path": f"/lib/{name}", "file": name, "peak": peak, "trim_db": trim_db}


class CuePlacement(unittest.TestCase):
    def setUp(self):
        level = 0.1
        self.sounds = {
            "press-1.wav": np.full(2400, level, dtype=np.float32),
            "press-2.wav": np.full(2400, level, dtype=np.float32),
            "whoosh.wav": np.full(4800, level, dtype=np.float32),
            "rain.wav": np.full(4800, level, dtype=np.float32),
        }
        self.level = level
        self.family = {
            "press": [take("press-1.wav", trim_db=-2.0), take("press-2.wav")],
            "whoosh": [take("whoosh.wav", peak=0.04)],
            "rain": [take("rain.wav")],
        }
        self.cues = [
            {"t": 1.0, "fam": "press", "db": -2, "desc": "press"},
            {
                "t": 0.01,
                "fam": "press",
                "db": -4,
                "desc": "first press, before the lead allows",
            },
            {
                "t": 2.0,
                "fam": "whoosh",
                "db": -7,
                "desc": "whoosh",
                "peak_align": True,
                "rate": 1.12,
            },
            {"t": 3.0, "fam": "press", "db": -3, "desc": "exact press", "exact": True},
            {
                "t": 4.0,
                "fam": "rain",
                "db": -10,
                "desc": "rain",
                "until": 5.0,
                "fin": 0.1,
                "fout": 0.1,
            },
        ]
        self.h = RunHarness(self, self.sounds)
        self.h.run(self.cues, self.family, name="demo")
        self.mix = self.h.written["mix_raw.wav"]
        self.plan = replay(self.cues, self.family)

    def expected_start(self, step):
        c = step["cue"]
        lead = 0 if c.get("exact") or c.get("until") else 0.03
        peak = step["take"]["peak"] / step["rate"] if c.get("peak_align") else 0.0
        return c["t"] - lead - peak

    def test_mix_is_the_piece_length(self):
        self.assertEqual(len(self.mix), int(6.0 * SR))

    def test_each_cue_starts_where_the_rules_put_it_at_its_gain(self):
        for step in self.plan:
            if step["cue"].get("until"):
                continue
            start = int(max(0.0, self.expected_start(step)) * SR)
            length = int(len(self.sounds[step["take"]["file"]]) / step["rate"])
            amplitude = self.level * 10 ** (step["gain_db"] / 20)
            with self.subTest(cue=step["cue"]["desc"]):
                if start > 0:
                    self.assertEqual(self.mix[start - 1], 0.0)
                self.assertAlmostEqual(
                    float(self.mix[start]), amplitude, delta=amplitude * 1e-5
                )
                self.assertAlmostEqual(
                    float(self.mix[start + length - 1]),
                    amplitude,
                    delta=amplitude * 1e-5,
                )
                self.assertEqual(self.mix[start + length], 0.0)

    def test_lead_peak_alignment_and_exact_cues(self):
        by_desc = {s["cue"]["desc"]: s for s in self.plan}
        self.assertAlmostEqual(self.expected_start(by_desc["press"]), 1.0 - 0.03)
        whoosh = by_desc["whoosh"]
        self.assertAlmostEqual(
            self.expected_start(whoosh), 2.0 - 0.03 - 0.04 / whoosh["rate"]
        )
        self.assertAlmostEqual(self.expected_start(by_desc["exact press"]), 3.0)
        self.assertTrue(1.12 * 0.96 <= whoosh["rate"] <= 1.12 * 1.04)

    def test_a_cue_before_the_lead_starts_at_zero_whole(self):
        first = self.plan[0]
        length = int(len(self.sounds[first["take"]["file"]]) / first["rate"])
        amplitude = self.level * 10 ** (first["gain_db"] / 20)
        self.assertAlmostEqual(float(self.mix[0]), amplitude, delta=amplitude * 1e-5)
        self.assertEqual(self.mix[length], 0.0)

    def test_sustained_texture_tiles_from_t_to_until_with_fades_and_no_variation(self):
        rain = next(s for s in self.plan if s["cue"].get("until"))
        start, need = int(4.0 * SR), int(1.0 * SR)
        amplitude = self.level * 10 ** (-10 / 20)
        self.assertEqual(rain["gain_db"], -10)
        self.assertEqual(self.mix[start - 1], 0.0)
        self.assertEqual(self.mix[start], 0.0)
        self.assertAlmostEqual(
            float(self.mix[start + need // 2]), amplitude, delta=amplitude * 1e-5
        )
        self.assertAlmostEqual(
            float(self.mix[start + int(0.1 * SR) + 10]),
            amplitude,
            delta=amplitude * 1e-5,
        )
        self.assertEqual(self.mix[start + need - 1], 0.0)
        self.assertEqual(self.mix[start + need], 0.0)
        self.assertTrue(
            np.all(np.abs(self.mix[start : start + need]) <= amplitude * (1 + 1e-5))
        )

    def test_never_the_same_take_twice_in_a_row(self):
        presses = [s["take"]["file"] for s in self.plan if s["cue"]["fam"] == "press"]
        self.assertEqual(len(presses), 3)
        self.assertTrue(all(a != b for a, b in itertools.pairwise(presses)))

    def test_sound_md_lists_every_cue_with_its_take_gain_and_rate(self):
        for step in self.plan:
            c = step["cue"]
            line = (
                f"- {c['t']:.2f}s [you] {c['fam']} <- {step['take']['file']} "
                f"({round(step['gain_db'], 1):+.1f} dB, rate {round(step['rate'], 3)}) {c['desc']}"
            )
            self.assertIn(line, self.h.sound_md)
        self.assertIn(
            "Not claiming it sounds good: the model cannot hear.", self.h.sound_md
        )
        self.assertIn("Music: none", self.h.sound_md)

    def test_unknown_family_stops_the_pass(self):
        h = RunHarness(self, self.sounds)
        with self.assertRaises(SystemExit) as stop:
            h.run([{"t": 1.0, "fam": "nope", "db": 0, "desc": "x"}], self.family)
        self.assertIn("cue family nope is not defined", str(stop.exception))


class Loudness(unittest.TestCase):
    def setUp(self):
        self.sounds = {"click.wav": np.full(2400, 0.1, dtype=np.float32)}
        self.family = {"click": [take("click.wav")]}
        self.cues = [{"t": 1.0, "fam": "click", "db": 0, "desc": "click"}]

    def test_limits_within_the_cap_until_the_true_peak_fits(self):
        h = RunHarness(
            self, self.sounds, measures=[(-20.0, -3.0), (-16.4, -2.6), (-16.6, -2.7)]
        )
        result = h.run(self.cues, self.family, name="demo")
        log = "\n".join(result["log"])
        self.assertIn("pass 1: peak-normalised", log)
        self.assertIn("pass 2: gain", log)
        self.assertIn("limiter ceiling 0.75 -> -16.4 LUFS, true peak -2.6 dBTP", log)
        self.assertNotIn("NOTE", log)
        self.assertEqual((result["lufs"], result["tp"]), (-16.4, -2.6))
        self.assertTrue(result["post"].endswith("demo-sound-v1-post.mp4"))
        self.assertIn("audio eases out over the last 1.4s -> -16.6 LUFS", log)

    def test_a_shortfall_is_reported_not_forced(self):
        h = RunHarness(
            self, self.sounds, measures=[(-22.0, -3.0), (-19.7, -2.5), (-19.7, -2.5)]
        )
        result = h.run(self.cues, self.family, name="demo")
        self.assertIn(
            "NOTE: 3.7 dB short of the -16 LUFS target with limiting capped at 5 dB; reported, not forced.",
            result["log"],
        )
        self.assertIn("no music bed (effects only)", result["log"])


class LevelTrim(unittest.TestCase):
    def setUp(self):
        self.sp = load_script("soundpass.py", "soundpass_under_test")

    def test_coldframe_files_are_used_at_their_level_with_the_listed_peak(self):
        with open(os.path.join(SOUND, "lib", "coldframe", "library.json")) as f:
            library = json.load(f)
        family = self.sp.coldframe({"press": "click-firm"})["press"]
        listed = library["roles"]["click-firm"]["variants"]
        self.assertEqual([v["file"] for v in family], [v["file"] for v in listed])
        for got, want in zip(family, listed, strict=True):
            self.assertEqual(got["trim_db"], 0.0)
            self.assertEqual(got["peak"], want["peakMs"] / 1000)
            self.assertTrue(os.path.exists(got["path"]))

    def test_a_length_limit_keeps_only_short_takes(self):
        with open(os.path.join(SOUND, "lib", "coldframe", "library.json")) as f:
            library = json.load(f)
        variants = library["roles"]["whoosh"]["variants"]
        limit = min(v["ms"] for v in variants)
        family = self.sp.coldframe({"w": ("whoosh", limit)})["w"]
        self.assertEqual(
            [v["file"] for v in family],
            [v["file"] for v in variants if v["ms"] <= limit],
        )
        with self.assertRaises(SystemExit):
            self.sp.coldframe({"w": ("whoosh", limit - 1)})
        with self.assertRaises(SystemExit) as stop:
            self.sp.coldframe({"x": "no-such-role"})
        self.assertIn("role no-such-role not in", str(stop.exception))

    def test_other_files_are_trimmed_so_their_peak_sits_at_minus_8_dbfs(self):
        peaks = {}

        def load(path):
            a = np.zeros(SR // 2, dtype=np.float32)
            level = 0.2 + 0.1 * (len(peaks) % 5)
            a[SR // 10] = level
            peaks[os.path.basename(path)] = level
            return a

        self.sp._load = load
        family = self.sp.bartybart({"tick": "tick"})["tick"]
        with open(os.path.join(SOUND, "lib", "barty-bart", "manifest.json")) as f:
            manifest = json.load(f)
        entries = [
            e
            for e in manifest["default_kit"] + manifest["bundled"]
            if e.get("file") and e.get("bundled", True)
        ]
        expected = [
            os.path.basename(e["file"]) for e in entries if e["category"] == "tick"
        ]
        self.assertEqual([v["file"] for v in family], expected)
        self.assertEqual(family[0]["file"], "tick.ogg", "the default kit comes first")
        for v in family:
            level_db = 20 * math.log10(peaks[v["file"]] + 1e-9)
            self.assertAlmostEqual(v["trim_db"], -8.0 - level_db, places=4)
            self.assertAlmostEqual(v["peak"], 0.1, delta=0.006)

    def test_a_given_peak_and_trim_are_kept_as_given(self):
        self.sp._load = mock.MagicMock(
            side_effect=AssertionError("nothing should be measured")
        )
        fam = {}
        self.sp.add_file(fam, "own", "/x/my-click.wav", peak=0.05, trim_db=-3.0)
        self.assertEqual(
            fam["own"],
            [
                {
                    "path": "/x/my-click.wav",
                    "peak": 0.05,
                    "file": "my-click.wav",
                    "trim_db": -3.0,
                }
            ],
        )


class LicenceRefusal(unittest.TestCase):
    def setUp(self):
        self.sp = load_script("soundpass.py", "soundpass_under_test")
        self.sp.run = mock.MagicMock()
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)

    def main(self, spec, *extra):
        path = os.path.join(self.dir, "cues.json")
        with open(path, "w") as f:
            json.dump(spec, f)
        argv = [
            "soundpass.py",
            "--video",
            "out/piece.mp4",
            "--cues",
            path,
            "--out",
            "out/sound",
            *extra,
        ]
        with mock.patch.object(sys, "argv", argv):
            self.sp.main()

    def spec(self, **extra):
        base = {
            "name": "demo",
            "family": {"press": {"lib": "coldframe", "role": "click-firm"}},
            "cues": [{"t": 0.9, "fam": "press", "db": -2, "desc": "press"}],
        }
        base.update(extra)
        return base

    def test_a_bed_without_source_and_licence_is_refused(self):
        for extra in ({}, {"music_source": "My track"}, {"music_license": "CC BY 4.0"}):
            with self.subTest(given=extra), self.assertRaises(SystemExit) as stop:
                self.main(self.spec(music="music/track.mp3", **extra))
            self.assertIn(
                "a music bed needs music_source and music_license", str(stop.exception)
            )
        self.sp.run.assert_not_called()

    def test_a_music_override_needs_the_licence_too(self):
        with self.assertRaises(SystemExit):
            self.main(self.spec(), "--music", "other.mp3")
        self.sp.run.assert_not_called()

    def test_a_bed_with_source_and_licence_runs_with_paths_relative_to_cues_json(self):
        self.main(
            self.spec(
                music="music/track.mp3",
                music_source="Own recording",
                music_license="CC0 1.0",
                options={"bpm": 100},
            )
        )
        kwargs = self.sp.run.call_args.kwargs
        self.assertEqual(kwargs["music"], os.path.join(self.dir, "music/track.mp3"))
        self.assertEqual(
            (kwargs["music_source"], kwargs["music_license"]),
            ("Own recording", "CC0 1.0"),
        )
        self.assertEqual(kwargs["bpm"], 100)

    def test_no_music_needs_no_licence(self):
        self.main(self.spec())
        self.assertIsNone(self.sp.run.call_args.kwargs["music"])


class StarterCueList(unittest.TestCase):
    def test_the_starter_cue_list_resolves_against_the_bundled_libraries(self):
        sp = load_script("soundpass.py", "soundpass_under_test")
        sp._load = lambda path: np.full(4800, 0.5, dtype=np.float32)
        templates = os.path.join(SKILL, "templates")
        with open(os.path.join(templates, "cues.json")) as f:
            spec = json.load(f)
        family = sp.family_from_spec(spec["family"], templates)
        self.assertEqual(sorted(family), sorted(spec["family"]))
        for name, takes in family.items():
            self.assertTrue(takes, name)
            for t in takes:
                self.assertTrue(os.path.exists(t["path"]), t["path"])
        self.assertTrue(all(c["fam"] in family for c in spec["cues"]))
        self.assertIsNone(spec["music"])
        loudest = max(spec["cues"], key=lambda c: c["db"])
        self.assertEqual(
            loudest["fam"], "reward", "the one reward sound is the loudest cue"
        )


if __name__ == "__main__":
    unittest.main()
