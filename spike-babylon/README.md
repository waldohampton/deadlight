# deadlight — Babylon.js phase-one spike

A single static page that answers one question: **is Babylon's frame better than the
three.js one, for the price of a rewrite?** Phase one only — car, ground, sun, sky, ACES.
No gameplay, no driving, no checkpoints, no HUD (except an optional debug readout).

The existing game (`course.html`, `index.html`, everything outside this folder) is
untouched. This folder is self-contained.

```
spike-babylon/
  index.html                   the scene (one inline script, no build step)
  babylon.js                   Babylon.js v9.35.0 UMD, vendored (8,908,650 B)
  babylonjs.loaders.min.js     glTF loader UMD, vendored (884,628 B)
  qwantani_sunset_2k_cd.hdr    Poly Haven CC0 sunset, re-encoded photometric (4,015,589 B)
  shots/                       measured evidence frames
```

## Run it

From the repo root (this is the same static server the rest of the game uses):

```
python3 -m http.server 8900 --bind 127.0.0.1
# then open http://127.0.0.1:8900/spike-babylon/
```

The existing game already runs on **8899** — do not touch it.

URL knobs (all optional): `?hud=0`, `?e=<exposure>`, `?env=<ibl factor>`, `?ssao=0`,
`?orbit=1`, `?glb=1` (shows the character GLB), `?rocks=<n>`, `?fogend=<m>`.

## Calibration

Everything is lit in real units, the same way `course.html` does it:

| quantity | value | why |
|---|---|---|
| sun | `DirectionalLight`, `#ffdcae`, **15 000 lux** | low golden-hour sun |
| sun angle | **14° elevation, azimuth 46°** (ahead-right, just out of frame) | long shadows, backlit chase frame |
| sun units | `intensityMode = ILLUMINANCE` (mode 3) | Babylon resolves `AUTOMATIC` to ILLUMINANCE for directional lights (divisor 1); set explicitly, verified at runtime |
| sky | HDRI, mid-sky **896 cd/m²** | `qwantani_sunset_puresky`, CC0 |
| IBL | `scene.environmentTexture`, `environmentIntensity = 1.0` | the sky is the fill; no ambient, no fill lights |
| tone map | ACES, `exposure = 0.00073` | the only dial |
| shadows | Cascaded Shadow Maps, 4 cascades, 2048², PCF, 480 m | vs one hand-rolled 34 m box in three.js |

The HDRI is **re-encoded**, not used raw. The file's mid-sky mean is 0.945 in its own
units, so every pixel is multiplied by 951.94 to make **1 unit = 1 cd/m²** (mid-sky
lands at 896). That is what lets `scene.environmentIntensity` be a physical number
instead of a magic dial. The re-encode is reproducible from the original Poly Haven 2k
HDR (download URL below) with a small RGBE scalar multiply.

Visible dome is graded **0.62×** (`reflectionTexture.level`): the HDRI's near-sun glow
is ~3 stops above its sky mean and ACES leaves it at 200+, which pushed the frame's mean
25 points above the reference. The IBL still sees the full 900 cd/m². **This is a grade
on a backdrop, not a change to the light, and it is one number.**

## Acceptance test — measured, not eyeballed

Screenshot `shots/hero.png` at 1376×768, measured in Python/PIL with 709 luma
(`0.2126 R + 0.7152 G + 0.0722 B`), which is how the reference numbers were produced.

| metric | reference `01-chase.png` | this frame | delta |
|---|---|---|---|
| mean | 100.4 | **101.8** | +1.4 |
| median | 102 | **102** | 0 |
| 1st percentile | 6 | 8 | +2 |
| 95th percentile | 170 | 193 | +23 |
| 99th percentile | 178 | 199 | +21 |
| top third mean | 135.6 | 125.5 | −10.1 |
| middle third mean | 99.7 | 107.9 | +8.2 |
| bottom third mean | 69.6 | 70.1 | +0.5 |

Mean and median land inside the ±5 gate. The 95th/99th are hotter than the reference
because the HDRI's near-sun glow sits at the right edge of frame and the reference's sun
is further out of frame; that is the shape of this sky, not a tone-curve difference.
The bottom third — the ground and road, where the light actually lands — is within 0.5.

