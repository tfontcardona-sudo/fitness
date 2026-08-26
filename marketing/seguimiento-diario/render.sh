#!/bin/sh
# Renderiza las piezas de la campaña con Chromium headless.
# Uso: ./render.sh [pieza...]   (sin argumentos: todas las fuentes/*.html)
set -e
CHROME="${CHROME:-/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell}"
cd "$(dirname "$0")"
for f in ${*:-fuentes/p*.html}; do
  b=$(basename "$f" .html)
  case "$b" in *story*) SIZE=1080,1920;; *) SIZE=1080,1350;; esac
  "$CHROME" --no-sandbox --hide-scrollbars --window-size=$SIZE \
    --screenshot="$b.png" "file://$(pwd)/$f" 2>/dev/null
  echo "✔ $b.png"
done
