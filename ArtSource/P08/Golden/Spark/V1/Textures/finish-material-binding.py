"""Staged helper, NOT run by the texture author. No scene change on import.

Parent usage in Blender, after every PNG and the manifest are fully saved:
    exec(Path(".../Textures/finish-material-binding.py").read_text())
    bind_spark_finish_materials(Path(".../Textures"))
Run before packing. This deliberately loads new image datablocks, sets their
colour space and reloads from disk. It never touches Spark_Copper or geometry.
"""
import hashlib
import json
from pathlib import Path


def bind_spark_finish_materials(texture_dir, uv_map_name="UV0_SurfaceMetres"):
    import bpy
    texture_dir = Path(texture_dir)
    intent = json.loads((texture_dir / "finish-surface-intent.json").read_text())
    entries = intent["finishes"]
    if len(entries) != 10 or any(item["material"] == "Spark_Copper" for item in entries):
        raise RuntimeError("Unexpected finish binding scope")
    # Verify the whole staged set before changing any material.
    for entry in entries:
        material = bpy.data.materials.get(entry["material"])
        if not material or not material.use_nodes:
            raise RuntimeError("Missing existing material: " + entry["material"])
        if not any(node.type == 'BSDF_PRINCIPLED' for node in material.node_tree.nodes):
            raise RuntimeError("Missing Principled shader: " + entry["material"])
        for artifact in entry["maps"].values():
            path = texture_dir / Path(artifact["path"]).name
            if hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
                raise RuntimeError("Stale or incomplete texture: " + str(path))
    bound = []
    for entry in entries:
        material = bpy.data.materials[entry["material"]]
        tree = material.node_tree
        shader = next(node for node in tree.nodes if node.type == 'BSDF_PRINCIPLED')
        for node in list(tree.nodes):
            if node.get("sparkFinishBinding", False):
                tree.nodes.remove(node)

        def node(kind, name):
            result = tree.nodes.new(kind)
            result.name = name
            result.label = name
            result["sparkFinishBinding"] = True
            return result

        uv = node('ShaderNodeUVMap', 'Spark finish authored UV')
        uv.uv_map = uv_map_name
        uv.location = (-1000, 0)
        scale = node('ShaderNodeVectorMath', 'Spark finish metric repeat')
        scale.operation = 'SCALE'
        scale.inputs['Scale'].default_value = entry['uvScale']
        scale.location = (-800, 0)
        tree.links.new(uv.outputs['UV'], scale.inputs[0])
        textures = {}
        for index, (role, artifact) in enumerate(entry['maps'].items()):
            path = texture_dir / Path(artifact['path']).name
            image = bpy.data.images.load(str(path), check_existing=False)
            image.colorspace_settings.name = 'sRGB' if artifact['encoding'] == 'sRGB' else 'Non-Color'
            image.alpha_mode = 'CHANNEL_PACKED' if role == 'metallicSmoothness' else 'NONE'
            image.reload()
            texture = node('ShaderNodeTexImage', 'Spark finish ' + role)
            texture.image = image
            texture.interpolation = 'Linear'
            texture.extension = 'REPEAT'
            texture.location = (-560, 330 - 230 * index)
            tree.links.new(scale.outputs['Vector'], texture.inputs['Vector'])
            textures[role] = texture
        tree.links.new(textures['baseColor'].outputs['Color'], shader.inputs['Base Color'])
        channels = node('ShaderNodeSeparateColor', 'Spark R metallic')
        channels.mode = 'RGB'
        channels.location = (-200, -130)
        tree.links.new(textures['metallicSmoothness'].outputs['Color'], channels.inputs['Color'])
        tree.links.new(channels.outputs['Red'], shader.inputs['Metallic'])
        tree.links.new(textures['roughness'].outputs['Color'], shader.inputs['Roughness'])
        normal = node('ShaderNodeNormalMap', 'Spark tangent normal +Y')
        normal.space = 'TANGENT'
        normal.uv_map = uv_map_name
        normal.inputs['Strength'].default_value = 1
        normal.location = (-200, -390)
        tree.links.new(textures['normal'].outputs['Color'], normal.inputs['Color'])
        tree.links.new(normal.outputs['Normal'], shader.inputs['Normal'])
        if 'emission' in textures:
            tree.links.new(textures['emission'].outputs['Color'], shader.inputs['Emission Color'])
            shader.inputs['Emission Strength'].default_value = entry['emissionStrengthBlender']
        material['sparkFinishIntent'] = entry['intent']
        material['sparkFinishVisualAccepted'] = False
        material['sparkFinishBindingVersion'] = 1
        bound.append(entry['material'])
    return {'boundMaterials': bound, 'imagesLoadedFreshAndReloaded': True,
            'copperTouched': False, 'visualAccepted': False}