Exposure sweep actually run (in-browser `readPixels`, 1376×768):

| exposure | mean | median | p95 |
|---|---|---|---|
| 0.00066 | 96.2 | 95 | 187 |
| 0.00069 | 98.4 | 98 | 190 |
| 0.00071 | 99.8 | 100 | 191 |
| **0.00073** | **101.2** | **102** | 193 |

## The thing the three.js build could not do

The brief said the sky never lit the ground. Here it does, and it is measurable by
turning the environment off and changing nothing else (`shots/ibl-off.png` vs
`shots/ibl-on.png`, same camera, same sun, same exposure):

| probe | env = 0 | env = 1.0 (physical) |
|---|---|---|
| mesa shadow face, 80×40 px patch, RGB | **(1, 1, 0)** — pure black | **(50, 51, 55)** — cool, sky-coloured |
| shadow under the car, RGB | **(0, 0, 0)** | **(53, 53, 53)** |
| whole frame mean | 81.2 | 101.8 |
| pixels changed by >5 levels | — | **73.4 %** of the frame |

The mesa patch coming back (50, 51, 55) rather than neutral grey is the tell: that light
is the blue upper sky, not an ambient constant. No fog is used to fake it; fog here is
only atmosphere (`fogStart 60`, `fogEnd 900`, fog colour = horizon sky radiance).

CSM likewise measured (`shots/csm-distance-on.png` vs `csm-distance-off.png`, elevated
camera 300 m up-road): with shadows on, **4.14 % of the frame** is shadowed across the
full width of the visible ground with a **mean shadow depth of 45 levels**, from the
foreground to the far rocks. The cascades are real and they reach.

## Cost

| item | bytes |
|---|---|
| `babylon.js` (v9.35.0 UMD) | 8,908,650 |
| `babylonjs.loaders.min.js` | 884,628 |
| HDRI (2k, photometric) | 4,015,589 |
| `waldo_game.glb` (loaded only to measure it) | 3,338,024 |
| 8 textures (ground, road, cliff, boulder + normals) | ~2,048,000 |
| `index.html` | 26,730 |
| **page total** | **≈ 19.2 MB** |

The three.js build's whole engine is `three.min.js` (603 KB) + `GLTFLoader.js` (96 KB).
**Babylon is 14× the library weight** (9.8 MB vs 0.7 MB) before a single asset.

Timings on this machine, which is **software-rendered** — headless Chrome here reports
`ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)))`, so treat these as relative:

| measurement | value |
|---|---|
| first frame, assets cold, localhost | **2.4 s** (1.6 s warm) |
| render cost, all on, 1376×768 | **8.2 ms/frame** (194 draw calls) |
| render cost, SSAO2 off | 5.6 ms/frame |
| render cost, CSM off | 3.8 ms/frame |
| `engine.getFps()` | meaningless here — the tab is backgrounded and rAF is throttled to 0.6 Hz; frame *cost* above is the honest number |

`csm.autoCalcDepthBounds = true` cost **622 ms/frame** on this renderer against **9.3 ms**
with it off — it re-renders the shadow maps to compute depth bounds every frame. That is
the single biggest performance trap in the spike and it is now off.

## What the glb actually is (read this before planning anything)

The brief called `models/waldo_game.glb` "the car". It is not. Measured at runtime with
`getHierarchyBoundingVectors`:

```
min  [-0.481, 0.000, -0.148]
max  [ 0.481, 1.750,  0.150]
size [ 0.963, 1.750,  0.299]   metres
2 meshes · 25 nodes · 1 skeleton (head, spine, arms, legs)
```

A 1.75 m rigged humanoid, not a vehicle. It is loaded and measured, then hidden; `?glb=1`
stands it beside the car so you can see it. The car in the frame is `course.html`'s
Calder Arrow rebuilt in Babylon (3.9 m long, wheels r 0.36 with the tyre bottom exactly
at y = 0), because that is the car the game actually drives.

