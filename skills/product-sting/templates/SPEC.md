# <Product>: <piece name>

<!-- Fill every section before writing any animation code. The state list is the contract: the user approves it, then you build it. -->

## Brief
- **Mode:** loop (8-14s, last frame = first frame) | sting (2-5s, ends on a held logo or line)
- **Format:** 16:9 1920x1080 | 1:1 1080x1080 | 4:5 1080x1350 | 9:16 1080x1920 (render as 375x667 at 2.88x). Several formats = one page with a camera table each, chosen by `?ar=`
- **Length:** <seconds> at 30 fps
- **Tempo:** <BPM> (120 BPM = 0.5s beats). Every state change lands on a beat.
- **Where it will be seen:** <README / landing hero / phone feed / pitch deck / app store>, at about <seen width> px wide. Important text at least <px> in the frame, secondary about three quarters of that (SKILL.md Step 3).
- **Camera:** moves (a push-in toward the action) | fixed (zoom 1, `moves: []`, when an asset must not be shown above its captured size), because <reason>
- **One-line story:** <what the viewer should understand by the end, in one sentence>

## Reference
- **Brand source:** <path to DESIGN.md / tokens file / URL / screenshots>
- **Tokens used:** <background, surface, ink, accent: hex values, and what the accent is reserved for>
- **Fonts:** <family names + local woff2 files in fonts/>
- **Real assets:** <logo SVG (or the wordmark set from the brand font), product screenshots, icons, and any crop cut from a screenshot with its captured size. Never invented.>
- **Missing inputs:** <what the guide references that the user did not supply, and what was agreed, or "none">
- **Motion bans from the brand guide, and what each means in motion:** <rule: its motion meaning (for example "no opacity tricks": colours enter and leave by size or position, never by a fade)>, or "none stated". Motion blur in the final render: kept | off, at the user's word.

## Shape
<!-- One shape, never cut: a single element morphs from state to state instead of cutting between screens.
     Name the shape and every form it takes. -->
One <element>, never cut. It becomes: <form A> -> <form B> -> <form C> -> back to <form A>.

## Reads
<!-- In order, what the viewer must understand. Give each read time to be found and understood. Never overlap two important reads. -->
1. <read> (needs ~<s>s)
2. <read>
3. <read>

Too small to read at the seen size: <element: shown as a whole object after its key content has been read large>, or "none".

## State list
| t (s) | Beat | The shape becomes / what happens | Spring |
|---|---|---|---|
| 0.0 | 0 | <starting state> | - |
| | | | |
| <DUR> | <n> | Identical to frame 0 (loop) / held end card (sting) | - |

## Springs
- **Preset:** <snappy / def / heavy / swiss / punchy / calm, or custom f + zeta>, chosen because <brand reason>
- UI controls: <preset>. Cards and panels: <preset>. Type and logo: <preset> (no overshoot on type).

## Formats (if more than one)
| Format | `?ar=` | Viewport (`--w --h --scale`) | Opening = closing framing [x, y, zoom] | Camera moves |
|---|---|---|---|---|
| 16:9 | wide | 1920 1080 1 | <960, 540, 1.0> | <t, x, y, zoom; ...> |
| 1:1 | square | 1080 1080 1 | <...> | <pushes in less than wide> |

HUD elements (logo mark, labels): <list>, kept outside the camera stage.

## Sound (optional)
- **Families (three or four, one brand):** <family: library role or category, e.g. press = coldframe click-firm, whoosh = coldframe whoosh, tick = barty-bart tick, reward = coldframe confirm>
- **The one reward sound:** <family>, the loudest cue, at <t>
- **Cues:** <t>: <family>, <dB>, <what it marks> (the pass places each ~0.03s before its visual; whooshes peak on the fastest frame)
- **Music bed:** <none / the user's track: file, source, licence>. Wanted for anything over about 10s.
- **Loudness:** about -16 LUFS, true peak at or below -2 dBTP, measured on the exported MP4
- **Headphone checks for the user:** <about five timestamps and what to listen for>

## Deliverables
- `out/<name>.mp4` (final, silent: the web and README version; 4 subframes, or 8 when a move exceeds about 60 px per frame)
- If sound: `out/sound/<name>-sound-<tag>.mp4` (seamless loop) and `out/sound/<name>-sound-<tag>-post.mp4` (eased out for single play), plus `out/sound/SOUND.md`
- `check/beats.png` contact sheet, `check/final.png`
- Other formats: <list>, each from the same page with its own camera table, never cropped
