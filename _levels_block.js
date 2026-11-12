// ---------------------------------------------------------------- levels
// A level is one place, one mode and one route. Some levels are walking, some
// are driving. Everything downstream (reset, markers, finish, the HUD) asks the
// level rather than hard coding a route, so adding the next one is data only.

var TRACK_MATS = [];          // road materials, textured once the scans load

function buildDesertCircuit(){
  // A loop out of the yard to the south, across open ground, and back. The
  // shape is quoted in the concept art: one long road, poles on one side,
  // mesas on the horizon, nothing to hit.
  var spine = [
    [   6, 30], [   0, 100], [ -28, 165], [ -66, 225], [ -60, 305],
    [  -6, 352], [  64, 360], [ 128, 332], [ 160, 262], [ 162, 176],
    [ 132, 106], [  84,  56], [  42,  30], [  14, 26]
  ];
  var curve = new THREE.CatmullRomCurve3(
    spine.map(function(p){ return new THREE.Vector3(p[0], 0, p[1]); }), true, 'catmullrom', 0.5);

  var SEG = 420;
  var pts = curve.getPoints(SEG);
  var g = new THREE.Group();
  g.name = 'circuit';

  // cumulative distance, so the road texture tiles with the ground speed
  var dist = [0];
  for (var i = 1; i < pts.length; i++) dist.push(dist[i-1] + pts[i].distanceTo(pts[i-1]));
  var total = dist[dist.length-1] + pts[pts.length-1].distanceTo(pts[0]);

  function ribbon(halfW, y, uRep){
    var pos = [], uv = [], idx = [];
    for (var i = 0; i < pts.length; i++){
      var p = pts[i], q = pts[(i+1) % pts.length];
      var tx = q.x - p.x, tz = q.z - p.z, L = Math.hypot(tx, tz) || 1;
      var sx = -tz / L, sz = tx / L;                 // left of travel
      pos.push(p.x + sx*halfW, y, p.z + sz*halfW);
      pos.push(p.x - sx*halfW, y, p.z - sz*halfW);
      uv.push(0, dist[i]/4, uRep, dist[i]/4);
      if (i > 0){
        var a = (i-1)*2, b = a+1, c2 = i*2, d = c2+1;
        idx.push(a, c2, b, b, c2, d);
      }
    }
    var geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    geo.setIndex(idx);
    // flat ground, so every normal is up. Winding on a ribbon is easy to get
    // backwards and a road lit from underneath looks like a hole.
    var nrm = new Float32Array(pos.length);
    for (var k = 1; k < nrm.length; k += 3) nrm[k] = 1;
    geo.setAttribute('normal', new THREE.BufferAttribute(nrm, 3));
    return geo;
  }

  var shoulderMat = new THREE.MeshStandardMaterial({color:0x8a7355, roughness:0.98, metalness:0.0});
  var roadMat     = new THREE.MeshStandardMaterial({color:0x9a9a96, roughness:0.95, metalness:0.0});
  TRACK_MATS.push({mat: shoulderMat, kind:'shoulder'}, {mat: roadMat, kind:'road'});

  var shoulder = new THREE.Mesh(ribbon(9.0, 0.01, 4.5), shoulderMat);
  shoulder.receiveShadow = true;
  g.add(shoulder);
  var road = new THREE.Mesh(ribbon(4.0, 0.03, 2.0), roadMat);
  road.receiveShadow = true;
  g.add(road);

  // centre dashes, every 14 m, 3 m long, faded
  (function(){
    var pos = [], idx = [], n = 0;
    var step = 14;
    for (var d = 20; d < total - 10; d += step){
      var u = d / total;
      var p0 = curve.getPointAt(Math.max(0, Math.min(0.9999, u)));
      var p1 = curve.getPointAt(Math.max(0, Math.min(0.9999, (d + 3) / total)));
      var tx = p1.x - p0.x, tz = p1.z - p0.z, L = Math.hypot(tx, tz) || 1;
      var sx = -tz / L * 0.14, sz = tx / L * 0.14;
      pos.push(p0.x + sx, 0.05, p0.z + sz,  p0.x - sx, 0.05, p0.z - sz,
               p1.x + sx, 0.05, p1.z + sz,  p1.x - sx, 0.05, p1.z - sz);
      idx.push(n, n+2, n+1, n+1, n+2, n+3);
      n += 4;
    }
    var geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geo.setIndex(idx);
    var nrm = new Float32Array(pos.length);
    for (var k = 1; k < nrm.length; k += 3) nrm[k] = 1;
    geo.setAttribute('normal', new THREE.BufferAttribute(nrm, 3));
    var m = new THREE.MeshStandardMaterial({color:0xbcb49c, roughness:0.88, metalness:0.0});
    var mesh = new THREE.Mesh(geo, m);
    g.add(mesh);
  })();

  // poles and wires, one side of the road, every 45 m
  (function(){
    var poleMat = new THREE.MeshStandardMaterial({color:0x4a3a2a, roughness:0.92, metalness:0.0});
    var poleGeo = new THREE.BoxGeometry(0.20, 9.2, 0.20);
    var armGeo  = new THREE.BoxGeometry(2.3, 0.13, 0.13);
    var tops = [];
    for (var d = 30; d < total - 5; d += 45){
      var u = d / total;
      var p = curve.getPointAt(Math.min(0.9999, u));
      var p2 = curve.getPointAt(Math.min(0.9999, u + 0.004));
      var tx = p2.x - p.x, tz = p2.z - p.z, L = Math.hypot(tx, tz) || 1;
      var sx = -tz / L, sz = tx / L;
      var px = p.x + sx * 12.5, pz = p.z + sz * 12.5;
      var pole = new THREE.Mesh(poleGeo, poleMat);
      pole.position.set(px, 4.6, pz);
      pole.castShadow = true;
      g.add(pole);
      var arm = new THREE.Mesh(armGeo, poleMat);
      arm.position.set(px, 8.6, pz);
      arm.rotation.y = Math.atan2(tx, tz);
      g.add(arm);
      tops.push(new THREE.Vector3(px, 8.55, pz));
    }
    // sagging wire between consecutive poles
    var wmat = new THREE.LineBasicMaterial({color:0x1a1614});
    for (var i = 1; i < tops.length; i++){
      var a = tops[i-1], b = tops[i];
      if (a.distanceTo(b) > 60) continue;
      var verts = [];
      for (var s = 0; s <= 10; s++){
        var t = s / 10;
        verts.push(
          a.x + (b.x - a.x) * t,
          a.y + (b.y - a.y) * t - Math.sin(t * Math.PI) * 1.1,
          a.z + (b.z - a.z) * t);
      }
      var geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
      g.add(new THREE.Line(geo, wmat));
    }
  })();

  // mesas on the horizon. Fog does most of the work, these just give the
  // horizon a silhouette instead of a straight line.
  (function(){
    var mat = new THREE.MeshStandardMaterial({color:0x6b4a38, roughness:0.96, metalness:0.0, flatShading:true});
    var spots = [[-420, 120, 95, 46], [-260, -240, 120, 38], [180, -300, 140, 52],
                 [430, 60, 110, 40], [380, 420, 130, 44], [-380, 400, 100, 34],
                 [-60, 520, 150, 50], [520, 300, 90, 36]];
    spots.forEach(function(s){
      var m = new THREE.Mesh(new THREE.CylinderGeometry(s[2]*0.55, s[2], s[3], 6, 1), mat);
      m.position.set(s[0], s[3]/2 - 4, s[1]);
      m.rotation.y = s[0] * 0.01;
      g.add(m);
    });
  })();

  scene.add(g);

  // gates along the loop, placed by distance so they sit on the road
  var rings = [];
  [0.14, 0.31, 0.48, 0.65, 0.82].forEach(function(u, i){
    var p = curve.getPointAt(u);
    var p2 = curve.getPointAt(Math.min(0.9999, u + 0.004));
    rings.push({ x:+p.x.toFixed(2), y:0.03, z:+p.z.toFixed(2),
                 label:'GATE ' + (i+1), yaw: Math.atan2(p2.x - p.x, p2.z - p.z) });
  });
  return rings;
}

