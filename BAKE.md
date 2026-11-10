# Baked lighting pipeline

The reason this exists: a Ryzen 5 4650U with integrated Radeon cannot light a lush
scene in real time. Cycles can. So the expensive light is computed once, offline,
and the browser or the APK just plays it back.

## What is installed and why

Blender 4.2.9 LTS runs headless from `~/opt/blender-4.2.9-linux-x64`.
It is missing `libSM` and `libICE` on this WSL image, which you install without sudo:

```bash
mkdir -p /tmp/debdl && cd /tmp/debdl
apt-get download libsm6 libice6          # works as a normal user
mkdir -p ~/opt/xlibs
for d in *.deb; do dpkg-deb -x "$d" ~/opt/xlibs; done
```

Then always launch Blender with `LD_LIBRARY_PATH=~/opt/xlibs/usr/lib/x86_64-linux-gnu`,
which `bake.sh` does for you.

## Run

```bash
./bake.sh 1024 64        # resolution, samples
```

Writes to `bake/`:

- one `*_lm.png` per object, pure irradiance (Cycles DIFFUSE bake, direct + indirect,
  colour pass off, so it is light only, no albedo)
- `baked.glb`, the geometry with a smart-projected lightmap UV
- `manifest.txt`

Open `baked.html` to see it with the lightmaps applied, and the toggle button to see
the difference with them off.

## How the web side reads it

glTF has no lightmap slot, so `baked.html` does three things:

1. copies `geometry.attributes.uv` to `uv2` (three.js lightmaps sample the second UV set)
2. loads `bake/<meshName>_lm.png` and sets `material.lightMap`
3. keeps a real-time spotlight on the camera

That last point is the whole trick for a chase game: baked GI gives you the room, the
torch gives you the movement, and you only pay for one dynamic light.

## Gotchas found the hard way

- One shared material across objects is fine: baking uses the material's *active* image
  texture node, so each object gets its own node and its own image.
- Baking requires the object to be selected and active, in OBJECT mode, with a UV map.
- The lightmap is irradiance, not colour. `pass_filter={'DIRECT','INDIRECT'}` and
  deliberately no `'COLOR'`. If you include colour you are baking the albedo in twice.
- Blender writes the PNG with `img.save()`, not `save_render()`, or you get the
  render output path instead of the image.
