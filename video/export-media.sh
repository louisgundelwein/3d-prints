#!/usr/bin/env bash
set -euo pipefail

# Build the README preview from the approved delivery render.
video_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
movie="$video_dir/../images/assembly.mp4"
test -s "$movie"
ffmpeg -hide_banner -loglevel error -y -i "$movie" \
  -filter_complex '[0:v]fps=10,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3' \
  -loop 0 "$video_dir/../images/assembly-preview.gif"
