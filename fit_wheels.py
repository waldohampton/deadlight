#!/usr/bin/env python3
"""
Cut the fused wheels out of the Tripo car and fit Waldo's tyre model.

The image-to-3D car is one fused surface, so there was nothing to steer. This
deletes the tyre geometry inside a cylinder around each axle, then places four
copies of model.glb there: origin on the axle, axle along X, so the game steers
it about Y and rolls it about X.

model.glb measured: one mesh, 3,641 verts, 3,763 tris, axle along Z, diameter
1.0, width 0.262, one 1.47 MB texture. It is scaled to a 0.71 m diameter, which
is what the original fused tyre measured, and the texture drops to 512.

Run: LD_LIBRARY_PATH=~/opt/xlibs/usr/lib/x86_64-linux-gnu \
     ~/opt/blender-4.2.9-linux-x64/blender -b -noaudio -P fit_wheels.py
"""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

SRC = "/home/waldo/repos/deadlight/models/arrow_tripo.glb"
TYRE = "/mnt/c/Users/waldo/Downloads/model.glb"
OUT = "/home/waldo/repos/deadlight/models/arrow_wheels.glb"

AXLE_LEN = 1.25      # metres from the centre along Y (Blender: Y is length).
                     # measured contact patch mid: front 1.22, rear -1.25
AXLE_H = 0.355       # axle height = tyre radius, so the wheel meets z 0
CUT_R = 0.40         # cut a touch outside the old tyre so none of it survives
CUT_X = 0.66         # outboard of this is tyre
TYRE_D = 0.71        # finished diameter, same as the original fused tyre
AXLE_X = 0.830       # wheel centre; outer face lands around 0.925
TEX_MAX = 512        # a wheel does not need 2 k

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=SRC)
body = [o for o in sc.objects if o.type == "MESH"][0]
print("body:", body.name, "verts:", len(body.data.vertices))

def mat(name, color, rough, metal):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m

M_LINER = mat("liner", (0.010, 0.011, 0.012), 0.95, 0.0)

# ---------------------------------------------------------------- cut the old
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
doomed = []
for v in bm.verts:
    p = v.co
    if abs(p.x) <= CUT_X:            # Blender space here: x width, y length, z up
        continue
    for sz in (-1, 1):
        dy = p.y - sz * AXLE_LEN
        dz = p.z - AXLE_H
        if dy*dy + dz*dz <= CUT_R*CUT_R:
            doomed.append(v)
            break
print("deleting", len(doomed), "fused tyre verts")
bmesh.ops.delete(bm, geom=doomed, context='VERTS')
bm.to_mesh(body.data)
bm.free()
body.data.update()
print("body verts after cut:", len(body.data.vertices))

# ---------------------------------------------------------------- the tyre
before = set(sc.objects)
bpy.ops.import_scene.gltf(filepath=TYRE)
tyre_parts = [o for o in sc.objects if o.type == "MESH" and o not in before]
if not tyre_parts:
    raise SystemExit("tyre import produced no mesh")
tsrc = tyre_parts[0]
print("tyre import produced", len(tyre_parts), "meshes:", [o.name for o in tyre_parts])
if len(tyre_parts) > 1:
    for nm in [o.name for o in tyre_parts if o is not tsrc]:
        ob = bpy.data.objects.get(nm)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)

mn = Vector((9e9, 9e9, 9e9)); mx = Vector((-9e9, -9e9, -9e9))
for v in tsrc.data.vertices:
    for i in range(3):
        mn[i] = min(mn[i], v.co[i]); mx[i] = max(mx[i], v.co[i])
ext = mx - mn
# a tyre is a disc: the axle is the shortest axis. Blender's importer maps the
# glTF z axle onto Blender y, so do not assume which one it is.
axle_axis = min(range(3), key=lambda i: ext[i])
others = [i for i in range(3) if i != axle_axis]
diameter = max(ext[i] for i in others)
s = TYRE_D / diameter
if axle_axis == 1:
    R = Matrix.Rotation(math.pi / 2, 4, 'Z')      # axle y -> x
elif axle_axis == 2:
    R = Matrix.Rotation(math.pi / 2, 4, 'Y')      # axle z -> x
else:
    R = Matrix.Identity(4)
print("tyre: verts %d  extents %s  axle axis %s  diameter %.3f  width %.3f  scale %.3f"
      % (len(tsrc.data.vertices), [round(v, 3) for v in ext], "xyz"[axle_axis],
         diameter, ext[axle_axis] * s, s))
M = Matrix.Scale(s, 4) @ R
ctr = (mn + mx) / 2
tsrc.data.transform(Matrix.Translation(-(M @ ctr)))
tsrc.data.transform(M)
tsrc.matrix_world = Matrix.Identity(4)
for img in bpy.data.images:
    if img.size[0] > TEX_MAX:
        k = TEX_MAX / max(img.size)
        img.scale(int(img.size[0] * k), int(img.size[1] * k))
        print("texture", img.name, "->", tuple(img.size))

