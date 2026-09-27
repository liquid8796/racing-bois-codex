# Independent read-only Blender asset QA

Run while the live Blender scene is the authored `RB_RoadBarrier.blend` and the
project Blender MCP bridge is connected on `127.0.0.1:9876`:

```powershell
_local\blender-env\Scripts\python.exe tools/blender/mcp_client.py execute_blender_code --code-file tools/p02/assetqa/inspect_barrier.py --receipt docs/p02/assetqa/barrier-qa-mcp.json
python tools/p02/assetqa/summarize.py
```

`inspect_barrier.py` uses no scene mutation operators or saves. It reads the
current meshes, UVs, image metadata/pixels, transforms and material assignments;
checks every potential positive-area UV triangle intersection; and frees its
detached bmesh copies. Output is returned through MCP, not written by Blender.

`summarize.py` validates the receipt, reopens texture PNGs independently, hashes
the produced files and recipe, and compares hashes to the P00 original manifest.
Different hashes are only a supporting check, never a standalone originality
claim. Pillow is required for this second script.

Unity-specific collider, compression, prefab, lighting and performance checks
are deliberately identified as separate pending evidence in the QA report.
