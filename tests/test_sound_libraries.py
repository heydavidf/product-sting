"""Every bundled sound must be listed, sourced and CC0 (run: python -m unittest discover -s tests -v).

The skill redistributes these files, so a sound without a clear CC0 source, or a file that its library's
manifest and licence file do not list, must not be added. Music is never bundled.
"""

import json
import os
import unittest

from helpers import SKILL, SOUND

LIB = os.path.join(SOUND, "lib")
AUDIO = (".wav", ".ogg", ".mp3", ".flac", ".m4a", ".aac", ".aif", ".aiff", ".opus")


def audio_files(folder):
    found = []
    for dirpath, _dirs, files in os.walk(folder):
        found += [
            os.path.relpath(os.path.join(dirpath, f), folder)
            for f in files
            if f.lower().endswith(AUDIO)
        ]
    return sorted(found)


class SoundLibraries(unittest.TestCase):
    def test_coldframe_lists_every_file_in_its_manifest_and_licence(self):
        folder = os.path.join(LIB, "coldframe")
        with open(os.path.join(folder, "library.json")) as f:
            library = json.load(f)
        with open(os.path.join(folder, "LICENSE.md")) as f:
            licence = f.read()
        listed = sorted(
            {v["file"] for role in library["roles"].values() for v in role["variants"]}
        )
        self.assertEqual(audio_files(folder), listed)
        self.assertIn("CC0", licence)
        for name in listed:
            self.assertIn(
                name, licence, f"{name} has no source line in coldframe/LICENSE.md"
            )

    def test_barty_bart_bundles_only_listed_cc0_files(self):
        folder = os.path.join(LIB, "barty-bart")
        with open(os.path.join(folder, "manifest.json")) as f:
            manifest = json.load(f)
        with open(os.path.join(folder, "LICENSES.md")) as f:
            licences = f.read()
        bundled = [
            e
            for e in manifest["default_kit"] + manifest["bundled"]
            if e.get("file") and e.get("bundled", True)
        ]
        self.assertEqual(audio_files(folder), sorted(e["file"] for e in bundled))
        for e in bundled:
            with self.subTest(file=e["file"]):
                self.assertEqual(e["license"], "CC0 1.0")
                self.assertTrue(
                    e["source_url"].startswith(
                        ("https://freesound.org/", "https://kenney.nl/")
                    ),
                    e["source_url"],
                )
                self.assertIn(os.path.basename(e["file"]), licences)

    def test_the_barty_bart_copy_has_no_download_entries(self):
        folder = os.path.join(LIB, "barty-bart")
        with open(os.path.join(folder, "manifest.json")) as f:
            manifest = json.load(f)
        with open(os.path.join(folder, "LICENSES.md")) as f:
            licences = f.read()
        self.assertNotIn("runtime", manifest)
        for e in manifest["default_kit"] + manifest["bundled"]:
            self.assertTrue(e.get("file"), e)
            self.assertNotIn("runtime_url", e)
        self.assertNotIn("runtime:", licences)
        self.assertNotIn("so the skill downloads them", licences)

    def test_each_library_carries_its_upstream_mit_licence(self):
        for name, holder in (
            ("coldframe", "Saqlain Abbas (Razee4315)"),
            ("barty-bart", "Bart"),
        ):
            with self.subTest(library=name):
                with open(os.path.join(LIB, name, "UPSTREAM-LICENSE.txt")) as f:
                    text = f.read()
                self.assertTrue(text.startswith("MIT License\n"))
                self.assertIn(f"Copyright (c) 2026 {holder}\n", text)
                self.assertIn(
                    "The above copyright notice and this permission notice", text
                )

    def test_no_audio_outside_the_two_libraries(self):
        everywhere = audio_files(SKILL)
        inside = [
            os.path.join("sound", "lib", "coldframe", f)
            for f in audio_files(os.path.join(LIB, "coldframe"))
        ]
        inside += [
            os.path.join("sound", "lib", "barty-bart", f)
            for f in audio_files(os.path.join(LIB, "barty-bart"))
        ]
        self.assertEqual(everywhere, sorted(inside))
        self.assertEqual(sorted(os.listdir(LIB)), ["barty-bart", "coldframe"])


if __name__ == "__main__":
    unittest.main()
