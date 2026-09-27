"""Use real MCP stdio initialize/tools/call against the pinned Blender MCP server."""
from __future__ import annotations
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from result_status import execution_failure

PROJECT = Path(__file__).resolve().parents[2]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tool", choices=["get_addon_status", "get_scene_info", "get_object_info", "execute_blender_code", "get_viewport_screenshot"])
    parser.add_argument("--code-file", type=Path)
    parser.add_argument("--object-name")
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--user-prompt", default="ok hãy hoàn thiện tất cả các phase từ P08 tới P10 nhé, làm cho tới khi nào xong, ko cần dừng lại giữa chừng.")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Task Blender port must be between1024 and65535")
    environment = dict(os.environ)
    environment.update(BLENDER_HOST="127.0.0.1", BLENDER_PORT=str(args.port),
                       BLENDER_MCP_DISABLE_TELEMETRY="true", DISABLE_TELEMETRY="true",
                       BLENDER_MCP_SAFE_MODE="1", PYTHONIOENCODING="utf-8")
    parameters = StdioServerParameters(command=sys.executable,
                                      args=["-m", "blender_mcp.server"], env=environment)
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            initialized = await session.initialize()
            catalog = await session.list_tools()
            arguments = {"user_prompt": args.user_prompt}
            if args.code_file:
                arguments["code"] = args.code_file.read_text(encoding="utf-8-sig")
            if args.object_name:
                arguments["object_name"] = args.object_name
            if args.tool == "get_viewport_screenshot":
                arguments["max_size"] = 1440
            result = await session.call_tool(args.tool, arguments)
            payload = {"protocol": initialized.model_dump(mode="json"),
                       "tool_names": [t.name for t in catalog.tools], "tool": args.tool,
                       "result": result.model_dump(mode="json")}
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            args.receipt.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            for block in result.content:
                if block.type == "text":
                    print(block.text)
                elif block.type == "image":
                    import base64
                    destination = args.receipt.with_suffix(".png")
                    destination.write_bytes(base64.b64decode(block.data))
                    print("Screenshot:", destination)
            failure = execution_failure(payload["result"], args.tool)
            if failure:
                raise RuntimeError(failure)


if __name__ == "__main__":
    asyncio.run(main())
