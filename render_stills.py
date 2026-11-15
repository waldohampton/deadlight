#!/usr/bin/env python3
"""Render the Deadlight concept stills on nano-banana-2 (FAL)."""
import os, pathlib, urllib.request, json

env = pathlib.Path(os.path.expanduser("~/.hermes/.env")).read_text()
for line in env.splitlines():
    line = line.strip()
    if line.startswith("FAL_KEY="):
        os.environ["FAL_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
assert os.environ.get("FAL_KEY"), "no FAL_KEY"

import fal_client

OUT = pathlib.Path(os.path.expanduser("~/Downloads/deadlight-concept"))
OUT.mkdir(parents=True, exist_ok=True)

P1 = """Photorealistic 35 mm film still, camera behind and slightly above a car on a hardpacked desert track at sunset. Hero object: a low 1970s wedge coupe in matte charcoal grey, long flat rear deck, black louvred rear panel, thin horizontal amber tail lamp strip, dark tinted glass, wide wheel arches on dirty tyres, and a large pale grey parabolic satellite dish gimballed through the middle of the roof and tilted back. It is not a DeLorean, not stainless steel, no gullwing doors, no time machine wiring, no other vehicle in frame. Camera four metres behind at roof height, 40 mm equivalent, car filling the lower third. Beyond it a dead flat desert basin of dry brown gravel and sand, tyre tracks pressed into the surface, dry scrub tufts, scattered sandstone rocks. Two utility poles with sagging wires along the right of the track, receding to the horizon. On the horizon three flat topped mesas, horizontal sedimentary strata, eroded gullies, a skirt of loose scree at their base, hazed by distance. Low sun twelve degrees above the horizon behind and to the left of camera, warm orange raking light, long soft shadows to the right, dust hanging in the air around the wheels, sky grading from warm ochre at the horizon to dusty blue overhead. Fine natural film grain, realistic falloff, no flare. No people, no text, no logos, no watermark, no HUD overlay."""

P5 = """Photorealistic wide landscape photograph, a dirt track running arrow straight from the foreground into a hazy desert basin at sunset, a single small matte charcoal coupe with a roof antenna a hundred metres ahead, dust hanging behind it. Flat gravel plain, dry scrub, sandstone rocks, utility poles and sagging wires down one side, three stratified flat topped mesas on the horizon, low warm sun behind camera left, long shadows, ochre to dusty blue sky. No people, no text, no logos."""

P6 = P1.replace("No people, no text, no logos, no watermark, no HUD overlay.",
                "A man in his forties stands beside the driver door, short dark hair and beard, white linen shirt with the sleeves rolled, dark trousers, lit by the same low sun. No text, no logos, no watermark, no HUD overlay.")

JOBS = [("01-chase", P1), ("02-wide", P5), ("03-chase-character", P6)]

for slug, prompt in JOBS:
    print("submitting", slug, flush=True)
    res = fal_client.subscribe(
        "fal-ai/nano-banana-2",
        arguments={"prompt": prompt, "aspect_ratio": "16:9", "num_images": 1},
        with_logs=False,
    )
    url = res["images"][0]["url"]
    dst = OUT / (slug + ".png")
    urllib.request.urlretrieve(url, dst)
    print("saved", dst, dst.stat().st_size, url, flush=True)
