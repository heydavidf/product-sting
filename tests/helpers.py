"""Shared helpers for the sound tests: import the sound scripts with stand-ins for their heavy packages.

The tests need numpy (pinned in skills/product-sting/sound/requirements.txt) and nothing else outside the
standard library. librosa, soundfile and matplotlib are replaced by stand-ins, so every file read, sound
measurement, plot and ffmpeg call is controlled by the test and no audio is decoded or rendered.
"""

import importlib.util
import os
import sys
import types
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "product-sting")
SOUND = os.path.join(SKILL, "sound")


def load_script(filename, module_name):
    """Import one of the sound scripts by path, with stand-in librosa, soundfile and matplotlib modules."""
    stubs = {
        name: types.ModuleType(name)
        for name in ("librosa", "soundfile", "matplotlib", "matplotlib.pyplot")
    }
    stubs["matplotlib"].use = lambda backend: None
    stubs["matplotlib"].pyplot = stubs["matplotlib.pyplot"]
    with mock.patch.dict(sys.modules, stubs):
        spec = importlib.util.spec_from_file_location(
            module_name, os.path.join(SOUND, filename)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    module.librosa = mock.MagicMock(name="librosa")
    module.sf = mock.MagicMock(name="soundfile")
    if hasattr(module, "plt"):
        module.plt = mock.MagicMock(name="pyplot")
    return module
