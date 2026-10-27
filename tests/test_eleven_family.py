"""Tests for skills/product-sting/sound/eleven_family.py (run: python -m unittest discover -s tests -v).

No network and no key: the ElevenLabs API is replaced by a stand-in that returns synthetic audio, so these
tests check what the script does with a response (decoding, length check, splitting, trimming, the files it
writes and the credits it reports), not the live service, which is not exercised here.
"""

import contextlib
import io
import json
import os
import runpy
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
from helpers import SOUND, load_script

SR = 48000


def pcm_stereo(seconds, bursts):
    """16-bit interleaved stereo PCM, silent except a 440 Hz burst (start, length in s) per entry."""
    n = int(seconds * SR)
    mono = np.zeros(n, dtype=np.float32)
    for start, length in bursts:
        i, j = int(start * SR), int((start + length) * SR)
        mono[i:j] = 0.5 * np.sin(2 * np.pi * 440 * np.arange(j - i) / SR)
    pcm = (mono * 32767).astype("<i2")
    return np.repeat(pcm, 2).tobytes()


class FakeResponse:
    def __init__(self, body):
        self.body, self.headers = body, {}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Decoding(unittest.TestCase):
    def setUp(self):
        self.ef = load_script("eleven_family.py", "eleven_family_under_test")

    def test_stereo_pcm_is_downmixed_and_its_rate_read_from_the_format(self):
        raw = np.array([1000, 3000, -2000, 0], dtype="<i2").tobytes()
        audio, rate = self.ef.decode(raw, "pcm_48000")
        self.assertEqual(rate, 48000)
        np.testing.assert_allclose(audio, [2000 / 32768, -1000 / 32768], rtol=1e-6)

    def test_a_take_of_the_wrong_length_stops_the_run(self):
        self.ef.check_length(np.zeros(SR), SR, 1.0, "ok")
        self.ef.check_length(np.zeros(SR), SR, None, "no length asked")
        with self.assertRaises(SystemExit) as stop:
            self.ef.check_length(np.zeros(2 * SR), SR, 1.0, "tap #1")
        self.assertIn("PCM channel layout", str(stop.exception))

    def test_the_key_comes_only_from_the_environment(self):
        with (
            mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "  "}),
            self.assertRaises(SystemExit) as stop,
        ):
            self.ef._key()
        self.assertIn("ELEVENLABS_API_KEY", str(stop.exception))
        with mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": " k-123 "}):
            self.assertEqual(self.ef._key(), "k-123")


