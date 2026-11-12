#!/usr/bin/env python3
"""
Calder Arrow 305 - procedural body for Deadlight.
Run: LD_LIBRARY_PATH=~/opt/xlibs/usr/lib/x86_64-linux-gnu ~/opt/blender-4.2.9-linux-x64/blender -b -noaudio -P build_arrow.py
Writes models/arrow_game.glb plus two preview renders.
Nose is +Y in Blender, which lands at -Z in glTF, the direction the game's CAR faces.
"""
import bpy, bmesh, math, os, traceback
from mathutils import Vector

OUT_GLB = "/home/waldo/repos/deadlight/models/arrow_game.glb"

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# ------------------------------------------------------------------ materials
def mat(name, color, rough, metal, emit=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1.0)
        b.inputs["Emission Strength"].default_value = strength
    return m

M_PAINT = mat("paint", (0.018, 0.020, 0.024), 0.50, 0.35)
M_TRIM  = mat("trim",  (0.010, 0.011, 0.013), 0.42, 0.55)
M_GLASS = mat("glass", (0.005, 0.008, 0.011), 0.08, 0.90)
M_RIM   = mat("rim",   (0.075, 0.080, 0.090), 0.35, 0.90)
M_TYRE  = mat("tyre",  (0.009, 0.010, 0.011), 0.88, 0.00)
M_DISH  = mat("dish",  (0.360, 0.375, 0.395), 0.30, 0.92)
M_LAMP  = mat("lamp",  (0.90, 0.80, 0.55), 0.30, 0.0, emit=(1.0, 0.88, 0.62), strength=7.0)
M_TAIL  = mat("tail",  (0.60, 0.06, 0.04), 0.35, 0.0, emit=(1.0, 0.10, 0.04), strength=6.0)
M_SILL  = mat("sill",  (0.45, 0.34, 0.10), 0.40, 0.20, emit=(1.0, 0.62, 0.12), strength=3.5)

# ------------------------------------------------------------------ helpers
def catmull(p0, p1, p2, p3, t):
    t2, t3 = t*t, t*t*t
    return 0.5 * ((2*p1) + (-p0 + p2)*t + (2*p0 - 5*p1 + 4*p2 - p3)*t2 + (-p0 + 3*p1 - 3*p2 + p3)*t3)

def resample(stations, n_out):
    """smooth the station list so the body loft is not faceted along its length"""
    out = []
    m = len(stations)
    for i in range(n_out):
        u = i / (n_out - 1) * (m - 1)
        k = min(int(u), m - 2)
        t = u - k
        p0 = stations[max(k-1, 0)]
        p1 = stations[k]
        p2 = stations[k+1]
        p3 = stations[min(k+2, m-1)]
        out.append(tuple(catmull(p0[j], p1[j], p2[j], p3[j], t) for j in range(4)))
    return out

def ring(hw, bot, top, y, n=20, e_side=0.55, e_up=0.72):
    """superellipse cross section: flat-ish floor, tucked sides, rounded shoulder"""
    mid = (bot + top) / 2.0
    hh = (top - bot) / 2.0
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        x = hw * math.copysign(abs(c) ** e_side, c)
        z = mid + hh * math.copysign(abs(s) ** e_up, s)
        pts.append((x, y, max(z, bot)))
    return pts

def loft(name, stations, material, n_ring=20, smooth=True):
    verts, faces = [], []
    for (y, hw, bot, top) in stations:
        verts += ring(hw, bot, top, y, n_ring)
    ns = len(stations)
    for i in range(ns - 1):
        a, b = i * n_ring, (i + 1) * n_ring
        for k in range(n_ring):
            k2 = (k + 1) % n_ring
            faces.append((a + k, a + k2, b + k2, b + k))
    faces.append(tuple(range(n_ring - 1, -1, -1)))
    base = (ns - 1) * n_ring
    faces.append(tuple(base + k for k in range(n_ring)))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    me.materials.append(material)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    return ob

def add_box(name, size, loc, material, rot=(0, 0, 0), smooth=False):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(material)
    return ob

