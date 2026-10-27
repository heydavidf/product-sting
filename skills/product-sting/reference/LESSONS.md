# Lessons from real pieces

Each of these was learned by shipping a broken frame (or a broken mix) first, or from a fresh agent's first run of this skill. Check the relevant ones at every review pass.

## Before code
1. **Read the brand guide for motion bans before pitching an idea.** Brands ban specific motifs (ornamental motion, bounce, gradients, glows). A clever idea that breaks a ban is a wasted round.
2. **No reference, no code.** A real frame, clip, DESIGN.md or token file, plus real assets. Without one the piece drifts toward generic "AI motion" that looks like everyone else's.
3. **Mark example data on screen** ("Example data") when the product shows names, numbers or people that are not real.
4. **Brand guardrails carry into motion.** If the accent colour is reserved for one thing (a primary action, a human decision), it stays reserved in the animation.

## Timing
5. **Fast actions, slow meanings.** Motion can be quick if it is anticipated; the meaning that follows needs a hold. Timing is what models get wrong most often: when in doubt, hold longer.
6. **Never overlap two important reads.** If two things need reading, stagger them.
7. **Text at the size it will be seen.** About 14 px as seen for anything that must be read (SKILL.md Step 3 turns that into frame pixels per destination), checked on a sheet at the seen width, not on the 640 px contact sheet. UI that is legible in the real app is often unreadable in a feed; add a camera move (scale toward the action) rather than shrinking the story, unless an asset must not be enlarged: then fix the camera at zoom 1 and size the layout for reading.
8. **Pace for carousels and slide sequences is ~4s per slide.** Faster reads as a flicker.

## Motion
9. **Springs, not one easing curve.** Tiny overshoot on UI, none on type and logos. Tune the preset to the brand: hard modernist brands want critically damped (swiss), energetic ones want visible overshoot (punchy), soothing ones want slow and damped (calm).
10. **A value that changes target several times = start value + one spring per change** (`track()`). Restarting a spring from zero on each change makes values jump.
11. **Text inside a morphing shape needs its own enter and exit timing,** and must leave before its container shrinks or fades. Otherwise it clips or overlaps the next state's text.
12. **Same-colour wipes are invisible.** A wipe between two surfaces of the same colour needs a coloured leading edge.
13. **Colour transitions: blend surfaces in OKLab, but flip text colours in a single frame.** Blending text with its background (for example a day-to-night shift) collapses contrast mid-transition.
14. **Avoid "twinning"**: code tends to move paired things identically. Offset them in time (overlapping action) so it feels alive.

## Rendering
15. **Every frame is a pure function of time.** No CSS transitions, `setTimeout`, counters or `Math.random()`. Seeded noise only. Frames must render in any order.
16. **Motion blur = subframes over half a frame (a 180-degree shutter): 4 by default, 8 for fast moves.** A full-frame shutter smears text. Above about 60 px per frame (a spring move of D px at frequency f peaks near D × f ÷ 12), 4 subframes leave 3 to 4 separate copies and a paused caption looks doubled: render with `--sub=8`. Above about 120 px per frame even 8 steps faintly; slow the move. Check it on a fast-move frame pulled from the MP4; page stills have no blur.
17. **Even output dimensions.** An odd height (for example 667 x 2.88 = 1921, or 375x667 at 1x) can hang the encoder; the renderer forces even sizes.
18. **Fonts must be local files, and fonts and images must be loaded before `__ready`:** `document.fonts.load()` for every weight used, not only those in the first frame, and `decode()` for every image. A CDN font, or a weight first used mid-piece, can arrive late and render in a fallback face.
19. **Render the hardest 2-4 seconds first** as stills and strips before a full render (`--range` renders one part as video). Full renders are slow; stills are cheap.

## Loops
20. **The last frame must equal the first.** Check it explicitly: render stills at `0` and `DUR - 1/fps` side by side, and diff the full-size pair with ffmpeg's `psnr` (`inf`; above about 60 dB is a tiny difference, so confirm it by eye). A loop that ends one state early (a ticked box, a filled bar) jumps on repeat. Once the page pair passes, a lower figure on the MP4's own first and last frames is compression, not a seam; never judge the seam from the MP4 figure alone.
21. **Every spring must settle before the loop point.** Leave at least ~1s after the last target change for heavy springs.

