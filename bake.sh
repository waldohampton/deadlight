#!/usr/bin/env bash
# Bake the test room's global illumination to lightmaps, then export the GLB.
# Usage: ./bake.sh [res] [samples]
set -e
cd "$(dirname "$0")"

BLENDER="$HOME/opt/blender-4.2.9-linux-x64/blender"
LIBS="$HOME/opt/xlibs/usr/lib/x86_64-linux-gnu"

if [ ! -x "$BLENDER" ]; then
  echo "Blender not installed. See BAKE.md" >&2
  exit 1
fi

export BAKE_RES="${1:-512}"
export BAKE_SAMPLES="${2:-48}"

echo "baking at ${BAKE_RES}px / ${BAKE_SAMPLES} samples"
LD_LIBRARY_PATH="$LIBS" "$BLENDER" -b -noaudio -P bake_scene.py \
  | grep -E "BAKED|DONE|Error|Traceback" || true

echo "lightmaps -> $(pwd)/bake"
