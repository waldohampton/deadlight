# DEADLIGHT

First-person chase game. You wake up in a concrete maze. Something is in there with
you and it knows roughly where you are. Find the lit EXIT door, go through it, get a
bigger maze and a faster thing.

No assets, no build step. Two files: `index.html` and `three.min.js` (r128, MIT).

## Run it

```
cd ~/repos/deadlight
python3 -m http.server 8123
```

Then open http://localhost:8123 (WSL forwards localhost to Windows).

Double-clicking `index.html` also works in most browsers, but a local server is the
reliable path.

## Controls

Desktop
- WASD or arrows: move
- Mouse: look (click the view once to capture the cursor, Esc releases)
- Shift: run

Phone
- Left half: drag to move (the stick appears where you press)
- Right half: drag to look
- Push the stick past about 85%: run
- TILT button (bottom right): steer by tilting the phone instead of the stick

## The rules

- Walking is quiet and slow. Running is fast and loud, and it hears you.
- Breath is your sprint budget. Run out and you are down to a walk while it closes.
- The EXIT distance readout is top right. The green door is the only lit thing that
  is not your torch.
- Each sector is bigger and the thing is faster.

## How it is built

- Maze: recursive backtracker with a few walls knocked out for loops.
- Walls and floor: procedurally drawn canvas textures, one instanced box mesh.
- Light: camera spotlight, flickering ceiling lamps, distance fog. No shadow maps.
- Audio: WebAudio only. Drone + heartbeat are driven by how close it is.
- Chaser: BFS on the maze graph every 350ms, walks cell centre to cell centre.
- Frame budget: render scale drops from 2x to 1x if 90 frames average worse than 43fps.

## Known limits

- Stylized concrete, not photoreal. Cinematic is the fog, grain, torch and sound
  design, not textures.
- The thing pathfinds, it does not see. It always knows your cell.
- No jump, crouch, doors or keys yet.
