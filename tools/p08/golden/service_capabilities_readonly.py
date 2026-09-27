"""Read direct Blender MCP generation configuration without exposing credentials.

No service request, preference change, upload, download, or generation occurs.
"""
import bpy, json

scene = bpy.context.scene
server = bpy.types.RacingBoisMCPServer
result = {
    'blender_version': bpy.app.version_string,
    'scene_file': bpy.data.filepath,
    'objects': [{'name': o.name, 'type': o.type} for o in scene.objects],
    'services': {
        'hyper3d_rodin': {
            'enabled': bool(scene.blendermcp_use_hyper3d),
            'mode': scene.blendermcp_hyper3d_mode,
            'credential_present': bool(server._get_hyper3d_api_key()),
        },
        'hunyuan3d': {
            'enabled': bool(scene.blendermcp_use_hunyuan3d),
            'mode': scene.blendermcp_hunyuan3d_mode,
            'secret_id_present': bool(server._get_hunyuan3d_secret_id()),
            'secret_key_present': bool(server._get_hunyuan3d_secret_key()),
            'local_api_configured_explicitly': bool(getattr(scene, 'blendermcp_hunyuan3d_api_url', '')),
        },
        'sketchfab': {
            'enabled': bool(scene.blendermcp_use_sketchfab),
            'credential_present': bool(server._get_sketchfab_api_key()),
        },
        'polyhaven': {'enabled': bool(scene.blendermcp_use_polyhaven)},
    },
    'external_requests_performed': False,
}
print(json.dumps(result, ensure_ascii=False))