`models/tex/gravel_road_col.jpg` and `cliff_side`/`boulder` do not exist under those
names. What is in the repo and used here: `gravel_col/nrm` (ground, 16 m tile),
`road_col/nrm` (road, 5 m), `cliff_col/nrm` (mesas, 18.3 m), `boulder_col/nrm` (rocks,
13.9 m). `CREDITS.txt` is untouched.

## Shipping this for real

1. **Bake an `.env`** with the Babylon IBL tool (`sandbox.babylonjs.com` → environment
   texture tools, or `babylonjs-gltf2character`'s sibling CLI). Why: `HDRCubeTexture`
   decodes a 4 MB equirect and prefilters it **on the main thread at load** (that is most
   of the 2.4 s first frame). A `.env` is the already-prefiltered cubemap — much smaller,
   no decode, no prefilter, correct roughness mips, and it can be streamed. The page
   would then use `CubeTexture.CreateFromPrefilteredData("sky.env", scene)`.
2. Keep the sky/IBL split. ONE texture for both, graded only in the skybox material.
3. `csm.autoCalcDepthBounds = false`, `shadowMaxZ` fixed to the camera's far shadow range.
4. If the tab's MSAA matters, note SSAO2 silently disables the canvas MSAA; FXAA is added
   to compensate and that is a real softness cost.

## Honest verdict

**Lighting machinery: Babylon wins clearly.** Cascaded shadows, ACES as one number, and
an IBL path that actually puts sky into the shadow side are all built in and measured
here. In three.js the CSM had to be a single 34 m box, the sky was a hand-written shader
that lit nothing, and the black shadow side was being hidden with fog — the source says
so in its own comments.

**Frame: Babylon does not win by itself.** The spike's frame is cruder than the incumbent
game's (`shots/threejs-game.png`): boxy car, five cylinder mesas, tiled textures. Art
dominates the picture; a renderer swap does not fix a low-poly car. The incumbent frame
also measured mean 66 / median 65, i.e. it is darker than the reference, but it is not
full of black slabs at its own default framing.

**And the specific win is portable.** The thing that was broken — sky not lighting the
ground — is one `PMREMGenerator` + `scene.environment` + an HDRI in three.js, maybe
60 lines. Babylon gives it to you for free, plus CSM and SSAO2, but the price is a
9.8 MB engine and a rewrite of 3 000 working lines.

So: **no-go on "rewrite for the lighting"** as a standalone justification. If the rewrite
is happening anyway for tooling/physics/editor reasons, Babylon's frame is a good place
to land. If the goal is only "make the desert light read", fix the environment map in
three.js first and spend the rewrite budget on the car and the mesas.

## Known rough edges in Babylon 9.35 (found the hard way)

- `BackgroundMaterial` + HDR cube rendered **pure black** even with `SKYBOX_MODE` set and
  the texture ready. A `StandardMaterial` with `disableLighting`, black diffuse/specular/
  emissive and `reflectionTexture.coordinatesMode = SKYBOX_MODE` works.
- Cube textures default to `CUBIC_MODE`; a skybox must be told `SKYBOX_MODE` or it samples
  one face and the sky is black.
- Two `HDRCubeTexture`s from the same URL created in the same tick raced each other and
  one failed with "Failed to parse texture data". One load, cloned for the skybox.
- `PBRMaterial.metallic` defaults to **1.0**, not 0. Everything here sets it.
- Texture tiling lives on the texture object (`uScale`), so a mesh whose UVs already carry
  world-scale tiling gets scale applied twice and the surface averages to flat colour.
- `SSAO2RenderingPipeline` turns off canvas MSAA with no warning.
- CSM's `autoCalcDepthBounds` is a 60× frame cost on a fixed camera.

## Asset provenance

- `qwantani_sunset_puresky` — Poly Haven, **CC0**. Source:
  `https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/qwantani_sunset_puresky_2k.hdr`
  (4,171,959 B), re-encoded photometric as `qwantani_sunset_2k_cd.hdr`.
- Ground/road/cliff/boulder textures — Poly Haven CC0, from `../models/tex/`,
  see `../models/tex/CREDITS.txt` (untouched).
- Babylon.js is Apache-2.0. Loader: `https://cdn.babylonjs.com/loaders/babylonjs.loaders.min.js`.