def add_cyl(name, r, depth, loc, material, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(material)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob

def edge_split(objs, angle=52):
    for ob in objs:
        bpy.context.view_layer.objects.active = ob
        m = ob.modifiers.new("es", "EDGE_SPLIT")
        m.split_angle = math.radians(angle)
        bpy.ops.object.modifier_apply(modifier=m.name)

# ------------------------------------------------------------------ body
# y, half width, floor, shoulder height
BODY = [
    ( 2.15, 0.46, 0.30, 0.44),
    ( 2.02, 0.74, 0.24, 0.50),
    ( 1.80, 0.89, 0.18, 0.58),
    ( 1.45, 0.94, 0.15, 0.66),
    ( 1.05, 0.95, 0.14, 0.72),
    ( 0.62, 0.95, 0.14, 0.77),
    ( 0.20, 0.94, 0.14, 0.81),
    (-0.30, 0.93, 0.14, 0.82),
    (-0.85, 0.93, 0.14, 0.80),
    (-1.35, 0.94, 0.15, 0.75),
    (-1.80, 0.92, 0.18, 0.68),
    (-2.05, 0.87, 0.24, 0.62),
    (-2.16, 0.78, 0.30, 0.58),
]
body = loft("arrow_body", resample(BODY, 26), M_PAINT)

# greenhouse: long raked screen, short roof, fastback. Low, not a box.
CAB = [
    ( 0.78, 0.72, 0.74, 0.79),
    ( 0.34, 0.68, 0.75, 0.92),
    ( 0.02, 0.66, 0.75, 1.01),
    (-0.48, 0.65, 0.75, 1.03),
    (-0.86, 0.62, 0.74, 0.96),
    (-1.12, 0.58, 0.72, 0.84),
]
cab = loft("arrow_cabin", resample(CAB, 14), M_GLASS, n_ring=16)
add_box("arrow_roof", (1.16, 0.52, 0.035), (0, -0.24, 1.035), M_PAINT)
edge_split([body, cab], 46)

# ------------------------------------------------------------------ wheels
WHEEL_R = 0.37
for sx in (-1, 1):
    for sy in (1.45, -1.47):
        add_cyl("tyre", WHEEL_R, 0.26, (sx * 0.905, sy, WHEEL_R), M_TYRE, rot=(0, math.pi / 2, 0), verts=28)
        add_cyl("hub", 0.225, 0.275, (sx * 0.905, sy, WHEEL_R), M_RIM, rot=(0, math.pi / 2, 0), verts=22)
        add_cyl("hub_cap", 0.07, 0.30, (sx * 0.905, sy, WHEEL_R), M_TRIM, rot=(0, math.pi / 2, 0), verts=12)
        # arch lip
        bpy.ops.mesh.primitive_torus_add(major_radius=0.435, minor_radius=0.030,
                                        location=(sx * 0.93, sy, WHEEL_R + 0.01),
                                        rotation=(0, math.pi / 2, 0),
                                        major_segments=24, minor_segments=8)
        a = bpy.context.object
        a.name = "arch"
        a.data.materials.append(M_TRIM)

# ------------------------------------------------------------------ details
add_box("splitter",   (1.74, 0.26, 0.045), (0, 2.02, 0.27), M_TRIM)
add_box("tail_panel", (1.68, 0.07, 0.24),  (0, -2.16, 0.60), M_TRIM)
for sx in (-1, 1):
    add_box("tail_light", (0.54, 0.035, 0.07), (sx * 0.55, -2.195, 0.62), M_TAIL)
    add_box("lamp_recess", (0.44, 0.16, 0.045), (sx * 0.54, 1.90, 0.53), M_TRIM)
    add_box("lamp_face",   (0.36, 0.025, 0.07), (sx * 0.54, 1.99, 0.53), M_LAMP)
    add_box("sill",        (0.035, 2.10, 0.045), (sx * 0.945, 0.02, 0.235), M_SILL)
    add_box("mirror_stalk",(0.09, 0.035, 0.03), (sx * 0.94, 0.56, 0.80), M_TRIM)
    add_box("mirror",      (0.13, 0.05, 0.04),  (sx * 1.00, 0.56, 0.81), M_TRIM)
    add_box("rail",        (0.028, 0.50, 0.028), (sx * 0.26, -0.86, 1.012), M_TRIM)
add_box("grille", (1.30, 0.05, 0.13), (0, 2.12, 0.40), M_TRIM)

# ------------------------------------------------------------------ dish
def paraboloid(name, r_max, depth, loc, material, segs=32, rings=6):
    verts = [(0.0, 0.0, 0.0)]
    for i in range(1, rings + 1):
        r = r_max * i / rings
        z = depth * (r / r_max) ** 2
        for k in range(segs):
            a = 2 * math.pi * k / segs
            verts.append((r * math.cos(a), r * math.sin(a), z))
    faces = []
    for k in range(segs):
        faces.append((0, 1 + k, 1 + (k + 1) % segs))
    for i in range(rings - 1):
        a = 1 + i * segs
        b = 1 + (i + 1) * segs
        for k in range(segs):
            k2 = (k + 1) % segs
            faces.append((a + k, b + k, b + k2, a + k2))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    me.materials.append(material)
    ob.location = loc
    for p in me.polygons:
        p.use_smooth = True
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    ob.rotation_euler = (math.radians(66), 0, 0)
    return ob

paraboloid("dish", 0.48, 0.115, (0, -1.02, 1.78), M_DISH)
add_cyl("dish_post", 0.042, 0.50, (0, -1.02, 1.50), M_TRIM, verts=12)
add_cyl("dish_yoke", 0.075, 0.10, (0, -1.02, 1.69), M_TRIM, rot=(math.radians(66), 0, 0), verts=12)
add_cyl("feed", 0.05, 0.09, (0, -0.83, 1.87), M_TRIM, rot=(math.radians(66), 0, 0), verts=10)
for ang in (0.4, 2.5, 4.6):
    x = 0.40 * math.cos(ang)
    add_cyl("strut", 0.009, 0.46, (x * 0.62, -0.92, 1.83), M_TRIM,
            rot=(math.radians(64), 0, math.radians(20)), verts=6)

# ------------------------------------------------------------------ export
meshes = [o for o in sc.objects if o.type == "MESH"]
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = body
os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", use_selection=True,
                          export_apply=True, export_yup=True)
