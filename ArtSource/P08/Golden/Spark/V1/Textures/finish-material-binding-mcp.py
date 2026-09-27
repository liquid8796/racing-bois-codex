"""STAGED ONLY. Parent sends this file's source directly to Blender MCP.

Run the separate normal-Python SHA preflight immediately beforehand. This
snippet performs no Python filesystem reads or custom imports. Executing it
explicitly changes source UV loops/materials and packs freshly reloaded images.
Use BEFORE assembly/LOD creation. Copper is outside the binding and UV scope.
"""
import bpy


MANIFEST_SHA256 = '8eed5c04871350a5212452917ae1efa1322a4a8128aa65028a099b655b4fca52'
TEXTURE_DIRECTORY = 'D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/Textures/'
SOURCE_ROOT = 'RB_Golden_Spark_v1'
UV_LAYER = 'UV0_SurfaceMetres'
BAKE_GUARD = 'sparkFinishUvBakeV1'
UV_GUARD = 'sparkFinishUvCoordinatesV1'
# Exact material, once-only UV factor, emission strength and texture bindings.
# Shader coordinates are always the baked UV directly, with no scale node.
FINISH_BINDINGS = (
    ('Spark_Cream', 1, 0, (
        ('baseColor', 'Spark_Cream_BaseColor.png', 'sRGB'),
        ('normal', 'Spark_Cream_Normal.png', 'Non-Color'),
        ('metallicSmoothness', 'Spark_Cream_MetallicSmoothness.png', 'Non-Color'),
        ('roughness', 'Spark_Cream_Roughness.png', 'Non-Color'))),
    ('Spark_Graphite', 2, 0, (
        ('baseColor', 'Spark_Graphite_BaseColor.png', 'sRGB'),
        ('normal', 'Spark_Graphite_Normal.png', 'Non-Color'),
        ('metallicSmoothness', 'Spark_Graphite_MetallicSmoothness.png', 'Non-Color'),
        ('roughness', 'Spark_Graphite_Roughness.png', 'Non-Color'))),
    ('Spark_Machined', 8, 0, (
        ('baseColor', 'Spark_Machined_BaseColor.png', 'sRGB'),
        ('normal', 'Spark_Machined_Normal.png', 'Non-Color'),
        ('metallicSmoothness', 'Spark_Machined_MetallicSmoothness.png', 'Non-Color'),
        ('roughness', 'Spark_Machined_Roughness.png', 'Non-Color'))),
    ('Spark_SatinSteel', 4, 0, (
        ('baseColor', 'Spark_SatinSteel_BaseColor.png', 'sRGB'),
        ('normal', 'Spark_SatinSteel_Normal.png', 'Non-Color'),
        ('metallicSmoothness', 'Spark_SatinSteel_MetallicSmoothness.png', 'Non-Color'),
        ('roughness', 'Spark_SatinSteel_Roughness.png', 'Non-Color'))),
    ('Spark_Rubber', 2, 0, (
        ('baseColor', 'Spark_Rubber_BaseColor.png', 'sRGB'),
        ('normal', 'Spark_Rubber_Normal.png', 'Non-Color'),
        ('metallicSmoothness', 'Spark_Rubber_MetallicSmoothness.png', 'Non-Color'),
        ('roughness', 'Spark_Rubber_Roughness.png', 'Non-Color'))),
    ('Spark_Leather', 1, 0, (
        ('baseColor', 'Spark_Leather_BaseColor.png', 'sRGB'),
        ('normal', 'Spark_Leather_Normal.png', 'Non-Color'),
        ('metallicSmoothness', 'Spark_Leather_MetallicSmoothness.png', 'Non-Color'),
        ('roughness', 'Spark_Leather_Roughness.png', 'Non-Color'))),
    ('Spark_Lens', 1, 0, (
        ('baseColor', 'Spark_Lens_BaseColor.png', 'sRGB'),
        ('normal', 'Spark_Lens_Normal.png', 'Non-Color'),
        ('metallicSmoothness', 'Spark_Lens_MetallicSmoothness.png', 'Non-Color'),
        ('roughness', 'Spark_Lens_Roughness.png', 'Non-Color'))),
    ('Spark_Lamp', 1, .15, (
        ('baseColor', 'Spark_Lamp_BaseColor.png', 'sRGB'),
        ('normal', 'Spark_Lamp_Normal.png', 'Non-Color'),
        ('metallicSmoothness', 'Spark_Lamp_MetallicSmoothness.png', 'Non-Color'),
        ('roughness', 'Spark_Lamp_Roughness.png', 'Non-Color'),
        ('emission', 'Spark_Lamp_Emission.png', 'sRGB'))),
    ('Spark_Amber', 1, .25, (
        ('baseColor', 'Spark_Amber_BaseColor.png', 'sRGB'),
        ('normal', 'Spark_Amber_Normal.png', 'Non-Color'),
        ('metallicSmoothness', 'Spark_Amber_MetallicSmoothness.png', 'Non-Color'),
        ('roughness', 'Spark_Amber_Roughness.png', 'Non-Color'),
        ('emission', 'Spark_Amber_Emission.png', 'sRGB'))),
    ('Spark_RedLamp', 1, .25, (
        ('baseColor', 'Spark_RedLamp_BaseColor.png', 'sRGB'),
        ('normal', 'Spark_RedLamp_Normal.png', 'Non-Color'),
        ('metallicSmoothness', 'Spark_RedLamp_MetallicSmoothness.png', 'Non-Color'),
        ('roughness', 'Spark_RedLamp_Roughness.png', 'Non-Color'),
        ('emission', 'Spark_RedLamp_Emission.png', 'sRGB'))),
)


