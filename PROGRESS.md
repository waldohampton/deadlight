# DEADLIGHT — progress and handoff

Last session: 2026-11-10. Branch `master`, commit `75d4d8c`, working tree clean.

## What this is

A filmic night-industrial parkour course that runs in a browser and can be wrapped for
Android with Capacitor. Deadlight no longer has a chaser. That premise is shelved, not
deleted: `play.html` still has it if it is ever wanted back.

The loop that works: build the set in Blender, bake irradiance into lightmaps with Cycles,
export a GLB with the lightmaps in the `uv2` channel, play it back in Three.js with a live
torch and a film pass on top.

## Which file is which

| File | Role |
| --- | --- |
| `course.html` | **the game.** Third-person parkour, 8 pads, jumps, checkpoints, timer, film pass |
| `play.html` | shelved first-person chase slice on the same yard |
| `night.html` | night yard viewer, lightmap toggle, no gameplay |
| `room.html` | cloister bake-test viewer (`?d=bake3` for the planted room) |
| `baked.html` | first lightmap proof of concept |
| `index.html` | the original v1.0.0 maze chase. Untouched since, still the Pages root |
| `look*.html` | look-dev experiments: textures, scanned plants, DOF test |

`course.html` is a single file, everything inline except `three.min.js`, `GLTFLoader.js`
and `models/Soldier.glb`.

## Running it

```bash
cd ~/repos/deadlight && python3 -m http.server 8123     # usually already running
```

- local: http://localhost:8123/course.html
- live: https://waldohampton.github.io/deadlight/course.html
- repo: https://github.com/waldohampton/deadlight

Pages is served from `master` root and takes 40-60 seconds to pick up a push. Poll
`curl -o /dev/null -w "%{http_code}"` rather than assuming a 404 means a broken build.

## Controls

WASD or arrows move, camera-relative. Space jumps. Shift runs. R restarts. V toggles
first/third person. F toggles the film pass. On touch: left stick, JUMP button, drag the
right side to look.

## Rebuilding the art

Bakes are **not** committed. They are reproducible, and the repo would be 200MB otherwise.

```bash
cd ~/repos/deadlight
LD_LIBRARY_PATH=~/opt/xlibs/usr/lib/x86_64-linux-gnu \
  ~/opt/blender-4.2.9-linux-x64/blender -b -noaudio -P bake_night.py
```

Driven by `BAKE_RES` / `BAKE_SAMPLES` / `BAKE_OUT`. Look-dev at `384 24` is about 6 minutes
and is where every look decision should be made. The night yard lives in `bakenight/`
(`night.glb` 20MB plus per-object `*_lm.png`). The planted cloister is `bake3/` at 65MB.

The full recipe — bake settings, the two black-frame bugs, the film pass shaders, the rigged
character setup, the spring-arm camera — is written up as a skill reference:

`~/.hermes/skills/software-development/webgl-game-build/references/baked-gi-and-film-pass.md`

## Where it stands

Working and verified: baked GI reads on every mesh, the lightmap toggle changes 44% of the
night yard's pixels, third-person camera with collision pull-in, rigged character with
speed-blended animation clips, jump/land/checkpoint/fall-reset/finish all exercised by real
key events against the live build, film pass toggle measured on and off.

## Open items

1. **Phone payload.** `night.glb` is 20MB and takes about 17 seconds to load on a phone.
   Needs 1k textures and meshopt or Draco before this is shippable as an APK.
2. **The set is the weak link.** Flat painted metal and 384px lightmaps read as a game in
   close up. Next real quality jump is scanned industrial assets, not more character work.
3. **Camera clipping.** Pull-in is implemented and seen working on one pad; it has not been
   walked into every corner of the course.
4. **Course feel is untuned by a human.** Gaps are 1.3m, run 4.0 m/s, jump 6.2, pads 1.8-2.0m
   long. Numbers are sane on paper but the test rig renders at 8fps, which changes timing.
5. **No Android wrapper yet.** Capacitor is the plan, nothing scaffolded.
6. **The character is a game soldier**, CC0 from the three.js examples. A scanned human with
   skin and cloth needs paid assets and will not run here anyway.
7. **`index.html` is still the old maze game** at the Pages root, so the site root and
   `course.html` disagree about what this project is. Point the root at the course when the
   old build is retired.

## Gotchas that cost time

- Blender needs `libSM`/`libICE`; installed without sudo into `~/opt/xlibs` and passed via
  `LD_LIBRARY_PATH`. Every Blender command needs that prefix.
- `uv_layers.active_render = layer` does nothing. Assign `layer.active_render = True`.
- A ground plane with reversed winding receives no light and renders black while everything
  else looks fine. So does a PMREM env capture that goes to `inf` and turns ACES into NaN.
- The glTF forward axis is not to be trusted. Flip the holder group and check on screen.
- Patching inside a shader string array in `course.html`: keep the surrounding quotes and
  commas, patch whole quoted lines, or the script dies with a syntax error and `COURSE` never
  exists.
- `.git` is 132MB from early bake commits. Bakes are ignored now but the history still has
  them.
