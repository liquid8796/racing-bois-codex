"""Read-only ordinary-Python preflight before sending the literal bpy snippet.

This is NOT Blender MCP code. It reads and validates files, statically checks
the staged snippet, and prints its SHA256. It never imports/executes bpy and
never changes the manifest, PNGs, scene or runtime sources.
"""
import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FOLDER = ROOT / 'ArtSource/P08/Golden/Spark/V1/Textures'
MANIFEST_SHA256 = '8eed5c04871350a5212452917ae1efa1322a4a8128aa65028a099b655b4fca52'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = FOLDER / 'finish-surface-intent.json'
    if sha(manifest_path) != MANIFEST_SHA256:
        raise RuntimeError('Locked finish manifest changed')
    manifest = json.loads(manifest_path.read_text())
    for relative, expected in manifest['lockedReferences'].items():
        if sha(ROOT / relative) != expected:
            raise RuntimeError('Locked concept changed: ' + relative)
    for entry in manifest['finishes']:
        for artifact in entry['maps'].values():
            if sha(ROOT / artifact['path']) != artifact['sha256']:
                raise RuntimeError('Texture changed: ' + artifact['path'])
    for artifact in (manifest['authoringScript'], manifest['bindingSnippet']):
        if sha(ROOT / artifact['path']) != artifact['sha256']:
            raise RuntimeError('Original manifest dependency changed: ' + artifact['path'])

    snippet_path = FOLDER / 'finish-material-binding-mcp.py'
    source = snippet_path.read_text(encoding='utf-8')
    tree = ast.parse(source, filename=str(snippet_path))
    compile(tree, str(snippet_path), 'exec')  # Syntax only. Never execute.
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = ast.literal_eval(node.value)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            raise RuntimeError('MCP snippet must not use from-imports')
        if isinstance(node, ast.Import) and [item.name for item in node.names] != ['bpy']:
            raise RuntimeError('MCP snippet may only import bpy')
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {'open', 'exec', 'eval', '__import__', 'compile'}:
                raise RuntimeError('Forbidden MCP Python entry point: ' + node.func.id)
        if isinstance(node, ast.Name) and node.id in {'pathlib', 'hashlib', 'importlib'}:
            raise RuntimeError('Forbidden MCP filesystem/import helper: ' + node.id)
        if isinstance(node, ast.Constant) and node.value in ('ShaderNodeMapping', 'ShaderNodeVectorMath'):
            raise RuntimeError('UV factors must be baked in mesh loops, never shader nodes')
    expected = tuple(
        (entry['material'], entry['uvScale'], entry['emissionStrengthBlender'],
         tuple((role, Path(artifact['path']).name,
                'sRGB' if artifact['encoding'] == 'sRGB' else 'Non-Color')
               for role, artifact in entry['maps'].items()))
        for entry in manifest['finishes'])
    if constants['FINISH_BINDINGS'] != expected:
        raise RuntimeError('MCP literal bindings differ from finalized manifest')
    if constants['MANIFEST_SHA256'] != MANIFEST_SHA256:
        raise RuntimeError('MCP manifest identity mismatch')
    if Path(constants['TEXTURE_DIRECTORY']).resolve() != FOLDER.resolve():
        raise RuntimeError('MCP texture directory points elsewhere')
    if constants['UV_LAYER'] != 'UV0_SurfaceMetres' or constants['SOURCE_ROOT'] != 'RB_Golden_Spark_v1':
        raise RuntimeError('Unexpected source UV/root target')
    print(json.dumps({
        'passed': True, 'manifestSha256': MANIFEST_SHA256,
        'verifiedPngCount': manifest['pngCount'], 'literalBindingsMatchManifest': True,
        'allowedImportOnlyBpy': True, 'syntaxCompiledOnly': True,
        'sceneCodeExecuted': False, 'sourceUvMutationOccursOnlyWhenParentSendsSnippet': True,
        'snippetPath': snippet_path.relative_to(ROOT).as_posix(),
        'snippetSha256': sha(snippet_path), 'snippetBytes': snippet_path.stat().st_size,
        'visualAccepted': False,
    }, indent=2))


if __name__ == '__main__':
    main()
