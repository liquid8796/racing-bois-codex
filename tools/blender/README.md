# Blender MCP authoring pipeline

The task uses the real MCP stdio protocol (`initialize`, `tools/list`, `tools/call`) to a pinned Blender MCP server, which connects to a task-owned Blender session at `127.0.0.1:9876`. It is not a simulated MCP response or direct headless export being mislabeled as MCP.

Setup on this Windows machine:

```powershell
.\tools\blender\prepare.ps1
.\tools\blender\start-blender.ps1
& .\_local\blender-env\Scripts\python.exe tools\blender\mcp_client.py get_addon_status --receipt docs\p02\blender\handshake.json
& .\_local\blender-env\Scripts\python.exe tools\blender\mcp_client.py get_scene_info --receipt docs\p02\blender\scene-before.json
```

`start-blender.ps1` defaults to installed Blender 5.2 (observed runtime 5.2.1 LTS). Pass `-BlenderExe` on another machine. A bridge already listening on 9876 is left alone; reuse it instead of starting another.

Upstream: [ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender), commit `6f992ffbca3cb715d111fc640b737b808632273c`, package 2.0.0; Python dependencies pinned in `requirements.lock`. Source checkout and venv live under ignored `_local/`. A small reproducible patch prevents the status endpoint from importing an omitted generated telemetry module when telemetry is explicitly disabled. Safe-mode stays enabled. No asset marketplace or generative service is used.

The script `create_barrier.py` creates the entire **new** barrier scene; it clears the current task-owned Blender scene, so only run it in that dedicated scene. It produces `.blend` authoring source in `ArtSource/Props`, FBX/maps in `Assets/RacingBois/Art/Props/Barrier` and a studio render in `docs/p02/blender`. It never loads original-game files.

```powershell
& .\_local\blender-env\Scripts\python.exe tools\blender\mcp_client.py execute_blender_code --code-file tools\blender\create_barrier.py --receipt docs\p02\blender\creation-receipt.json
```

[Independent Blender QA](../../docs/p02/assetqa/REPORT.md) checks all LOD meshes and UV triangles; Unity importer/prefab checks live in `FoundationBuilder.Validate`. ArtSource remains separate from Unity so Unity does not invoke Blender implicitly when importing the production FBX.

The source file preserves the studio review scene. The production prefab contains only the barrier meshes/materials/LOD/primitive collider; studio lights and camera are excluded from the FBX selection.
