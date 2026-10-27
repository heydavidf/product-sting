# product-sting contributor guide

This repository holds one agent skill, `product-sting`, which turns a brand guide and product screens into a short motion piece (a seamless product loop or a logo sting) rendered to MP4, with an optional measured sound pass. `skills/product-sting/SKILL.md` is the operational authority for how the skill runs; the README owns installation and public claims. This file is for people and agents changing the repository.

## Map

- `skills/product-sting/`: the installable skill. `gh skill install` copies only this folder, so everything the skill needs at run time lives here.
  - `SKILL.md`: the workflow, steps 0 to 9.
  - `engine/motion.js`: springs and helpers, loaded by the page as browser globals. `engine/render.mjs`: the renderer (Playwright screenshots into ffmpeg). `engine/package.json`: its one dependency.
  - `templates/`: the starter page (`index.html`), the spec template (`SPEC.md`) and a CC0 cue list for the starter page (`cues.json`).
  - `sound/`: `soundpass.py` (the measured sound pass), `eleven_family.py` (optional ElevenLabs generator), `requirements.txt` (pinned), `README.md`, and `lib/` with the two CC0 libraries, each with its manifest and licence file.
  - `reference/LESSONS.md`: the review checklist. Each rule came from a broken frame or mix.
  - `LICENSE` and `THIRD_PARTY_NOTICES.md`: copies of the root files, so installed copies carry them. Keep each pair identical.
- `tests/`: `motion.test.mjs` and `render.test.mjs` (Node's test runner; no browser needed), and `test_*.py` for the sound tools and libraries (standard `unittest`, plus numpy).
- `.github/`: the CI workflow (`workflows/checks.yml`), `tripwire.sh`, `check-shell-blocks.sh` and `dependabot.yml`.

## Rules for changes

- The skill never writes inside its own folder. Engines, environments, downloads, temporary files and pieces go in the user's project under `motion/`. Keep it that way when you change a command.
- Bundled sounds are CC0 only, each listed in its library's manifest and licence file. Never add music. `tests/test_sound_libraries.py` and the tripwire check this.
- When you change a command or flag in `SKILL.md`, change the README, `sound/README.md` and the comments at the top of `render.mjs` or `soundpass.py` to match.
- Shell code blocks in Markdown carry no comments, so they paste cleanly into zsh. Explain them in the text around the block.
- Render test pieces in a folder outside the repository. `.gitignore` keeps `motion/`, `.tmp/`, `node_modules/` and `.venv/` out, but a stray piece still costs a review.
- For any change a user would notice, add a line to `CHANGELOG.md` under an `## Unreleased` heading at the top (add the heading if it is not there yet).

## Checks

Run these from the repository root before saying a change is done. CI runs the same checks in `.github/workflows/checks.yml` on every push to `main`, on pull requests and weekly.

```sh
pipx run --spec ruff==0.17.1 ruff check --no-cache .
pipx run --spec ruff==0.17.1 ruff format --no-cache --check .
node --test tests/*.test.mjs
cmp LICENSE skills/product-sting/LICENSE
cmp THIRD_PARTY_NOTICES.md skills/product-sting/THIRD_PARTY_NOTICES.md
bash .github/check-shell-blocks.sh
bash .github/tripwire.sh origin/main
gitleaks git --redact --no-banner .
gitleaks dir --redact --no-banner .
lychee --offline --no-progress .
```

In order: Python lint and format; the engine tests; the two copies in the skill folder; shell blocks in the docs (no comments, they must parse); personal paths, junk files, sounds outside the libraries, rendered pieces and checks silenced since `main`; secrets in history and in the working files (gitleaks v8); local links.

The sound tests need Python 3.12 or later with the pinned numpy, in an environment outside the repository. Choose a fresh path if that example already exists:

```sh
python3 -m venv /tmp/product-sting-tests
/tmp/product-sting-tests/bin/pip install "$(grep -E '^numpy==' skills/product-sting/sound/requirements.txt)"
PYTHONDONTWRITEBYTECODE=1 /tmp/product-sting-tests/bin/python -m unittest discover -s tests -v
```

The tripwire takes the commit your change started from (`origin/main` in a clone of the GitHub repository); it fails if that commit is missing rather than reporting clean. For the Agent Skills format, use the official validator in a disposable environment:

```sh
python3 -m venv /tmp/product-sting-validator
/tmp/product-sting-validator/bin/pip install 'skills-ref @ git+https://github.com/agentskills/agentskills.git@69ef37e9424c0a7ea9dd2293b559e43ec8176379#subdirectory=skills-ref'
/tmp/product-sting-validator/bin/skills-ref validate "$PWD/skills/product-sting"
```

CI also renders the starter page with the preflight's own commands (SKILL.md Step 0) and audits the engine's and the sound step's dependencies (`npm audit`, `pip-audit`). Those steps download Playwright's browser and the sound packages, so when you change the engine, the starter page or `requirements.txt`, run them the way the workflow does, in a folder outside the repository. A change to how the skill behaves deserves a real run too: install your branch into an empty folder with `gh skill install --from-local . product-sting --dir <empty folder>` and make the starter piece from that copy.

Pip, Node's test runner, gitleaks, lychee and network access are development tools, not requirements for using the installed skill.

## Working rules

1. **A bug fix ships with a committed test** that fails on the old version and passes on the new one. A one-off check in a temporary folder does not count. Here that is usually a case in `tests/`.
2. Run every check listed above before saying a change is done, and quote the output.
3. Don't silence a check to get green, for example with `noqa`, a skipped test or a looser pattern. The tripwire fails the build on common silencing markers unless the line says `tripwire-allow:` followed by a reason.
4. Stop any server you started. Leave no stray files (caches, `__pycache__`, renders, `motion/`, `.tmp/`, `node_modules/`, `.venv/`, `.DS_Store`) in the repository folder.
5. For a non-trivial change, a different agent writes an independent scenario test before the change is accepted: for example, a fresh agent installs the skill from your branch into an empty folder and makes a short loop for a fictional brand.
