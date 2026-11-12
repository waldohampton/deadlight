#!/usr/bin/env python3
"""
Download CC0 photo textures from Poly Haven and pack them small.

Poly Haven assets are CC0, so nothing here needs attribution, though it is
given in models/tex/CREDITS.txt anyway.

Writes 1024 px JPEGs, which is the right size for a browser game where the
camera is doing 60 km/h: 2 k costs 4x the bytes and you cannot see it.

Run: python3 fetch_tex.py
"""
import json, os, io, urllib.request
from PIL import Image

OUT = "/home/waldo/repos/deadlight/models/tex"
SIZE = 1024
QUALITY = 82

# id -> what it is for
SETS = {
    "asphalt_05":        ("asphalt",  "yard floor"),
    "brushed_concrete_03": ("concrete", "sheds, blocks, kerbs"),
    "rusty_metal_02":    ("metal",    "tanks, pipes, railings"),
}

def api(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "deadlight/1.0"}), timeout=60) as r:
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
for asset, (slug, use) in SETS.items():
    try:
        files = api("https://api.polyhaven.com/files/%s" % asset)
    except Exception as e:
        print("SKIP %s: %s" % (asset, e))
        continue
    jobs = [
        (pick(files, ["Diffuse", "diff", "Color", "col"]), slug + "_col.jpg", True),
        (pick(files, ["nor_gl", "nor", "Normal"]),        slug + "_nrm.jpg", False),
        (pick(files, ["Rough", "rough", "Roughness"]),    slug + "_rgh.jpg", False),
    ]
    got = []
    for url, name, srgb in jobs:
        if not url:
            print("  %s: missing %s" % (asset, name))
            continue
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "deadlight/1.0"}), timeout=120) as r:
            data = r.read()
        im = Image.open(io.BytesIO(data)).convert("RGB")
        if max(im.size) > SIZE:
            im = im.resize((SIZE, SIZE), Image.LANCZOS)
        p = os.path.join(OUT, name)
        im.save(p, "JPEG", quality=QUALITY, optimize=True)
        got.append("%s %dKB" % (name, os.path.getsize(p) // 1024))
    credits.append("%s (%s, %s): Poly Haven, CC0" % (asset, slug, use))
    print("%-20s %s" % (asset, ", ".join(got)))

with open(os.path.join(OUT, "CREDITS.txt"), "w") as f:
    f.write("Textures from Poly Haven, all CC0 (public domain, no attribution required).\n\n")
    f.write("\n".join(credits) + "\n")
total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
print("total %d KB in %s" % (total // 1024, OUT))
