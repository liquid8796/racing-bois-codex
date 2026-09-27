"""Read the MCP envelope and the pinned Blender server's execution status."""


def execution_failure(result, tool):
    if result.get("isError"):
        return "MCP server reported an error"
    if tool != "execute_blender_code":
        return None
    texts = [block.get("text", "").lstrip() for block in result.get("content", [])
             if block.get("type") == "text"]
    for text in texts:
        if text.startswith("Rejected by safe mode"):
            return "Blender safe mode rejected the script; it was not executed"
        if text.startswith(("Error executing code:", "Error executing Python code:")):
            return "Blender reported a Python execution failure"
    if not any(text.startswith("Code executed successfully:") for text in texts):
        return "Blender execution success was not confirmed"
    return None