mn2 = Vector((9e9, 9e9, 9e9)); mx2 = Vector((-9e9, -9e9, -9e9))
for v in tsrc.data.vertices:
    for i in range(3):
        mn2[i] = min(mn2[i], v.co[i]); mx2[i] = max(mx2[i], v.co[i])
e2 = mx2 - mn2
print("fitted tyre: extents %s  centre %s  (x is the axle now)"
      % ([round(v, 3) for v in e2], [round(v, 3) for v in ((mn2 + mx2) / 2)]))

# ---------------------------------------------------------------- four wheels
def make_wheel(name, sx, sz):
    w = tsrc.copy()
    w.data = tsrc.data.copy()
    sc.collection.objects.link(w)
    w.name = name
    w.data.name = name + "_mesh"
    w.matrix_world = Matrix.Identity(4)
    # arch liner: a black disc inboard, wider than the cut, so the hole the cut
    # left in the arch cannot be seen through. It spins with the wheel and a
    # uniform disc looks the same at any angle.
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=CUT_R + 0.025, depth=0.016, location=(0, 0, 0))
    liner = bpy.context.object
    liner.data.transform(Matrix.Rotation(math.pi/2, 4, 'Y'))
    liner.data.materials.append(M_LINER)
    liner.location = (-sx * 0.115, 0, 0)
    bpy.ops.object.select_all(action='DESELECT')
    liner.select_set(True)
    w.select_set(True)
    bpy.context.view_layer.objects.active = w
    bpy.ops.object.join()
    w = bpy.context.object
    w.name = name
    w.location = (sx * AXLE_X, sz * AXLE_LEN, AXLE_H)
    return w

wheels = [
    # Blender: +Y is the nose, so the front pair sit at +AXLE_LEN
    make_wheel("wheel_FL", -1,  1),
    make_wheel("wheel_FR",  1,  1),
    make_wheel("wheel_RL", -1, -1),
    make_wheel("wheel_RR",  1, -1),
]
bpy.data.objects.remove(tsrc, do_unlink=True)   # the prototype is copied now
print("wheels:", [(w.name, [round(v, 3) for v in w.location]) for w in wheels])
print("wheel bottom (should be ~0): %.4f" % (AXLE_H - TYRE_D / 2))

# ---------------------------------------------------------------- verify
bm = bmesh.new(); bm.from_mesh(body.data)
left = 0
for v in bm.verts:
    p = v.co
    if abs(p.x) <= CUT_X: continue
    for sz in (-1, 1):
        dy = p.y - sz * AXLE_LEN; dz = p.z - AXLE_H
        if dy*dy + dz*dz <= (TYRE_D / 2 * 0.98) ** 2:
            left += 1
            break
bm.free()
print("body verts still inside the new wheel volume:", left)

tris = sum(len(o.data.polygons) for o in sc.objects if o.type == "MESH")
# name the tyre material so the game can treat rubber as rubber instead of
# lifting every textured material the way it lifts the car paint
for o in wheels:
    for m in o.data.materials:
        if m and m.name != "liner":
            m.name = "tyre_tex"
for o in sc.objects:
    o.select_set(o.type == "MESH")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True,
                          export_apply=True, export_yup=True, export_image_format="AUTO")
print("GLB:", OUT, round(os.path.getsize(OUT) / 1e6, 2), "MB", "tris:", tris)

# ---------------------------------------------------------------- preview
sc.render.resolution_x = 1000; sc.render.resolution_y = 620
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.04, 0.045, 0.055, 1)
bpy.ops.object.light_add(type="AREA", location=(5, 6, 5))
L = bpy.context.object; L.data.energy = 2500; L.data.size = 7
L.rotation_euler = (Vector((0, 0, 0.7)) - L.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.light_add(type="AREA", location=(-6, -5, 4))
L2 = bpy.context.object; L2.data.energy = 900; L2.data.size = 8
L2.rotation_euler = (Vector((0, 0, 0.7)) - L2.location).to_track_quat("-Z", "Y").to_euler()
cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data)
sc.collection.objects.link(cam); sc.camera = cam; cam_data.lens = 55
# steer the front wheels so the render proves the pivots are right.
# In Blender the steer axis is Z (up); the export turns that into glTF Y.
for wname, ang in (("wheel_FL", 0.5), ("wheel_FR", 0.5)):
    bpy.data.objects[wname].rotation_euler = (0, 0, ang)
sc.render.engine = "BLENDER_EEVEE_NEXT"; sc.eevee.taa_render_samples = 24
for loc, path in (((4.6, -5.4, 1.9), "/tmp/tyre_front.png"), ((-5.2, 4.6, 2.1), "/tmp/tyre_rear.png")):
    cam.location = loc
    cam.rotation_euler = (Vector((0, 0, 0.7)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("shot", path)