var DESERT_GATES = buildDesertCircuit();

LEVELS.desert = {
  id: 'desert', name: 'THE LONG ROAD',
  mode: 'car', startInCar: true,
  route: [{x:6, y:0.02, z:22, label:'START', yaw:Math.PI}].concat(DESERT_GATES),
  finish: {x:6, y:0.0, z:22}
};

LEVELS.yard = {
  id: 'yard', name: 'THE YARD',
  mode: 'foot', startInCar: false,
  route: CHECKPOINTS,
  finish: FINISH
};

var LEVEL = LEVELS.desert;

function routeList(){ return LEVEL.route; }
function finishPoint(){ return LEVEL.finish; }

// markers for the current level. The car markers need to be seen at 60 km/h.
var MARKER_GROUP = new THREE.Group();
scene.add(MARKER_GROUP);
(function(){
  // painted, not glowing: an unlit 0xffb038 ring sits above the bloom threshold
  // and smears across the frame at sunset. This is bright enough to find and
  // dim enough to stay a marking on the floor.
  var ringMat = new THREE.MeshStandardMaterial({color:0x3a2a10, emissive:0xd08a28,
                                                emissiveIntensity:0.55, roughness:0.55, metalness:0.1});
  routeList().slice(1).concat([finishPoint()]).forEach(function(c){
    var r = new THREE.Mesh(new THREE.TorusGeometry(3.4, 0.09, 6, 30), ringMat);
    r.rotation.x = -Math.PI/2;
    r.position.set(c.x, (c.y || 0) + 0.07, c.z);
    MARKER_GROUP.add(r);
    var l = new THREE.PointLight(0xffa030, 1.2, 12, 2);
    l.position.set(c.x, (c.y || 0) + 0.9, c.z);
    MARKER_GROUP.add(l);
  });
})();
