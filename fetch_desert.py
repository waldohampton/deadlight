#!/usr/bin/env python3
"""
Fetch the desert pass: a photographed sky and two desert ground sets.

Same rules as fetch_tex.py. Poly Haven, all CC0, so no attribution is required,
though CREDITS.txt records it anyway.

What each asset is for:

  sandy_gravel_02  the big ground: 40 m per tile on the open plain, so the eye
                   reads a dusty expanse instead of a repeat
  pebble_ground_01 the detail layer: multiplied in the shader at about 1.2 m a
                   tile, which is what puts gravel under the wheels. A single
                   texture cannot do both, which is why the plain read as a
                   flat plane at chase-camera distance.
  qwantani_sunset_puresky  a photographed sunset, equirect, no ground in it, sun
                   low and wispy cloud in front of it. The dome samples this
                   instead of a hand-mixed gradient.

The script also measures the sky and prints the numbers course.html needs:
where the photographed sun sits (so the dome can be rotated to put it exactly
where the DirectionalLight already shines from) and the colour of the haze band
just above the horizon (so the fog can match it instead of fighting it).

Run: python3 fetch_desert.py
Writes: models/tex/{ground,pebble}_*.jpg, models/tex/sky_sunset.jpg
"""
import io, json, math, os, urllib.request
from PIL import Image

OUT = "/home/waldo/repos/deadlight/models/tex"
SIZE = 1024
QUALITY = 82

SKY = "qwantani_sunset_puresky"
SKY_W, SKY_H = 2048, 1024        # equirect, 2:1
SKY_QUALITY = 84

SETS = {
    # id -> (slug, maps it needs)
    "sandy_gravel_02":  ("ground", ("Diffuse", "nor_gl", "Rough")),
    "pebble_ground_01": ("pebble", ("Diffuse",)),
}

HDR = {"User-Agent": "deadlight/1.0 (texture fetch)"}


def api(url):
    req = urllib.request.Request(url, headers=HDR)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fetch(url):
    req = urllib.request.Request(url, headers=HDR)
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def pick(files, names, res="1k"):
    for n in names:
        node = files.get(n)
        if not node:
            continue
        for r in (res, "2k", "4k"):
            if r in node and "jpg" in node[r]:
                return node[r]["jpg"]["url"]
    return None


def pack(name, url):
    data = fetch(url)
    im = Image.open(io.BytesIO(data)).convert("RGB")
    if max(im.size) > SIZE:
        im = im.resize((SIZE, SIZE), Image.LANCZOS)
    p = os.path.join(OUT, name)
    im.save(p, "JPEG", quality=QUALITY, optimize=True)
    return "%s %dKB" % (name, os.path.getsize(p) // 1024)


os.makedirs(OUT, exist_ok=True)
credits = []

for asset, (slug, maps) in SETS.items():
    files = api("https://api.polyhaven.com/files/%s" % asset)
    got = []
    for m in maps:
        suffix = {"Diffuse": "_col", "nor_gl": "_nrm", "Rough": "_rgh"}[m]
        url = pick(files, [m])
        if not url:
            print("  %s: missing %s" % (asset, m))
            continue
        got.append(pack(slug + suffix + ".jpg", url))
    credits.append("%s (%s): Poly Haven, CC0" % (asset, slug))
    print("%-18s %s" % (asset, ", ".join(got)))

# ---------------------------------------------------------------- the sky
files = api("https://api.polyhaven.com/files/%s" % SKY)
raw = fetch(files["tonemapped"]["url"])
im = Image.open(io.BytesIO(raw)).convert("RGB")
w, h = im.size
im = im.resize((SKY_W, SKY_H), Image.LANCZOS)
sky_path = os.path.join(OUT, "sky_sunset.jpg")
im.save(sky_path, "JPEG", quality=SKY_QUALITY, optimize=True)
credits.append("%s (sky): Poly Haven, CC0" % SKY)
print("%-18s sky_sunset.jpg %dKB from %d x %d" %
      (SKY, os.path.getsize(sky_path) // 1024, w, h))

# ---------------------------------------------------------------- sky maths
# three samples an equirect as u = atan2(z, x) / 2pi + 0.5 and
# v = asin(y) / pi + 0.5, so image column = u * width and row (from the top) =
# (1 - v) * height. Find the sun by thresholding the brightest sky pixels and
# taking the centroid, so the number is measured, not guessed.
px = im.load()
best = []
for y in range(0, SKY_H // 2):
    for x in range(0, SKY_W, 2):
        r, g, b = px[x, y]
        v = r + g + b
        if v > 690:                      # near blown, the sun's own disc
            best.append((x, y))
if not best:
    # fall back to the single brightest pixel if the sun is dim or clouded in
    top = max(((sum(px[x, y]), x, y) for y in range(0, SKY_H // 2)
               for x in range(0, SKY_W, 2)))
    best = [(top[1], top[2])]
sx = sum(p[0] for p in best) / len(best)
sy = sum(p[1] for p in best) / len(best)
u = sx / SKY_W
v = 1.0 - sy / SKY_H
sun_az = (u - 0.5) * 360.0               # degrees from +X toward +Z
sun_el = (v - 0.5) * 180.0               # degrees above the horizon

# haze band just above the horizon, around the sun side, is what the fog should
# be set to or the ground fades into a colour that is not in the sky
band = im.crop((0, int(SKY_H * 0.44), SKY_W, int(SKY_H * 0.50))).resize((64, 4))
bp = band.load()
n = 0
tr = tg = tb = 0
for y in range(band.size[1]):
    for x in range(band.size[0]):
        r, g, b = bp[x, y]
        tr += r; tg += g; tb += b; n += 1
horizon = (tr // n, tg // n, tb // n)

print(json.dumps({
    "sky_file": "models/tex/sky_sunset.jpg",
    "image": [SKY_W, SKY_H],
    "sun_pixels": len(best),
    "sun_uv": [round(u, 4), round(v, 4)],
    "sun_azimuth_deg": round(sun_az, 1),
    "sun_elevation_deg": round(sun_el, 1),
    "horizon_rgb": list(horizon),
    "horizon_hex": "0x%02x%02x%02x" % horizon,
}, indent=1))

with open(os.path.join(OUT, "CREDITS.txt"), "a") as f:
    f.write("\n\nDesert pass:\n" + "\n".join(credits) + "\n")

total = sum(os.path.getsize(os.path.join(OUT, f))
            for f in os.listdir(OUT) if f.endswith((".jpg", ".png")))
print("total %d KB in %s" % (total // 1024, OUT))
