# Assembly animation

20-second silent orbit, exploded view and reassembly using the original STEP geometry. The nine screws and nine inserts are separate modeled parts.

```sh
npm ci
npm run dev
npm run check
npm run render -- --quality delivery --output ../images/assembly.mp4
./export-media.sh
```

Rebuild the CAD assembly and render meshes from the repository root:

```sh
uv venv --python 3.13
uv pip install --python .venv/bin/python -r scripts/requirements.txt
.venv/bin/python scripts/export_assembly.py
```

Hardware geometry is illustrative: M4×10 shafts, Ø7×4 heads, and Ø5.6×8 inserts with Ø4 bores. Threads and knurling are simplified. Confirm the actual insert's dimensions before fabrication. Rack-mount M6 screws and cage nuts are excluded because no rack rail is modeled.

Animation timing and camera are in `scene.js`. Model parts remain in their original assembly coordinates; animation only translates them. `cad/assembly_with_hardware.step` is the supplementary hardware assembly. Printable files and the parametric rack remain unchanged.
