# Review dash ( Blender review room for oddhobb output )

Node 22, zero npm deps. Serves the image gallery, a Three.js 3D room,
Blender job queue (QC / render / repair via headless Blender scripts
in freaktown), verdict store, Blender-docs lookup, and an MCP
endpoint so agents (pi 3D tools included) can drive it.

Run: `PORT=8809 node review/server.mjs` (live behind
https://review.oddhobb.com via the figgsite tunnel).

Paths assume this box: Blender at
`/home/ubuntu/blender-5.0.1-linux-x64/blender`, scripts in
`/home/ubuntu/freaktown/scripts`, GLB symlinks under `review/models/`
point at R2-cached meshes. `review/data/` (jobs, verdicts) and
`review/shots/` are runtime state — jobs ledger is committed history,
shots are symlinks to regenerable outputs.
