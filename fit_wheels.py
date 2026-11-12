#!/usr/bin/env python3
"""
Cut the fused wheels out of the Tripo car and fit four real ones.

The image-to-3D mesh is a single surface, so there is nothing to rotate. This
deletes the tyre geometry inside a cylinder around each axle and builds a wheel
object there, origin on the axle, axle along X, so the game can steer it about Y
and spin it about X.

Measured from the mesh: axles at z +-1.27, axle height 0.35, tyre face out at
0.96. Cut radius is a little generous so no sliver of the old tyre is left
behind, and the new wheel is a little big so it covers the cut.

Run: LD_LIBRARY_PATH=~/opt/xlibs/usr/lib/x86_64-linux-gnu \
     ~/opt/blender-4.2.9-linux-x64/blender -b -noaudio -P fit_wheels.py
"""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

SRC = "/home/waldo/repos/deadlight/models/arrow_tripo.glb"
OUT = "/home/waldo/repos/deadlight/models/arrow_wheels.glb"

AXLE_LEN = 1.25      # metres from the centre along Y (Blender: Y is length).
                     # measured contact patch mid: front 1.22, rear -1.25
AXLE_H = 0.366       # measured tyre radius, so the wheel touches z 0 exactly
CUT_R = 0.40         # cut a touch outside the old tyre so none of it survives
CUT_X = 0.66         # outboard of this is tyre
TYRE_R = 0.368       # matches the original 0.732 diameter, so the stance holds
TYRE_W = 0.28
RIM_R = 0.235
AXLE_X = 0.845       # wheel centre, outboard face lands at 0.985

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=SRC)

meshes = [o for o in sc.objects if o.type == "MESH"]
body = meshes[0]
print("body:", body.name, "verts:", len(body.data.vertices))

def mat(name, color, rough, metal):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m

M_TYRE = mat("tyre", (0.012, 0.013, 0.015), 0.90, 0.0)
M_RIM  = mat("rim",  (0.115, 0.125, 0.140), 0.34, 0.85)
M_HUB  = mat("hub",  (0.060, 0.065, 0.075), 0.45, 0.70)

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

# ---------------------------------------------------------------- new wheels
def wheel(name, sx, sz):
    parts = []
    # tyre: cylinder axis along X, so rotate the default Z axis cylinder
    bpy.ops.mesh.primitive_cylinder_add(vertices=28, radius=TYRE_R, depth=TYRE_W, location=(0, 0, 0))
    tyre = bpy.context.object
    tyre.name = name
    tyre.data.transform(Matrix.Rotation(math.pi/2, 4, 'Y'))
    tyre.data.materials.append(M_TYRE)
    for p in tyre.data.polygons:
        p.use_smooth = True
    # rim face, slightly proud of the tyre on the outboard side
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=RIM_R, depth=TYRE_W * 0.94, location=(0, 0, 0))
    rim = bpy.context.object
    rim.data.transform(Matrix.Rotation(math.pi/2, 4, 'Y'))
    rim.data.materials.append(M_RIM)
    for p in rim.data.polygons:
        p.use_smooth = True
    # five spokes, cheap depth at night but they catch the fill light
    for k in range(5):
        a = 2*math.pi*k/5
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
        sp = bpy.context.object
        sp.scale = (TYRE_W * 0.5, 0.045, 0.16)
        sp.data.materials.append(M_RIM)
        sp.rotation_euler = (a, 0, 0)
        sp.location = (sx * TYRE_W * 0.30, math.sin(a) * 0.15, math.cos(a) * 0.15)
        parts.append(sp)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.055, depth=TYRE_W * 1.02, location=(0, 0, 0))
    hub = bpy.context.object
    hub.data.transform(Matrix.Rotation(math.pi/2, 4, 'Y'))
    hub.data.materials.append(M_HUB)
    # arch liner: a black disc just inboard of the tyre, wider than the cut, so
    # the hole the cut left in the arch cannot be seen through. It spins with
    # the wheel and a uniform disc looks the same at any angle.
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=CUT_R + 0.025, depth=0.016, location=(0, 0, 0))
    liner = bpy.context.object
    liner.data.transform(Matrix.Rotation(math.pi/2, 4, 'Y'))
    liner.data.materials.append(M_TYRE)
    liner.location = (-sx * (TYRE_W * 0.5 + 0.02), 0, 0)
    parts += [tyre, rim, hub, liner]

    # join into one object whose origin sits on the axle
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = tyre
    bpy.ops.object.join()
    w = bpy.context.object
    w.name = name
    # geometry is already centred on the origin; the node carries the position
    w.location = (sx * AXLE_X, sz * AXLE_LEN, AXLE_H)
    return w

wheels = [
    # Blender: +Y is the nose, so the front pair sit at +AXLE_LEN
    wheel("wheel_FL", -1,  1),
    wheel("wheel_FR",  1,  1),
    wheel("wheel_RL", -1, -1),
    wheel("wheel_RR",  1, -1),
]
print("wheels:", [(w.name, [round(v, 2) for v in w.location]) for w in wheels])
print("tyre face outboard at %.3f" % (AXLE_X + TYRE_W/2))

# ---------------------------------------------------------------- verify
bm = bmesh.new(); bm.from_mesh(body.data)
left = 0
for v in bm.verts:
    p = v.co
    if abs(p.x) <= CUT_X: continue
    for sz in (-1, 1):
        dy = p.y - sz * AXLE_LEN; dz = p.z - AXLE_H
        if dy*dy + dz*dz <= (TYRE_R*0.98)**2: left += 1; break
bm.free()
print("verts still inside the new wheel volume:", left)

for o in sc.objects:
    o.select_set(o.type == "MESH")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True,
                          export_apply=True, export_yup=True, export_image_format="AUTO")
print("GLB:", OUT, round(os.path.getsize(OUT)/1e6, 2), "MB")

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
    ob = bpy.data.objects[wname]
    ob.rotation_euler = (0, 0, ang)
sc.render.engine = "BLENDER_EEVEE_NEXT"; sc.eevee.taa_render_samples = 24
for loc, path in (((4.6, -5.4, 1.9), "/tmp/wheels_front.png"), ((-5.2, 4.6, 2.1), "/tmp/wheels_rear.png")):
    cam.location = loc
    cam.rotation_euler = (Vector((0, 0, 0.7)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("shot", path)
