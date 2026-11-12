#!/usr/bin/env python3
"""
Pass one on the Tripo export: import, measure, and find out which way it faces.
Writes /tmp/tripo_sheet.png (two views, so one look settles the orientation).
"""
import bpy, math, os
from mathutils import Vector

SRC = "/home/waldo/.hermes/cache/scratch/tripo/model.glb"
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=SRC)

meshes = [o for o in sc.objects if o.type == "MESH"]
print("objects:", [(o.name, len(o.data.polygons)) for o in meshes])

# world bounds
mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
size = mx - mn
print("bounds min", [round(v, 3) for v in mn], "max", [round(v, 3) for v in mx])
print("size  X %.3f  Y %.3f  Z %.3f" % (size.x, size.y, size.z))
ctr = (mn + mx) / 2
print("centre", [round(v, 3) for v in ctr])

# which horizontal axis is the car's length?
print("longest horizontal axis:", "X" if size.x > size.y else "Y")

# ---------------------------------------------------------------- two views
sc.render.resolution_x = 700
sc.render.resolution_y = 500
sc.render.film_transparent = False
w = bpy.data.worlds.new("w"); sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.06, 0.065, 0.075, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
bpy.ops.object.light_add(type="AREA", location=(4, -4, 5))
L = bpy.context.object; L.data.energy = 3000; L.data.size = 8
L.rotation_euler = (Vector((0, 0, 0.7)) - L.location).to_track_quat("-Z", "Y").to_euler()

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
sc.collection.objects.link(cam); sc.camera = cam
cam_data.lens = 60

def shoot(offset, path):
    dist = max(size) * 1.9
    cam.location = ctr + Vector(offset).normalized() * dist
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light, sh.color_type = "STUDIO", "TEXTURE"
    sh.show_shadows = True
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

shoot((0.6, 0, 1), "/tmp/tripo_pz.png")
shoot((0.6, 0, -1), "/tmp/tripo_nz.png")
shoot((0, 1, 0.35), "/tmp/tripo_py.png")
shoot((0, -1, 0.35), "/tmp/tripo_ny.png")
print("rendered 4 views")
