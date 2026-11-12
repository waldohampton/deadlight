# DEADLIGHT — progress and handoff

Last code change: `course.html`, traversal rebuild. Branch `master`, pushed.

## This session, 2026-11-11 (third session): the car

A drivable car and a chase camera, in the same yard. It is a sandbox: the run
is still on foot, the car does not trigger markers or the finish.

1. `CAR` is a 1979 Calder Arrow 305 built out of boxes: wedge nose, cabin, four
   wheels, a dish gimballed through the roof. Headlight spot, tail glow, amber
   side sills in the same family as the course edges.
2. Physics is a bicycle model: `vF`/`vR` decompose the velocity, engine and
   brake act along forward, lateral grip bleeds `vR` (1.5 when the handbrake is
   down, so it drifts), and the heading turns at `vF / wheelbase * tan(steer)`.
3. Collision is swept and axis-separated: move x, ask `carHitAt`, revert if it
   would penetrate, then the same for z. Resolving penetration instead made a
   thin wall (the rail) flip sides every frame and the car teleported back and
   forth.
4. Ground is a chassis query plus four wheel samples. The chassis height comes
   from one query under the middle; the wheels are sampled from *that* height
   for pitch and roll. Sampling the wheels against the car's own y is what made
   a 32 degree ramp vanish: the body lagged, the reach fell short, and the car
   sank into the slope.