## Sound
22. **Real recorded sounds, not synthesis.** A score of synthesised blips sounds thin and generic; use recorded CC0 effects and a real music track. Synthesis only for a deliberate retro or game feel.
23. **Three or four sound families from one brand, not dozens.** Typically clicks, whooshes, one reward and one impact. Write the room into a generated family's brief once ("close microphone, dry, single event") and vary only the object.
24. **One reward sound, and it is the loudest cue.** A firm click at the same level as the confirmation chime steals the moment; drop the click below it.
25. **A music bed under anything over about 10s,** sitting about 12 dB under the effects. Sparse effects over silence sound unfinished. The user supplies the track; snap state changes to its beats.
26. **Cues land ~0.03s before the visual, and whooshes peak on the fastest frame.** Late sound reads as broken; slightly early reads as in sync. Start a whoosh early (`peak_align`) so its loudest moment meets the move.
27. **Libraries differ in level: trim before mixing.** Barty-Bart files peak near 0 dBFS, Coldframe's at about -8. Untrimmed, the "quiet" blip becomes the loudest thing in the piece; the sound pass trims Barty-Bart files to match.
28. **Sustained textures (rain, footsteps, breeze) use `until` with fades, not pitch variation.** Rate variation on a long texture bends its pitch audibly; tile it to the end time and fade in and out instead.
29. **Measure loudness on the exported MP4, not the intermediate WAV.** About -16 LUFS, true peak at or below -2 dBTP. Sparse UI sound over a soft bed may fall short: cap the limiting and report the shortfall rather than crush the mix.
30. **Ship two audio cuts of any loop.** Seamless for looping players, and an eased-out `-post` cut (about 1.4s audio ease) for single play on phones and social. A loop played once ends abruptly.
31. **You cannot hear.** Measure everything, look at the per-cue waveform checks, and hand the user a short list of timestamps (about five) to check on headphones. Never claim the mix sounds good.
32. **Music never lives in the skill.** The user supplies the track; record its source and licence in the piece's SOUND.md, and do not commit a track whose licence forbids redistribution.

## Formats
33. **Design each format from one layout. Never crop.** A 16:9 piece cropped to 9:16 loses its story; re-position elements for each format instead.
34. **A square (or any new aspect ratio) needs its own camera table, not a crop.** Fit the content's width on wide shots, push in less (the frame is already tight), and make the opening framing equal the closing one so the loop still closes.
35. **Keep HUD elements outside the camera stage.** Labels, logo marks and indicators inside it zoom and drift with every camera move.
36. **A page-level query variable must not clash with page helper names.** A page that already used `q` as a helper clashed with a format query also named `q`; give the query its own name (`QUERY`, `AR`).
37. **Parse render flags on the first `=` only.** `--q=ar=square` split at every `=` loses its value; the renderer keeps everything after the first `=`.

## Brand into motion
38. **Translate static brand rules into motion rules, and get the translation approved in the spec.** "No opacity tricks" means colour enters by size or position, never by a fade; "no shadows" removes the starter's shadow; "no blur" means interface blur and glass, not the renderer's motion blur, which stays unless the user says otherwise.
39. **A logo can be a typeset word.** With no logo file, set it from the brand font at the guide's weight and letter-spacing, and confirm with the user.
40. **Assets cut from screenshots are never shown above their captured size,** camera zoom included. Crop and sample them with ffmpeg, check the sampling against one known colour, and keep working crops in `check/ref/`.
41. **A true-to-product element that cannot be legible at the seen size is shown as an object,** after its key content has been read large. Never enlarge it or fake its small print.

## Build and review
42. **A target that moves while it is chased needs `follow()`, not `track()`.** `track()` aims at fixed numbers, so a shape heading for a slot on a card that is still rising lands ahead of the card. `follow()` reads each target at time t. Jump (`"step"`) only while the element is invisible.
43. **Shapes that fly and grow: travel first, grow after** (a lag of about 0.12s), and launch the farthest first. Grown at once, they pile up mid-flight.
44. **Score the strips as well as the beat stills.** In the first blind run, all three of round 1's worst problems were in strips: pile-ups, crossings and clipping happen between the held states.
45. **Check the encode on frames pulled from the MP4,** draft and final. Fonts, colours, timing and motion blur as the viewer gets them exist only there; page stills show the page, not the video.
