#!/usr/bin/env python3
"""
Measure the fused wheels in the Tripo car so they can be cut free.
Prints an occupancy table of the low, outboard geometry in y (length) and z (up).
"""
import bpy, os
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath="/home/waldo/repos/deadlight/models/arrow_tripo.glb")
ob = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
print("mesh:", ob.name, "verts:", len(ob.data.vertices))
print("obj loc:", [round(v, 3) for v in ob.location], "rot:", [round(v, 3) for v in ob.rotation_euler])

# world-ish coords: apply the object transform to read real positions
M = ob.matrix_world
pts = [M @ v.co for v in ob.data.vertices]
xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
print("bounds x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f" % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))

# only outboard, low geometry: the tyres live there
wheel = [p for p in pts if abs(p.x) > 0.55 and p.z < 0.95]
print("outboard low verts:", len(wheel))

# y histogram, 10 cm buckets, to find the two axles
import collections
hy = collections.Counter(round(p.y * 10) / 10 for p in wheel)
print("y buckets:")
for k in sorted(hy):
    print("  y %5.1f  %s" % (k, '#' * min(60, hy[k] // 8)))

# z histogram for the same set, to find the tyre radius
hz = collections.Counter(round(p.z * 20) / 20 for p in wheel)
print("z buckets:")
for k in sorted(hz):
    print("  z %5.2f  %s" % (k, '#' * min(60, hz[k] // 8)))
