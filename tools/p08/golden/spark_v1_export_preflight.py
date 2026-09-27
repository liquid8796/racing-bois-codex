"""Load only the isolated Spark candidate and report source state via direct MCP."""
import bpy
import json

assert bpy.data.filepath == '' and set(bpy.data.objects.keys()) == {'Cube', 'Camera', 'Light'}, 'Expected isolated factory-startup session'
bpy.ops.wm.open_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_assembled.blend')
bpy.context.scene.blendermcp_auto_start_server = False
root = bpy.data.objects['RB_Golden_Spark_v1']
print('SPARK_EXPORT_PREFLIGHT=' + json.dumps({
    'file': bpy.data.filepath,
    'objects': [{'name': obj.name, 'type': obj.type, 'parent': obj.parent.name if obj.parent else None,
                 'materials': [m.name if m else None for m in obj.data.materials] if obj.type == 'MESH' else []}
                for obj in [root] + list(root.children_recursive)],
    'materials': [{'name': material.name,
                   'images': [{'name': node.image.name, 'path': node.image.filepath,
                               'size': list(node.image.size), 'colorSpace': node.image.colorspace_settings.name}
                              for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image]}
                  for material in bpy.data.materials if material.name.startswith('Spark_') and material.use_nodes],
    'visualAccepted': False,
}))