5. Two lip rules, both needed: a box below the wheels is ignored (`b.y1 <=
   base`), and a box up to 0.85 above is a kerb the wheels ride up (the curb,
   the deck's edge). Anything taller blocks, which keeps the rail, the pipes
   and the tank solid.
6. `E` near the car gets in, `E` gets out. In the car the avatar and the torch
   are hidden, the HUD switches to KM/H, and SHIFT+R or R puts you back on foot.
7. Chase camera: behind the heading, swings itself back after 0.7 s without a
   mouse move, arm pays out and the lens opens with speed, and it raycasts so
   the yard does not get between you and the car.
8. The body is `models/arrow_tripo.glb`: the Tripo image-to-3D export of the
   mood-board still, run through `tripo_to_game.py` (decimate 1,483,540 to
   48,000 tris, rotate the length from +X to +Y so glTF lands the nose at -Z,
   scale to 4.30 m, seat it on z 0, textures 2048 to 1024). 2.6 MB. Load order
   is tripo, then the hand-built `models/arrow_game.glb`, then the boxes in
   `course.html`, so a missing file never breaks the car.
   The Tripo mesh is one fused surface, so there are no wheel nodes and the
   wheels do not spin. Everything else about it is better than the loft.
9. `build_arrow.py` still builds the fallback body: a lofted superellipse (26
   stations, Catmull-Rom, 20 points per ring), a glass greenhouse, and a real
   paraboloid dish. Nose +Y in Blender so it exports to -Z. Worth keeping, it
   is the thing to fall back on and it is 2,116 tris.
10. Both models get relit on load because an exported black is invisible at
    night: texture bodies get the material colour lifted to `0x9aa0aa`, and
    the car carries a low cool fill plus a shader blob underneath so it does
    not read as hovering.

Transform gotcha, cost me a pass: `bpy.ops.object.transform_apply` operates on
the selection and can silently do nothing, which exported the car sideways at
the wrong length. Bake transforms into the mesh with `ob.data.transform(M)`
and print the resulting bounds, so the numbers are checkable.

## Sunset, not night

The yard's lightmaps are baked at night, so the bake is now treated as ambient
occlusion (`lightMapIntensity` 0.85, was 1.7) and the colour comes from three
things added in `course.html`: a gradient sky dome (horizon `0xc26a36`, mid
`0x7d4453`, zenith `0x172440`, plus a sun disc), a warm `DirectionalLight`
at 0.88 from `SUN_DIR`, and a warm-shifted grade in the post pass. Hemisphere
went from cool 0.34 to warm 0.42, fog from `0x0b1219` at 0.014 to `0x6e4638`
at 0.0085, exposure 1.34 to 1.04.

Measured on the same camera, mean of the frame: night was RGB 67/71/73 (cool,
30% of pixels near black), sunset is 116/101/82 with the ground band at 103
luma against 74. Warmth went from minus 6 to plus 34.

Known mismatch: the baked shadows are night shadows, so they do not agree with
the new sun direction. That stopped mattering when the bake came out entirely
(see below).

## Photo surfaces, and the bake gone

The yard had 42 meshes, 7 materials and **no albedo texture at all**. Every
surface was a flat colour with a baked lightmap on it, which is why it read as
a render: there was no photograph anywhere in the scene.

The bake is gone. `bakenight/<mesh>_lm.png` is no longer loaded, the emissive
bake is stripped from every material except `lamp` and `beacon`, and the yard
now casts shadows (`castShadow` true) so the sun makes the long shadows the
concept art has. The 4.7 MB of lightmap PNGs are still on disk and still in
git, just unused.

Three CC0 photo sets from Poly Haven, downloaded by `fetch_tex.py` at 1 k and
packed to 1024 px JPEG: asphalt, brushed concrete, rusty metal, colour, normal
and roughness each, **1.8 MB for all nine files**.

- the floor is one 70 m plane unwrapped 0..1, so it tiles at 2 m per repeat and
  keeps a real normal map
- everything else uses **world space triplanar** injected through
  `onBeforeCompile`, because the yard's other UVs are useless: a 26 m concrete
  cube has a u range of 0.001 to 0.101. Triplanar means texel density is the
  same on a wall, a pipe and the floor without touching a single UV
- our own pads and ramps get the concrete scan too, otherwise they read as
  flat grey slabs next to the yard

Two things the bake had been doing for free, and had to be replaced:

1. **Contact shading.** Without it every wheel and foot floated. There is now a
   ten tap screen space occlusion term in the composite shader, using a 24-bit
   depth texture on the scene target, with the radius in real metres
   (`uProj` converts 52 cm of world to pixels at any field of view).
2. **A horizon.** The baked floor is 70 m square, so the world ended on a
   straight line. There is a 240 m ground disc under it and the fog colour now
   matches the sky horizon (`0xa8643e` at 0.0105), so the two meet in haze
   instead of at an edge.

Marker rings were unlit `0xffb038`, which sits above the bloom threshold and
smeared across the frame. They are now low emissive paint: `0xd08a28` at 0.55.
The two neon green pad glows went the same way.

Verified with the sim driver: the ramp run reaches the deck at 4.26 on all five
starting points and carries on at 58 km/h; the rail stops the car at z 0.20;
the pipes stop it at z -4.56; a lateral run reaches 60.7 km/h and a 30 frame
turn swings the heading 1.95 rad without losing speed. Pose on the slope was
checked in a screenshot: nose up, wheels on the ramp, no clipping.

## This session, 2026-11-11 (second session): the yard became a place

The course was eight floating pads over a yard you could not touch, the floor
killed you, and the camera was bolted behind the body. It is now a route built
onto the yard's own geometry, with movement that keeps momentum.

What `course.html` does now:

1. **The line.** Apron on the floor, vault the yellow rail, cross the yard on
   the wet ground, climb the pipe rack (vault pipe_a 1.69, skim pipe_b, vault
   the catwalk 2.26), run the 17 m catwalk west, step onto the tank landing,
   run one 7.8 m flight up the tank's west face to 6.99, and finish on the tank
   cap under the green lamp. Both ramps are walkable slope, not steps.
2. **Momentum.** Speed climbs toward walk 3.0 / run 5.0, and the velocity you
   already have is steered rather than replaced. Nothing is scrubbed in the
   air, so a vault or a drop carries into the next beat. Landing keeps 94%.
3. **Steps.** Anything within `TUNE.stepUp` (0.42 m) is a step, not a wall:
   the 0.32 curb is now run over without a pause.
4. **Vaults.** Running into anything up to `TUNE.vaultMax` (1.75 m) at over
   1.2 m/s starts a 0.2-0.34 s mantle that keeps 92% of the speed. Thin
   obstacles tagged `'over'` (the rail) are crossed; everything else is landed
   on top of.
5. **Ramps.** New `ramp(name, x0,x1, z0,z1, y0,y1)` builds an axis-aligned
   sloped slab and registers the analytic plane, so the floor between 0 and
   4.26 m is continuous. The mesh top and the collision plane are the same
   line by construction.
6. **Camera.** Shoulder 0.45 to 0.22, arm pays out 0.75 m and the lens opens
   7 degrees at speed, and it swings back behind the run on its own after
   0.9 s without a mouse move (never when you are running at the camera).
7. **The floor is ground.** Touching the yard no longer resets anything.
   Falling costs you the climb, nothing else. R returns to the last marker,
   SHIFT+R starts the run over.
8. The gantry is still there as a side route: the long ramp off the back of
   the rail, the deck, and the lit shelf that drops you back at catwalk height.

Verified by an autopilot driving the real input path with the sim frozen
(`COURSE.press` + `COURSE.sim`): START to finish in 10.13 s, every marker hit,
y rising 2.26 to 6.99 on the tank flight with `grounded` true the whole way,
and `finish()` firing on the cap. Real key events and the live loop were also
checked separately: 5.0 m/s, fov 64 to 67.7, camDist 3.1 to 3.55.

## What this is

A filmic night-industrial traversal that runs in a browser and can be wrapped
for Android with Capacitor. Deadlight no longer has a chaser. That premise is
shelved, not deleted: `play.html` still has it if it is ever wanted back.

The loop that works: build the set in Blender, bake irradiance into lightmaps
with Cycles, export a GLB with the lightmaps in the `uv2` channel, play it back
in Three.js with a live torch and a film pass on top.

## Which file is which

| File | Role |
| --- | --- |
| `course.html` | **the game.** Third-person traversal, markers, timer, film pass |
| `play.html` | shelved first-person chase slice on the same yard |
| `night.html` | night yard viewer, lightmap toggle, no gameplay |
| `room.html` | cloister bake-test viewer (`?d=bake3` for the planted room) |
| `baked.html` | first lightmap proof of concept |
| `index.html` | the original v1.0.0 maze chase. Untouched since, still the Pages root |
| `look*.html` | look-dev experiments: textures, scanned plants, DOF test |

`course.html` is a single file, everything inline except `three.min.js`,
`GLTFLoader.js` and `models/waldo_game.glb`.

## Running it

```bash
cd ~/repos/deadlight && python3 -m http.server 8123     # usually already running
```

- local: http://localhost:8123/course.html
- live: https://waldohampton.github.io/deadlight/course.html
- repo: https://github.com/waldohampton/deadlight

Pages is served from `master` root and takes 40-60 seconds to pick up a push.
Poll `curl -o /dev/null -w "%{http_code}"` rather than assuming a 404 means a
broken build.

## Controls

WASD or arrows move, camera-relative. Space or left mouse click jumps. Shift
runs. R back to the last marker, Shift+R restarts. V first/third person. F film
pass. On touch: left stick, JUMP button, drag the right side to look.

The car: `E` near it to get in, `E` again to get out. W/S throttle and brake,
A/D steer, Space handbrake (it drifts), mouse to look around while it swings
back. Top end is 63 km/h, and it will take the gantry ramp and launch off the
deck.

## The line, in numbers

Everything below is measured off the loaded `night.glb`, so the feet land on
the real surfaces instead of near them.

| Beat | Surface | Height |
| --- | --- | --- |
| start | `apron` box on the floor | 0.10 |
| rail | baked curb (step) + 3-bar rail (vault) | 0.32 / 1.28 |
| pipes | baked pipe_a / pipe_b / pipe_c, now solid | 1.69 / 0.97 / 2.26 |
| catwalk | new deck over the pipe rack, 16.8 m long, 1.1 m wide | 2.26 |
| tank landing | `tw0`, 1.8 x 1.3 | 2.26 |
| tank flight | `tw_up`, 7.8 m run, 31 degrees | 2.26 to 6.99 |
| top landing | `tw_top`, 2.9 x 2.1 | 6.99 |
| finish | tank cap, baked, added as a solid | 6.99 |
| side route | `ramp_up` to the gantry deck, `shelf` back down | 0 to 4.26 |
| second way in | `tank_in`, ground to the tank landing | 0.06 to 2.26 |

Markers: START, YARD, PIPE, TANK. `setCP` only moves forward, so a shortcut
cannot un-set a marker you already touched.

## Tuning

All of it is in the `TUNE` block at the top of the player section, and it is
live-editable from the console (`COURSE.TUNE.run = 5.4`). The numbers that
decide feel: `accelG` 14 and `steerG` 7.5 give a 0.36 s run-up and a 0.21 s
90 degree turn at speed. Raising `steerG` makes it twitchier, lowering it makes
wide sweepers. `landKeep` 0.94 is what stops landings from feeling like a brake.

## Test hooks

`window.COURSE` carries `state()`, `place(x,y,z)`, `look(yaw,pitch)`,
`respawn(i)`, `sim(n,dt)` (freezes the render loop and steps physics by hand),
`resume()`, `press(code,down)`, `jump()`, `dbg()`, `TUNE`. The autopilot that
verified the route used `press` plus `sim` inside one `Runtime.evaluate`, which
is the only way to test this deterministically: the headless rig renders at
5-9 fps and the tab throttles rAF to zero when it is not visible (that reads
exactly like "the game does not respond to input", so check
`document.visibilityState` and call `Page.bringToFront` before believing it).

## Player character

There is one: Waldo. `CHARS` in `course.html` holds a single entry,
`START_CHAR = 'waldo'`, and there is no switching UI or key. The registry shape
is kept (height `h`, facing flip `face`, optional stride cadence `cad` as the
m/s the clip was authored at, clip-name map) so another character is a
one-entry addition. Clip lookup is case-insensitive, so `Idle`/`Walk`/`Run`
bind as-is.

| id | file | notes |
| --- | --- | --- |
| `waldo` | `models/waldo_game.glb` | own rigged character, `cad:{walk:1.45,run:3.25}` |

`models/Soldier.glb`, `models/Xbot.glb` and `models/RobotExpressive.glb` are
still on disk from the experimenting phase. Nothing references them, so they
cost nothing at runtime.

`waldo_game.glb` is the game-ready build of the scanned statue: 4,180 tris, 23
joints, Idle 4.0s / Walk 1.0s / Run 0.733s, 1.75 m, feet at y=0, authored
facing +Z, so it needs `face:Math.PI` here. Source and pipeline live in
`~/Downloads/waldo-character/`.

Without `cad`, the stride scaler falls back to the soldier numbers (2.6 walk /
4.4 run), which is wrong for a clip authored at a different speed. Waldo's walk
clip is clamped at 1.6x, so his feet skate a little at full walk speed; his run
matches.

Waldo's idle was reposed once already: the fitted rig rests in a narrow A-pose
with the arms 25 degrees out, so the Idle clip builds a square stance instead.
Measured in engine, stance 0.387 m and hand spread 0.470 m, up from
0.190 / 0.810. The pelvis is also tucked 3.5 degrees with the spine column
straightened, which cut the lumbar arch from 8.3 mm of anterior bow to 1.5 mm.
Walk and run still use the narrow base.

To change how he stands or moves: edit the IDLE / walk_pose / run_pose blocks in
`~/Downloads/waldo-character/tools/step_g_cycles.py` for a full rebuild, or run
`tools/idle_repose.py` or `tools/clips_repose.py`, which rebuild only those
clips in `waldo_final.blend` and re-export the GLB. `tools/probe_idle_axes.py`
prints bone world positions per rotation axis, which is how the signs were
settled instead of by guessing.

Heads up on caching: the browser will happily render a stale `waldo_game.glb`
after you replace the file. Bone positions in the console (`COURSE.dbg()`, walk
the scene for `l_foot`/`l_hand`) tell you which build is actually loaded, and
they only read true after the game has started and the mixer has run a frame.
The GLB has landed at the same byte size across rebuilds, so compare the first
keyframe quaternion of a `l_forearm` track in the `Walk` animation instead of
trusting file size.

## Gait

The walk and run arm swing was authored backwards in the first pass: arms swung
with the legs on the same side (foot-versus-hand correlation +0.84 walk, +0.92
run) and the elbows hyperextended, hands behind the elbows the whole cycle.
Flipping the sign of the upper-arm swing and the forearm terms fixed it, giving
-0.86 and -0.95, with the run's hands 0.13 to 0.23 m in front of the elbows.

Do not fix a clip that looks backwards by rotating the mesh or the rig. The
legs are the reference: in a correct clip the stance foot slides from in front
of the hips to behind them and the swing brings it forward again. Measure that
with `~/Downloads/waldo-character/tools/probe_gait.py` before changing any
orientation, because flipping the model also flips the legs.

## Rebuilding the art

Bakes are **not** committed. They are reproducible, and the repo would be
200MB otherwise.

```bash
cd ~/repos/deadlight
LD_LIBRARY_PATH=~/opt/xlibs/usr/lib/x86_64-linux-gnu \
  ~/opt/blender-4.2.9-linux-x64/blender -b -noaudio -P bake_night.py
```

Driven by `BAKE_RES` / `BAKE_SAMPLES` / `BAKE_OUT`. Look-dev at `384 24` is
about 6 minutes and is where every look decision should be made. The night yard
lives in `bakenight/` (`night.glb` 20MB plus per-object `*_lm.png`). The planted
cloister is `bake3/` at 65MB.

The full recipe, bake settings, the two black-frame bugs, the film pass
shaders, the rigged character setup, the spring-arm camera, is written up as a
skill reference:

`~/.hermes/skills/software-development/webgl-game-build/references/baked-gi-and-film-pass.md`

## Where it stands

Working and verified: baked GI reads on every mesh, the lightmap toggle changes
44% of the night yard's pixels, the traversal line runs start to finish, the
vault, step and ramp heights are exact as measured above, the film pass toggle
measured on and off, no console errors.

Not verified by a human: whether it is fun. The headless rig renders at 5-9 fps
and the dt clamp changes the timing, so feel is Waldo's call on his own machine.

## Open items

1. **Course feel is untuned by a human.** Run 5.0, walk 3.0, jump 6.4, ramp
   31 degrees, vault threshold 1.75. All sane on paper; the grader is a person
   holding W.
2. **Phone payload.** `night.glb` is 20MB and takes about 17 seconds to load on
   a phone. Needs 1k textures and meshopt or Draco before this is shippable as
   an APK.
3. **The set is the weak link.** Flat painted metal and 384px lightmaps read as
   a game in close up. Next real quality jump is scanned industrial assets, not
   more character work.
4. **The catwalk is unlit geometry.** It is new mesh in `STEP_MAT`, so it gets
   no lightmap. It reads from its edge strips and the torch. If it is too dark
   in practice, bake it into `bake_night.py` instead of adding lamps.
5. **Camera clipping.** Pull-in is implemented and seen working, it has not been
   walked into every corner of the yard.
6. **The car does not count for the run.** Markers and the finish are foot only.
   If driving should be a legal line, the finish test has to learn about `MODE`.
7. **Exiting beside a pipe can drop you inside it.** The car parks where it
   stops and the player is placed 1.9 m to its right, which can be inside a
   solid. Nudge on exit rather than teleport blind.
8. **Headlights run out before the car does.** At 60 km/h the beam reaches about
   15 m of readable ground, so the far yard is dark at speed. Either lean on it
   as night driving or raise the beam further.
9. **No Android wrapper yet.** Capacitor is the plan, nothing scaffolded.
10. **Waldo's limits.** Procedural weights on 178 welded patches, no finger or
    facial bones, one baked 2K texture. Deformation holds at the shoulders, hips,
    elbows and knees at 8 phases per clip. A proper retopo is what close-up hero
    work would need.
11. **Walk feet skate a little.** The walk clip was authored at 1.45 m/s and the
    game walks at 3.0, so the stride scaler clamps at 1.6x. The run matches.
12. **`index.html` is still the old maze game** at the Pages root, so the site
    root and `course.html` disagree about what this project is. Point the root
    at the course when the old build is retired.

## Gotchas that cost time

- Two Blender installs are in play. Yard bakes run on the Linux 4.2 build in
  `~/opt` (needs the `LD_LIBRARY_PATH` prefix). The character pipeline runs on
  the Windows 5.1 install:
  `"/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b -noaudio --python "C:\..."`.
  It works headless straight from WSL.
- Rotation signs are not guessable. `set_rot` applies world-axis rotations in
  rest space, so positive rx swings an arm backward but flexes a knee correctly.
  Measure with `probe_idle_axes.py` before authoring anything.
- The automated browser renders this scene at a few fps, so sampling bone
  positions on a timer yields two or three samples per second. Do pose and gait
  maths in Blender per frame instead; use the browser only to confirm which
  build is actually loaded and how it looks.
- A hidden tab stops `requestAnimationFrame` entirely. The game then looks
  completely unresponsive to input while `COURSE.state()` sits still. Check
  `document.visibilityState` and send `Page.bringToFront` before debugging
  anything else.
- Blender needs `libSM`/`libICE`; installed without sudo into `~/opt/xlibs` and
  passed via `LD_LIBRARY_PATH`. Every Linux Blender command needs that prefix.
- `uv_layers.active_render = layer` does nothing. Assign `layer.active_render = True`.
- A ground plane with reversed winding receives no light and renders black while
  everything else looks fine. So does a PMREM env capture that goes to `inf` and
  turns ACES into NaN.
- The glTF forward axis is not to be trusted. Flip the holder group and check on
  screen.
- Patching inside a shader string array in `course.html`: keep the surrounding
  quotes and commas, patch whole quoted lines, or the script dies with a syntax
  error and `COURSE` never exists.
- The ramp builder normalises its ends before picking an axis (a descending z
  run otherwise gets read as an x run and the slab lands at 90 degrees).
- Ramps do not block horizontally. Walk into the side of a low ramp and you pass
  through the slab. Nothing in the current line lets you do it, but a future
  ramp placement can.
- `.git` is 132MB from early bake commits. Bakes are ignored now but the history
  still has them.
