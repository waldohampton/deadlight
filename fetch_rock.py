#!/usr/bin/env python3
"""
Fetch the rock pass: the last big flat colour in the desert.

Same rules as fetch_tex.py and fetch_desert.py. Poly Haven, all CC0, no
attribution required, recorded in CREDITS.txt anyway.

What each asset is for, and the real world size of one tile, which is what sets
the repeat on the meshes:

  cliff_side        1830 cm. The mesas. A sedimentary canyon wall with the
                    strata running horizontally, which is the single thing that
                    separates a mesa from a lump of coloured rock.
  rock_boulder_cracked 1390 cm. The 900 scattered rocks, so the clutter is the
                    same stone the mesas are made of, at a size the eye can
                    check.
  gravelly_sand     2480 cm. The middle scale of the ground. The plain already
                    has a 40 m macro scan and a 1 m pebble detail, and nothing
                    in between, which is why it tiles visibly across a 520 m
                    disc.

Run: python3 fetch_rock.py
Writes: models/tex/{cliff,boulder,gravel}_*.jpg, appends to models/tex/CREDITS.txt
"""
import json, os, io, urllib.request
from PIL import Image

OUT = "/home/waldo/repos/deadlight/models/tex"
SIZE = 1024
QUALITY = 82
UA = {"User-Agent": "deadlight/1.0"}

# id -> (slug, real world size of one tile in metres, what it is for)
SETS = {
    "cliff_side":           ("cliff",  18.30, "mesas on the horizon"),
    "rock_boulder_cracked": ("boulder", 13.90, "the scattered rock clutter"),
    "gravelly_sand":        ("gravel", 24.80, "the middle scale of the ground"),
}


def api(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def pick(files, names, res="1k"):
    for n in names:
        node = files.get(n)
        if not node:
            continue
        for r in (res, "2k", "4k"):
            if r in node and "jpg" in node[r]:
                return node[r]["jpg"]["url"]
    return None


os.makedirs(OUT, exist_ok=True)
credits = []
for asset, (slug, real_m, use) in SETS.items():
    try:
        files = api("https://api.polyhaven.com/files/%s" % asset)
    except Exception as e:
        print("SKIP %s: %s" % (asset, e))
        continue
    jobs = [
        (pick(files, ["Diffuse", "diff", "Color", "col"]), slug + "_col.jpg"),
        (pick(files, ["nor_gl", "nor", "Normal"]),        slug + "_nrm.jpg"),
        (pick(files, ["Rough", "rough", "Roughness"]),    slug + "_rgh.jpg"),
    ]
    got = []
    for url, name in jobs:
        if not url:
            print("  %s: missing %s" % (asset, name))
            continue
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
            data = r.read()
        im = Image.open(io.BytesIO(data)).convert("RGB")
        if max(im.size) > SIZE:
            im = im.resize((SIZE, SIZE), Image.LANCZOS)
        p = os.path.join(OUT, name)
        im.save(p, "JPEG", quality=QUALITY, optimize=True)
        got.append("%s %dKB" % (name, os.path.getsize(p) // 1024))
    credits.append("%s (%s, %s, %.1f m tile): Poly Haven, CC0" % (asset, slug, use, real_m))
    print("%-22s %s" % (asset, ", ".join(got)))

cp = os.path.join(OUT, "CREDITS.txt")
old = open(cp).read() if os.path.exists(cp) else ""
with open(cp, "w") as f:
    f.write(old.rstrip("\n") + "\n\nRock pass:\n" + "\n".join(credits) + "\n")
total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
print("total %d KB in %s" % (total // 1024, OUT))