class SoundFamily(unittest.TestCase):
    def setUp(self):
        self.ef = load_script("eleven_family.py", "eleven_family_under_test")
        self.out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.out, True)
        self.written = {}
        self.ef.sf.write.side_effect = lambda path, data, sr: self.written.__setitem__(
            os.path.relpath(path, self.out), (np.array(data), sr)
        )
        self.ef.credits = mock.MagicMock(side_effect=[1000, 975])
        sleep = mock.patch.object(self.ef.time, "sleep")
        sleep.start()
        self.addCleanup(sleep.stop)

    def generate(self, spec, responses):
        self.ef.post = mock.MagicMock(side_effect=responses)
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            self.ef.gen_sfx(spec, self.out)
        return printed.getvalue()

    def test_writes_trimmed_takes_a_manifest_and_a_licence_note(self):
        spec = {
            "room": ", close microphone, dry",
            "roles": {"tap": ["a soft tap", 0.4, 2], "pop": ["two pops", 0.6, 1]},
            "split": ["pop"],
        }
        responses = [
            (pcm_stereo(0.4, [(0.1, 0.05)]), {}, None),
            (pcm_stereo(0.4, [(0.12, 0.05)]), {}, None),
            (pcm_stereo(0.6, [(0.05, 0.05), (0.35, 0.05)]), {}, None),
        ]
        printed = self.generate(spec, responses)
        self.assertIn(
            "requested 1.4 s of sound effects in 3 takes: up to 56 credits", printed
        )
        self.assertIn("credits used: 25", printed)
        with open(os.path.join(self.out, "manifest.json")) as f:
            manifest = json.load(f)
        self.assertEqual(manifest["credits_used"], 25)
        self.assertEqual(
            manifest["roles"]["tap"]["prompt"], "a soft tap, close microphone, dry"
        )
        self.assertEqual(
            [v["file"] for v in manifest["roles"]["tap"]["variants"]],
            ["tap-1.wav", "tap-2.wav"],
        )
        self.assertEqual(
            [v["file"] for v in manifest["roles"]["pop"]["variants"]],
            ["pop-1-e1.wav", "pop-1-e2.wav"],
        )
        for name in ("tap-1.wav", "tap-2.wav", "pop-1-e1.wav", "pop-1-e2.wav"):
            audio, rate = self.written[name]
            self.assertEqual(rate, SR)
            self.assertAlmostEqual(
                float(np.abs(audio).max()), 10 ** (-8 / 20), places=5
            )
        self.assertIn(os.path.join("raw", "pop-1.wav"), self.written)
        with open(os.path.join(self.out, "LICENSE.md")) as f:
            note = f.read()
        self.assertTrue(
            note.startswith("# ElevenLabs generated sound effects\n\nGenerated ")
        )
        self.assertTrue(note.endswith("Prompts are in manifest.json.\n"))
        first_call = self.ef.post.call_args_list[0]
        self.assertEqual(first_call.args[0], "/sound-generation")
        self.assertEqual(first_call.args[2], "pcm_48000")

    def test_a_take_twice_the_asked_length_stops_before_more_credits_are_spent(self):
        spec = {"roles": {"tap": ["a soft tap", 0.4, 3]}}
        with self.assertRaises(SystemExit):
            self.generate(spec, [(pcm_stereo(0.8, [(0.1, 0.05)]), {}, None)])
        self.assertEqual(self.ef.post.call_count, 1)
        self.assertFalse(os.path.exists(os.path.join(self.out, "manifest.json")))


class MusicBed(unittest.TestCase):
    def test_writes_each_candidate_and_a_measured_report(self):
        ef = load_script("eleven_family.py", "eleven_family_under_test")
        out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, out, True)
        ef.credits = mock.MagicMock(side_effect=[5000, 4400])
        ef.post = mock.MagicMock(return_value=(b"ID3 fake mp3 bytes", {}, None))
        y = 0.25 * np.sin(2 * np.pi * 110 * np.arange(20 * SR) / SR).astype(np.float32)
        ef.librosa.load.return_value = (y, SR)
        ef.librosa.beat.beat_track.return_value = (np.array([120.0]), np.arange(40))
        ef.librosa.frames_to_time.return_value = np.arange(40) * 0.5
        ef.librosa.feature.rms.return_value = np.array([[0.1, 0.1, 0.1]])
        with contextlib.redirect_stdout(io.StringIO()):
            ef.gen_music("calm bed", out, "bed", 2, 20000)
        for name in ("bed-1.mp3", "bed-2.mp3"):
            with open(os.path.join(out, name), "rb") as f:
                self.assertEqual(f.read(), b"ID3 fake mp3 bytes")
        with open(os.path.join(out, "bed.json")) as f:
            report = json.load(f)
        self.assertEqual(report["credits_used_counter"], 600)
        self.assertEqual(report["prompt"], "calm bed")
        first = report["candidates"][0]
        self.assertEqual(
            (
                first["file"],
                first["model"],
                first["seconds"],
                first["tempo"],
                first["beat_period"],
                first["rms_cv"],
            ),
            ("bed-1.mp3", "music_v2_5", 20.0, 120.0, 0.5, 0.0),
        )
        self.assertAlmostEqual(first["crest_db"], 3.0, delta=0.05)
        body = ef.post.call_args.args[1]
        self.assertEqual(body["force_instrumental"], True)
        self.assertEqual(body["music_length_ms"], 20000)


KEY = "test-key-7c1e9"


