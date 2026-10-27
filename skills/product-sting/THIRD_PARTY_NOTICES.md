# Third-party notices

The skill's own code and documents are MIT licensed (`LICENSE`, with a copy in `skills/product-sting/LICENSE`). It bundles two sets of third-party sound files, listed below with their sources and licences. This file is copied to `skills/product-sting/THIRD_PARTY_NOTICES.md` too, so an installed copy of the skill carries these notices. No music is bundled: the user supplies any track, and its source and licence are recorded in that piece's SOUND.md.

## Coldframe sound library

- **Path:** `skills/product-sting/sound/lib/coldframe/`: 37 WAV files, `library.json` and `LICENSE.md`.
- **Source:** [Razee4315/coldframe](https://github.com/Razee4315/coldframe) (its `sound-design` skill), retrieved 15 October 2026.
- **Sounds: CC0 1.0** (public domain dedication; no attribution required). 35 are trimmed, level-matched files from Kenney's [UI Audio](https://kenney.nl/assets/ui-audio), [Interface Sounds](https://kenney.nl/assets/interface-sounds) and [Impact Sounds](https://kenney.nl/assets/impact-sounds) packs; `whoosh-1.wav` and `whoosh-2.wav` are Freesound sounds [831936](https://freesound.org/s/831936/) and [838766](https://freesound.org/s/838766/), obtained via remotion.media. Each file's source is listed in `LICENSE.md` and `library.json` in that folder.
- **`library.json` and `LICENSE.md`** are files from the Coldframe repository, under its MIT licence:

```
MIT License

Copyright (c) 2026 Saqlain Abbas (Razee4315)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Barty-Bart sound library

- **Path:** `skills/product-sting/sound/lib/barty-bart/`: 109 OGG files in 13 folders (12 categories and a six-sound default kit), `manifest.json` and `LICENSES.md`.
- **Source:** [Barty-Bart/motion-graphics](https://github.com/Barty-Bart/motion-graphics) (its `sound-effects` skill; manifest dated 12 October 2026), retrieved 15 October 2026.
- **Sounds: CC0 1.0** (public domain dedication; attribution optional, given in the licence file). They are Kenney packs (Interface Sounds, UI Audio, Digital Audio, Impact Sounds, Sci-fi Sounds, [kenney.nl/assets](https://kenney.nl/assets)) and Freesound sounds whose pages showed CC0, checked per sound by the upstream author on 12 October 2026; the Freesound files are Freesound's compressed previews. Each file's author and source page are listed in `LICENSES.md` and `manifest.json` in that folder.
- **Not bundled:** the upstream manifest also lists Mixkit sounds as runtime downloads. Mixkit's licence does not allow redistributing the files, so none are included here, and the sound pass never downloads them.
- **`manifest.json` and `LICENSES.md`** are files from the Barty-Bart repository, under its MIT licence:

```
MIT License

Copyright (c) 2026 Bart

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Methods credited

Ideas only: no third-party code or text is reproduced in the skill's own files.

- The "one shape, never cut" UI-morph format and its build rules (seek(t) only, one spring per target change, stills per beat before the full render) follow a public prompt by @twoclipping, collected in [guanmo-ai/awesome-ai-motion](https://github.com/guanmo-ai/awesome-ai-motion). The spec template here is written fresh.
- "Reads", contact sheets and frame strips as review tools come from John Heibel's `ANIMATION_GUIDE.md` in [JohnHeibel/ClaudeAnimationBase](https://github.com/JohnHeibel/ClaudeAnimationBase) (MIT).
- The measured sound pass follows the sound-pass approach credited to Vox (@Voxyz_ai) as packaged in Barty-Bart's `sound-effects` skill, with the level, variation, sync and loudness rules of Coldframe's `sound-design` skill. `soundpass.py` is written for this skill.
- Placing each sound about 0.03s before its visual comes from Hanif's [claude-animation-skill](https://github.com/buildwithhanif/claude-animation-skill) (MIT), whose synthesised sound tools earlier versions of this skill bundled.