def _spark_uv_scope(obj, factors):
    mesh = obj.data
    slots = [(slot.material.name if slot.material else '',
              factors.get(slot.material.name, 1) if slot.material else 1)
             for slot in obj.material_slots]
    # This is an exact structural description, not a fabricated geometry hash.
    signature = str((UV_LAYER, len(mesh.vertices), len(mesh.loops), slots,
                     [(face.material_index, tuple(face.loop_indices)) for face in mesh.polygons]))
    return signature, slots


def _spark_uv_coordinates(uv):
    # Store exact UV coordinates so later manual UV edits cannot be silently
    # mistaken for already scaled coordinates on a rerun. Blender source-only
    # custom data is removed/handled by the parent's assembly/export workflow.
    return str([(float(loop.uv.x), float(loop.uv.y)) for loop in uv.data])


def bind_spark_finishes_mcp():
    if bpy.context.mode != 'OBJECT':
        raise RuntimeError('Finish UV baking requires Object mode before assembly')
    root = bpy.data.objects.get(SOURCE_ROOT)
    if root is None:
        raise RuntimeError('Missing editable Spark source root')
    factors = {entry[0]: entry[1] for entry in FINISH_BINDINGS}
    if len(factors) != 10 or 'Spark_Copper' in factors:
        raise RuntimeError('Unexpected material ownership scope')
    targets = []
    for obj in root.children_recursive:
        if obj.type != 'MESH':
            continue
        if '_LOD' in obj.name.upper():
            raise RuntimeError('Run finish UV baking on source components BEFORE assembly/LOD creation')
        if not any(slot.material and slot.material.name in factors for slot in obj.material_slots):
            continue
        if obj.library or obj.data.library or obj.data.shape_keys:
            raise RuntimeError('Linked or shape-key source mesh needs explicit handling: ' + obj.name)
        uv = obj.data.uv_layers.get(UV_LAYER)
        if uv is None:
            raise RuntimeError('Missing named source UV layer: ' + obj.name)
        if obj.data.uv_layers[0].name != UV_LAYER:
            raise RuntimeError('Named source UV must be the first FBX/Unity UV channel: ' + obj.name)
        signature, slots = _spark_uv_scope(obj, factors)
        for face in obj.data.polygons:
            if face.material_index >= len(slots):
                raise RuntimeError('Invalid material slot: ' + obj.name)
        object_guard = obj.get(BAKE_GUARD)
        mesh_guard = obj.data.get(BAKE_GUARD)
        if object_guard is not None or mesh_guard is not None:
            if object_guard != signature or mesh_guard != signature:
                raise RuntimeError('UV bake guards/layout disagree; do not clear blindly: ' + obj.name)
            stored_coordinates = obj.data.get(UV_GUARD)
            if stored_coordinates != _spark_uv_coordinates(uv):
                raise RuntimeError('UVs changed after finish bake; inspect instead of multiplying again: ' + obj.name)
            targets.append((obj, signature, slots, True))
        else:
            targets.append((obj, signature, slots, False))
    if not targets:
        raise RuntimeError('No editable Spark finish components found')
    for name, factor, emission, bindings in FINISH_BINDINGS:
        material = bpy.data.materials.get(name)
        if material is None or not material.use_nodes:
            raise RuntimeError('Missing existing material: ' + name)
        if not any(node.type == 'BSDF_PRINCIPLED' for node in material.node_tree.nodes):
            raise RuntimeError('Missing existing Principled shader: ' + name)

    # All scene preconditions pass before loading. Read all image files using
    # Blender's permitted image API, before touching any mesh or material.
    loaded = {}
    for name, factor, emission, bindings in FINISH_BINDINGS:
        for role, filename, color_space in bindings:
            image = bpy.data.images.load(TEXTURE_DIRECTORY + filename, check_existing=False)
            image.colorspace_settings.name = color_space
            image.alpha_mode = 'CHANNEL_PACKED' if role == 'metallicSmoothness' else 'NONE'
            image.reload()
            if image.size[0] <= 0 or image.size[1] <= 0:
                raise RuntimeError('Blender image reload failed: ' + filename)
            image.pack()
            loaded[(name, role)] = image

    baked = []
    skipped = []
    scaled_loops = 0
    copper_loops_checked = 0
    for obj, signature, slots, already_baked in targets:
        if already_baked:
            skipped.append(obj.name)
            continue
        # A linked mesh may also be used outside this source root. Isolate
        # every unbaked multi-user mesh before touching its per-face loops.
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        mesh = obj.data
        uv = mesh.uv_layers[UV_LAYER]
        # If execution stops partway through one mesh, a rerun fails rather
        # than scaling partially changed loops for a second time.
        obj[BAKE_GUARD] = 'pending:' + signature
        mesh[BAKE_GUARD] = 'pending:' + signature
        copper_before = []
        for face in mesh.polygons:
            name, factor = slots[face.material_index]
            if name == 'Spark_Copper':
                copper_before.extend((index, float(uv.data[index].uv.x), float(uv.data[index].uv.y))
                                     for index in face.loop_indices)
            if name in factors and factor != 1:
                for index in face.loop_indices:
                    uv.data[index].uv *= factor
                    scaled_loops += 1
        for index, u, v in copper_before:
            if float(uv.data[index].uv.x) != u or float(uv.data[index].uv.y) != v:
                raise RuntimeError('Copper UV invariant failed: ' + obj.name)
        copper_loops_checked += len(copper_before)
        # Object guard satisfies rerun protection; mesh guard covers shared
        # datablocks and makes partial/mismatched ownership fail closed.
        mesh[BAKE_GUARD] = signature
        mesh[UV_GUARD] = _spark_uv_coordinates(uv)
        obj[BAKE_GUARD] = signature
        mesh.update()
        baked.append(obj.name)

    bound = []
    for name, factor, emission, bindings in FINISH_BINDINGS:
        material = bpy.data.materials[name]
        tree = material.node_tree
        shader = next(node for node in tree.nodes if node.type == 'BSDF_PRINCIPLED')
        for old in list(tree.nodes):
            if old.get('sparkFinishBinding', False):
                tree.nodes.remove(old)

        def node(kind, label):
            created = tree.nodes.new(kind)
            created.name = label
            created.label = label
            created['sparkFinishBinding'] = True
            return created

        uv_node = node('ShaderNodeUVMap', 'Spark baked metric UV; shader scale 1')
        uv_node.uv_map = UV_LAYER
        uv_node.location = (-820, 0)
        textures = {}
        for index, (role, filename, color_space) in enumerate(bindings):
            texture = node('ShaderNodeTexImage', 'Spark finish ' + role)
            texture.image = loaded[(name, role)]
            texture.interpolation = 'Linear'
            texture.extension = 'REPEAT'
            texture.location = (-570, 330 - 230 * index)
            tree.links.new(uv_node.outputs['UV'], texture.inputs['Vector'])
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
        normal.uv_map = UV_LAYER
        normal.inputs['Strength'].default_value = 1
        normal.location = (-200, -390)
        tree.links.new(textures['normal'].outputs['Color'], normal.inputs['Color'])
        tree.links.new(normal.outputs['Normal'], shader.inputs['Normal'])
        if 'emission' in textures:
            tree.links.new(textures['emission'].outputs['Color'], shader.inputs['Emission Color'])
            shader.inputs['Emission Strength'].default_value = emission
        material['sparkFinishVisualAccepted'] = False
        material['sparkFinishBindingVersion'] = 2
        material['sparkFinishUvScaleBakedIntoMesh'] = factor
        material['sparkFinishShaderUvScale'] = 1
        bound.append(name)
    return {'boundMaterials': bound, 'uvBakedSourceObjects': baked,
            'alreadyBakedSourceObjectsSkipped': skipped, 'scaledUvLoops': scaled_loops,
            'copperUvLoopsVerifiedUnchanged': copper_loops_checked,
            'freshImagesReloadedAndPacked': len(loaded), 'shaderUvScale': 1,
            'manifestSha256ValidatedExternally': MANIFEST_SHA256,
            'beforeAssemblyRequired': True, 'visualAccepted': False}


print('SPARK_FINISH_BINDING_MCP=' + str(bind_spark_finishes_mcp()))
