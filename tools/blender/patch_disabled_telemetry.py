"""Fix the pinned source checkout's status endpoint only when telemetry is disabled.

Upstream omits its generated config module from Git. This bypasses telemetry
initialization on the disabled path; safe-mode and Blender tools stay unchanged.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
path = root / "_local/blender-mcp/src/blender_mcp/server.py"
text = path.read_text(encoding="utf-8")
changes = {
    '"telemetry_consent": get_telemetry().check_user_consent(),':
    '"telemetry_consent": False if os.getenv("BLENDER_MCP_DISABLE_TELEMETRY") == "true" else get_telemetry().check_user_consent(),',
    'return json.dumps(payload, indent=2) + await maybe_prompt_for_consent(ctx)':
    'return json.dumps(payload, indent=2) + ("" if os.getenv("BLENDER_MCP_DISABLE_TELEMETRY") == "true" else await maybe_prompt_for_consent(ctx))',
}
for old, new in changes.items():
    if new in text:
        continue
    if text.count(old) != 1:
        raise RuntimeError("Pinned upstream source does not match expected compatibility patch")
    text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("Disabled-telemetry compatibility patch ready")