print("GLB:", OUT_GLB, os.path.getsize(OUT_GLB), "bytes", "tris:", sum(len(o.data.polygons) for o in meshes))

# ------------------------------------------------------------------ previews
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.render.film_transparent = False
w = bpy.data.worlds.new("w"); sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.045, 0.05, 0.06, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0

# key + rim so the form reads, not a flat clay
for (loc, energy, size) in [((6, -7, 6), 2600, 6), ((-7, 5, 4), 900, 8), ((0, 0, 9), 400, 10)]:
    bpy.ops.object.light_add(type="AREA", location=loc)
    L = bpy.context.object
    L.data.energy = energy
    L.data.size = size
    L.rotation_euler = (0, 0, 0)
    d = Vector((0, 0, 0.6)) - L.location
    L.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
cam_data.lens = 70

def shoot(loc, path):
    cam.location = loc
    d = Vector((0, 0, 0.62)) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("shot:", path)

for engine, tag in (("BLENDER_EEVEE_NEXT", "eevee"), ("BLENDER_WORKBENCH", "wb")):
    try:
        sc.render.engine = engine
        if engine == "BLENDER_WORKBENCH":
            sh = sc.display.shading
            sh.light, sh.color_type = "STUDIO", "MATERIAL"
            sh.show_shadows = sh.show_cavity = True
        sc.eevee.taa_render_samples = 32 if engine == "BLENDER_EEVEE_NEXT" else 1
        shoot((4.9, 6.6, 2.3), "/tmp/arrow_front_%s.png" % tag)
        shoot((-5.2, -6.4, 2.4), "/tmp/arrow_rear_%s.png" % tag)
        print("engine ok:", engine)
        break
    except Exception:
        traceback.print_exc()
