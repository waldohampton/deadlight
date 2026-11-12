#!/usr/bin/env python3
"""
Game pass on the Tripo image-to-3D car.
Import -> decimate -> bake an exact orient/scale/seat matrix -> export.

The transform is applied to the mesh data with ob.data.transform(), not with
bpy.ops.object.transform_apply(). That op works on the selection and can
silently do nothing, which is what put the last export sideways.
"""
import bpy, math, os
from mathutils import Vector, Matrix

SRC = "/home/waldo/.hermes/cache/scratch/tripo/model.glb"
OUT = "/home/waldo/repos/deadlight/models/arrow_tripo.glb"
TARGET_TRIS = 48000
LENGTH_M = 4.30
TEX_MAX = 1024

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=SRC)

meshes = [o for o in sc.objects if o.type == "MESH"]
if not meshes:
    raise SystemExit("no mesh imported")
# drop any node transform: work in the mesh's own space from here on
for o in meshes:
    o.data.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
ob = meshes[0]
print("imported:", ob.name, "tris:", len(ob.data.polygons))

def bounds(me):
    mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
    for v in me.vertices:
        for i in range(3):
            mn[i] = min(mn[i], v.co[i]); mx[i] = max(mx[i], v.co[i])
    return mn, mx

mn, mx = bounds(ob.data)
print("imported bounds", [round(v, 3) for v in mn], [round(v, 3) for v in mx])

# ---------------------------------------------------------------- decimate
before = len(ob.data.polygons)
d = ob.modifiers.new("dec", "DECIMATE")
d.decimate_type = "COLLAPSE"
d.ratio = min(1.0, TARGET_TRIS / before)
d.use_collapse_triangulate = True
bpy.context.view_layer.objects.active = ob
bpy.ops.object.modifier_apply(modifier=d.name)
print("decimated:", before, "->", len(ob.data.polygons))

# ---------------------------------------------------------------- orient
# measured: length runs along +X and the nose is at +X. A +90 Z rotation maps
# +X to +Y, and the glTF exporter turns Blender +Y into -Z, which is the
# direction the game's car faces.
mn, mx = bounds(ob.data)
size = mx - mn
length_axis = max(range(3), key=lambda i: size[i])
print("after decimate, size", [round(v, 3) for v in size], "length axis", "XYZ"[length_axis])
s = LENGTH_M / size[length_axis]

rot = Matrix.Rotation(math.pi / 2, 4, 'Z')      # nose +X -> +Y
sca = Matrix.Diagonal((s, s, s, 1.0))
ob.data.transform(sca @ rot)

mn, mx = bounds(ob.data)
size = mx - mn
print("after orient, size", [round(v, 3) for v in size])
# seat it: centre in X, centred in Y, wheels on z = 0
off = Vector((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z))
ob.data.transform(Matrix.Translation(off))
mn, mx = bounds(ob.data)
size = mx - mn
print("final bounds", [round(v, 3) for v in mn], [round(v, 3) for v in mx],
      "size", [round(v, 3) for v in size])

for p in ob.data.polygons:
    p.use_smooth = True
es = ob.modifiers.new("es", "EDGE_SPLIT")
es.split_angle = math.radians(38)
bpy.ops.object.modifier_apply(modifier=es.name)

# ---------------------------------------------------------------- textures
for img in bpy.data.images:
    if not img.size[0]:
        continue
    w, h = img.size
    if max(w, h) > TEX_MAX:
        k = TEX_MAX / max(w, h)
        img.scale(int(w * k), int(h * k))
        print("texture", img.name, (w, h), "->", tuple(img.size))

# ---------------------------------------------------------------- export
for o in sc.objects:
    o.select_set(o.type == "MESH")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True,
                          export_apply=True, export_yup=True,
                          export_image_format="AUTO", export_jpeg_quality=82)
print("GLB:", OUT, round(os.path.getsize(OUT) / 1e6, 2), "MB", "tris:", len(ob.data.polygons))

# ---------------------------------------------------------------- preview
sc.render.resolution_x = 1000
sc.render.resolution_y = 620
w = bpy.data.worlds.new("w"); sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.04, 0.045, 0.055, 1)
bpy.ops.object.light_add(type="AREA", location=(5, 6, 5))
L = bpy.context.object; L.data.energy = 2500; L.data.size = 7
L.rotation_euler = (Vector((0, 0, 0.7)) - L.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.light_add(type="AREA", location=(-6, -5, 4))
L2 = bpy.context.object; L2.data.energy = 900; L2.data.size = 8
L2.rotation_euler = (Vector((0, 0, 0.7)) - L2.location).to_track_quat("-Z", "Y").to_euler()

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
sc.collection.objects.link(cam); sc.camera = cam
cam_data.lens = 55

def shoot(loc, path):
    cam.location = loc
    cam.rotation_euler = (Vector((0, 0, 0.85)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("shot", path)

sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.eevee.taa_render_samples = 24
shoot((5.4, 6.2, 2.6), "/tmp/tripo_front34.png")
shoot((-5.6, -6.0, 2.8), "/tmp/tripo_rear34.png")
