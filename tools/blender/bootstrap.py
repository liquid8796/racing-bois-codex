"""Start the pinned local Blender addon in a fresh task-owned Blender session."""
import importlib.util
import pathlib
import sys
import argparse
import bpy

project = pathlib.Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=9876)
options = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
if not 1024 <= options.port <= 65535:
    raise ValueError("Task Blender port must be between1024 and65535")
source = project / "_local/blender-mcp/addon.py"
spec = importlib.util.spec_from_file_location("racing_bois_blender_mcp", source)
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
addon.register()
bpy.context.scene.blendermcp_auto_start_server = False
server = addon.BlenderMCPServer(host="127.0.0.1", port=options.port)
server.start()
bpy.types.RacingBoisMCPServer = server
print("RACING_BOIS_BLENDER_READY", bpy.app.version_string, options.port, flush=True)