class CommandLine(unittest.TestCase):
    """The script run as a program, with the network replaced and stand-in audio packages."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.written = []
        soundfile = mock.MagicMock(name="soundfile")
        soundfile.write.side_effect = lambda path, data, sr: self.written.append(
            os.path.basename(path)
        )
        self.librosa = mock.MagicMock(name="librosa")
        self.modules = {"librosa": self.librosa, "soundfile": soundfile}
        self.balance = iter([800, 790, 780])
        self.bodies = []

    def urlopen(self, req, timeout):
        self.assertTrue(
            req.full_url.startswith("https://api.elevenlabs.io/v1/"), req.full_url
        )
        self.assertEqual(
            req.get_header("Xi-api-key"), KEY, "the key goes only in its header"
        )
        self.assertNotIn(KEY, req.full_url)
        self.assertNotIn(KEY.encode(), req.data or b"")
        if req.full_url.endswith("/user/subscription"):
            return FakeResponse(
                json.dumps(
                    {
                        "character_limit": 1000,
                        "character_count": 1000 - next(self.balance),
                    }
                ).encode()
            )
        self.bodies.append(json.loads(req.data))
        if "/music" in req.full_url:
            return FakeResponse(b"ID3 fake")
        return FakeResponse(pcm_stereo(0.3, [(0.05, 0.05)]))

    def run_script(self, *args):
        argv = ["eleven_family.py", *args]
        with (
            mock.patch.dict(sys.modules, self.modules),
            mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": KEY}),
            mock.patch.object(sys, "argv", argv),
            mock.patch("urllib.request.urlopen", self.urlopen),
            mock.patch("time.sleep"),
            contextlib.redirect_stdout(io.StringIO()) as printed,
        ):
            try:
                runpy.run_path(
                    os.path.join(SOUND, "eleven_family.py"), run_name="__main__"
                )
            except SystemExit as stop:
                self.assertIn(stop.code, (0, None))
        self.assertNotIn(KEY, printed.getvalue(), "the key is never printed")
        return printed.getvalue()

    def assert_key_in_no_file(self, folder):
        for dirpath, _dirs, files in os.walk(folder):
            for name in files:
                with open(os.path.join(dirpath, name), "rb") as f:
                    self.assertNotIn(KEY.encode(), f.read(), name)

    def test_sfx_reads_the_spec_file_and_writes_the_family(self):
        spec = os.path.join(self.dir, "family.json")
        with open(spec, "w") as f:
            json.dump({"room": ", dry", "roles": {"tick": ["a tick", 0.3, 1]}}, f)
        out = os.path.join(self.dir, "family-brand")
        self.run_script("sfx", "--spec", spec, "--out", out)
        self.assertEqual(self.bodies[0]["text"], "a tick, dry")
        self.assertIn("tick-1.wav", self.written)
        with open(os.path.join(out, "manifest.json")) as f:
            self.assertEqual(json.load(f)["credits_used"], 10)
        self.assertTrue(os.path.exists(os.path.join(out, "LICENSE.md")))
        self.assert_key_in_no_file(self.dir)

    def test_music_reads_the_prompt_file(self):
        prompt = os.path.join(self.dir, "bed.txt")
        with open(prompt, "w") as f:
            f.write("  warm bed, shaker on every beat \n")
        y = np.full(SR, 0.1, dtype=np.float32)
        self.librosa.load.return_value = (y, SR)
        self.librosa.beat.beat_track.return_value = (np.array([118.0]), np.arange(4))
        self.librosa.frames_to_time.return_value = np.array([0.0, 0.5, 1.0, 1.5])
        self.librosa.feature.rms.return_value = np.array([[0.1, 0.1]])
        out = os.path.join(self.dir, "music")
        self.run_script(
            "music", "--prompt-file", prompt, "--out", out, "--n", "1", "--ms", "10000"
        )
        self.assertEqual(self.bodies[0]["prompt"], "warm bed, shaker on every beat")
        self.assertEqual(self.bodies[0]["music_length_ms"], 10000)
        with open(os.path.join(out, "bed.json")) as f:
            self.assertEqual(json.load(f)["candidates"][0]["file"], "bed-1.mp3")
        self.assert_key_in_no_file(self.dir)

    def test_credits_prints_the_balance(self):
        self.assertEqual(self.run_script("credits").strip(), "800")


if __name__ == "__main__":
    unittest.main()
