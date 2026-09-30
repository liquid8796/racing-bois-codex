CONFIG = {'schema': 'racing-bois.tripo-blender-review-config.v1', 'asset_id': 'RB_P08_Bike_00', 'candidate_directory': 'ArtSource/P08/Tripo/Spark/20260930-hq01', 'evidence_directory': 'docs/p08/tripo/spark/20260930-hq01', 'model_name': 'model.glb', 'raw_source_name': 'Spark_Tripo_hq01_raw_import.blend', 'review_source_name': 'Spark_Tripo_hq01_review.blend', 'reference': {'path': 'ArtSource/Concepts/P08/Golden/spark-v1.png', 'sha256': 'e358ecf1a809f5373aa45ef92cbd6897ed1e1693cacc73b0f6df697d91bedce6'}, 'input': {'path': 'ArtSource/Concepts/P08/Golden/spark-v1-side.png', 'sha256': 'ad5478c942350462a34d12b1ba9f9714cb00a595ff9465bc1d000cf6b5e7ad0b'}, 'protected_club': {'path': 'ArtSource/Weapons/RB_Club.blend', 'sha256': '553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f'}, 'canonical_dimensions_metres': {}, 'resolution': [1536, 1024], 'front_long_axis_sign': 1, 'camera_scope': 'Uncalibrated full-object orthographic diagnostics matching previous API trial directions. Actual front sign must be visually confirmed before assigning front/rear names. No concept fidelity or physical scale accepted.', 'source_collection': 'RB_TRIPO_SPARK_HQ_SOURCE_UNACCEPTED', 'candidate_absolute': 'D:/Project/Unity/racing-bois/ArtSource/P08/Tripo/Spark/20260930-hq01', 'evidence_absolute': 'D:/Project/Unity/racing-bois/docs/p08/tripo/spark/20260930-hq01', 'requested_stage': 'saved-verification', 'config_sha256': 'd94845f9aea25d37faca00381ce8b03a39e8be661fb74840ac08667ea77a5d5d', 'model_sha256': '896e625af9a9a647b080b47fbb7f038950a1e3af61e22826eae872030ab7465c'}
"""Owned direct-Blender review of an immutable Tripo download, never production."""
from array import array
import json
import math
import colorsys

import bpy
from mathutils import Vector

# CONFIG is injected as a literal by the secret-free external stage runner.
SOURCE_COLLECTION = 'RB_TRIPO_SPARK_HQ_SOURCE_UNACCEPTED'
REVIEW_COLLECTION = 'RB_TRIPO_SPARK_HQ_REVIEW'


def require_safe():
    if bpy.context.preferences.filepaths.use_scripts_auto_execute:
        raise RuntimeError('Script auto-execution must already be disabled')


def raw_path():
    return CONFIG['candidate_absolute'] + '/' + CONFIG['raw_source_name']


def review_path():
    return CONFIG['candidate_absolute'] + '/' + CONFIG['review_source_name']


def require_loaded(path):
    require_safe()
    if bpy.data.filepath.replace('\\', '/') != path:
        raise RuntimeError('Unexpected owned Blender source')
    if bpy.app.is_job_running('RENDER'):
        raise RuntimeError('A render is still active')


def require_new_report(stage):
    if stage != CONFIG['requested_stage']:
        raise RuntimeError('Unexpected externally preflighted stage')


def report(stage, payload):
    payload = {'schema': 'racing-bois.tripo-owned-blender-stage.v1',
               'stage': stage, 'candidate_status': 'unaccepted',
               'visual_accepted': False, 'production_accepted': False,
               'config_sha256': CONFIG['config_sha256'], **payload}
    print('TRIPO_HQ_STAGE_JSON ' + json.dumps(payload))


def buffer_data(items, property_name, length, typecode):
    values = array(typecode, [0]) * length
    if length:
        items.foreach_get(property_name, values)
    return values.tobytes()


def named_key(datablock):
    return datablock.name


def source_objects():
    source = bpy.data.collections.get(SOURCE_COLLECTION)
    if source is None:
        raise RuntimeError('Owned raw source collection missing')
    return sorted(source.all_objects, key=named_key)


def assembly_bounds():
    records = []
    for obj in source_objects():
        if obj.type != 'MESH':
            continue
        points = [obj.matrix_world @ Vector(vertex) for vertex in obj.bound_box]
        lower = [min(point[i] for point in points) for i in range(3)]
        upper = [max(point[i] for point in points) for i in range(3)]
        records.append({'object': obj.name, 'mesh': obj.data.name,
            'bounds_min': lower, 'bounds_max': upper,
            'center': [(lower[i] + upper[i]) * .5 for i in range(3)],
            'dimensions': [upper[i] - lower[i] for i in range(3)],
            'triangles': sum(len(p.vertices) - 2 for p in obj.data.polygons),
            'vertices': len(obj.data.vertices),
            'classification': 'unassigned; actual view review required'})
    return records


def geometry_snapshot():
    result = []
    for obj in source_objects():
        record = {'object': obj.name, 'type': obj.type,
                  'matrix_world': [list(row) for row in obj.matrix_world],
                  'parent': obj.parent.name if obj.parent else None,
                  'modifiers': [(m.name, m.type) for m in obj.modifiers]}
        if obj.type == 'MESH':
            mesh = obj.data
            record.update({'mesh': mesh.name, 'vertices': len(mesh.vertices),
                'edges': len(mesh.edges), 'polygons': len(mesh.polygons),
                'triangles': sum(len(p.vertices) - 2 for p in mesh.polygons),
                'positions_diagnostic': {'count': len(mesh.vertices), 'byte_compare_with_owned_baseline': True},
                'uv_layers': [{'name': uv.name, 'loops': len(uv.data)}
                              for uv in mesh.uv_layers],
                'materials': [mat.name if mat else None for mat in mesh.materials],
                'shape_keys': list(mesh.shape_keys.key_blocks.keys()) if mesh.shape_keys else [],
                'vertex_groups': [group.name for group in obj.vertex_groups]})
        elif obj.type == 'ARMATURE':
            record['bones'] = len(obj.data.bones)
        result.append(record)
    return result


def image_snapshot():
    materials = {mat for obj in source_objects() if obj.type == 'MESH'
                 for mat in obj.data.materials if mat and mat.use_nodes}
    images = {node.image for mat in materials for node in mat.node_tree.nodes
              if node.type == 'TEX_IMAGE' and node.image}
    return [{'name': image.name, 'size': list(image.size),
             'color_space': image.colorspace_settings.name,
             'packed': bool(image.packed_file),
             'packed_bytes': len(image.packed_file.data) if image.packed_file else None}
            for image in sorted(images, key=named_key)]


def verify_mesh_pair(mesh, baseline):
    for left, right, property_name, multiplier, typecode in (
        (mesh.vertices, baseline.vertices, 'co', 3, 'f'),
        (mesh.edges, baseline.edges, 'vertices', 2, 'i'),
        (mesh.loops, baseline.loops, 'vertex_index', 1, 'i'),
        (mesh.polygons, baseline.polygons, 'loop_start', 1, 'i'),
        (mesh.polygons, baseline.polygons, 'loop_total', 1, 'i'),
        (mesh.polygons, baseline.polygons, 'material_index', 1, 'i')):
        if len(left) != len(right) or buffer_data(left, property_name, len(left)*multiplier, typecode) != buffer_data(right, property_name, len(right)*multiplier, typecode):
            raise RuntimeError('Raw mesh byte arrays changed: ' + mesh.name + ' / ' + property_name)
    if list(mesh.uv_layers.keys()) != list(baseline.uv_layers.keys()):
        raise RuntimeError('Raw UV layer membership changed')
    for uv in mesh.uv_layers:
        target = baseline.uv_layers[uv.name]
        if len(uv.data) != len(target.data) or buffer_data(uv.data, 'uv', len(uv.data)*2, 'f') != buffer_data(target.data, 'uv', len(target.data)*2, 'f'):
            raise RuntimeError('Raw UV byte array changed: ' + mesh.name)


def verify_unchanged():
    scene = bpy.context.scene
    baseline = json.loads(scene['raw_geometry_inventory_json'])
    geometry = geometry_snapshot()
    images = image_snapshot()
    if geometry != baseline or images != json.loads(scene['raw_image_inventory_json']):
        raise RuntimeError('Raw source transforms, object/UV/material inventory or texture metadata changed')
    for obj in source_objects():
        if obj.type == 'MESH':
            verify_mesh_pair(obj.data, bpy.data.meshes[obj.data['review_baseline_mesh']])
    for original_name, baseline_name in json.loads(scene['review_baseline_images_json']):
        original = bpy.data.images[original_name]
        copy = bpy.data.images[baseline_name]
        if not original.packed_file or not copy.packed_file or bytes(original.packed_file.data) != bytes(copy.packed_file.data):
            raise RuntimeError('Raw packed texture bytes changed')
    return geometry, images


def import_raw():
    require_safe()
    require_new_report('raw-import')
    model = CONFIG['candidate_absolute'] + '/' + CONFIG['model_name']
    if bpy.data.filepath or set(bpy.data.objects.keys()) != {'Cube', 'Camera', 'Light'}:
        raise RuntimeError('Expected fresh owned factory scene')
    before = set(bpy.data.objects)
    if bpy.ops.import_scene.gltf(filepath=str(model)) != {'FINISHED'}:
        raise RuntimeError('GLB importer did not finish')
    imported = [obj for obj in bpy.data.objects if obj not in before]
    if not any(obj.type == 'MESH' for obj in imported):
        raise RuntimeError('No source mesh imported')
    collection = bpy.data.collections.new(SOURCE_COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    for obj in imported:
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)
    for obj in before:
        obj.hide_render = True
        obj.hide_set(True)
    scene = bpy.context.scene
    scene['candidate_status'] = 'unaccepted'
    scene['master_sha256'] = CONFIG['reference']['sha256']
    scene['input_sha256'] = CONFIG['input']['sha256']
    scene['raw_model_sha256'] = CONFIG['model_sha256']
    scene['source_geometry_modified'] = False
    geometry = geometry_snapshot()
    images = image_snapshot()
    scene['raw_geometry_inventory_json'] = json.dumps(geometry)
    scene['raw_image_inventory_json'] = json.dumps(images)
    for obj in source_objects():
        if obj.type == 'MESH':
            copy = obj.data.copy()
            copy.name = obj.data.name + '_REVIEW_BASELINE_ONLY'
            copy.use_fake_user = True
            obj.data['review_baseline_mesh'] = copy.name
    image_pairs = []
    for image_record in images:
        original = bpy.data.images[image_record['name']]
        copy = original.copy()
        copy.name = original.name + '_REVIEW_BASELINE_ONLY'
        copy.use_fake_user = True
        image_pairs.append((original.name, copy.name))
    scene['review_baseline_images_json'] = json.dumps(image_pairs)
    verify_unchanged()
    bpy.ops.wm.save_as_mainfile(filepath=raw_path())
    report('raw-import', {'model_path': model, 'model_sha256': CONFIG['model_sha256'],
        'raw_source_path': raw_path(),
        'geometry': geometry, 'images': images, 'assembly_bounds': assembly_bounds(),
        'blender_version': bpy.app.version_string,
        'auto_execute': bpy.context.preferences.filepaths.use_scripts_auto_execute,
        'scale_status': 'Producer normalized coordinates; not physically calibrated',
        'assembly_status': 'Object, rig and vertex-group inventory only; no semantic part or motion validation'})


def prepare_review():
    require_loaded(raw_path())
    require_new_report('review-setup')
    if bpy.data.collections.get(REVIEW_COLLECTION):
        raise RuntimeError('Review setup already exists')
    geometry, images = verify_unchanged()
    meshes = [obj for obj in source_objects() if obj.type == 'MESH']
    points = [obj.matrix_world @ Vector(vertex) for obj in meshes for vertex in obj.bound_box]
    lower = Vector([min(p[i] for p in points) for i in range(3)])
    upper = Vector([max(p[i] for p in points) for i in range(3)])
    span = upper - lower
    center = (upper + lower) * .5
    extent = max(span)
    if not math.isfinite(extent) or extent <= 0:
        raise RuntimeError('Invalid source bounds')
    long_axis = 0 if span.x >= span.y else 1
    along = Vector((1, 0, 0) if long_axis == 0 else (0, 1, 0))
    along *= CONFIG['front_long_axis_sign']
    across = Vector((0, -1, 0) if long_axis == 0 else (1, 0, 0))
    up = Vector((0, 0, 1))
    review = bpy.data.collections.new(REVIEW_COLLECTION)
    bpy.context.scene.collection.children.link(review)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x, scene.render.resolution_y = CONFIG['resolution']
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = False
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    world = bpy.data.worlds.new('TripoHQReview_World')
    world.use_nodes = True
    background = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    background.inputs['Color'].default_value = (.18, .18, .18, 1)
    background.inputs['Strength'].default_value = .45
    scene.world = world
    floor_material = bpy.data.materials.new('TripoHQReview_Floor')
    floor_material.use_nodes = True
    shader = next(n for n in floor_material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value = (.24, .24, .24, 1)
    shader.inputs['Roughness'].default_value = .85
    bpy.ops.mesh.primitive_plane_add(size=extent * 200,
        location=(center.x, center.y, lower.z - extent * .002))
    floor = bpy.context.object
    floor.name = 'TripoHQReview_Floor'
    floor.data.materials.append(floor_material)
    for old in list(floor.users_collection):
        old.objects.unlink(floor)
    review.objects.link(floor)
    for name, direction, power in (
        ('Key', across * 2 - along + up * 3, 850),
        ('Fill', -across * 2 + along + up * 2, 450),
        ('Rim', along * 2 - across + up * 3, 900)):
        data = bpy.data.lights.new('TripoHQReview_' + name, 'AREA')
        data.energy = power * extent * extent / 4
        data.shape = 'DISK'
        data.size = extent * 1.8
        light = bpy.data.objects.new(data.name, data)
        review.objects.link(light)
        light.location = center + direction * extent
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
    cameras = []
    for name, direction in (
        ('quarter_positive', across * 1.65 + along * .9 + up * .55),
        ('quarter_negative', across * 1.65 - along * .9 + up * .55),
        ('side', across + up * .05),
        ('axis_positive', along + up * .1),
        ('axis_negative', -along + up * .1)):
        data = bpy.data.cameras.new('TripoHQReview_' + name)
        camera = bpy.data.objects.new(data.name, data)
        review.objects.link(camera)
        camera.location = center + direction.normalized() * extent * 4
        camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
        data.type = 'ORTHO'
        data.clip_start = extent * .001
        data.clip_end = extent * 1000
        bpy.context.view_layer.update()
        inv = camera.matrix_world.inverted()
        projected = [inv @ p for p in points]
        width = max(p.x for p in projected) - min(p.x for p in projected)
        height = max(p.y for p in projected) - min(p.y for p in projected)
        data.sensor_fit = 'HORIZONTAL'
        aspect = CONFIG['resolution'][0] / CONFIG['resolution'][1]
        data.ortho_scale = max(width, height * aspect) * 1.2
        cameras.append({'name': camera.name, 'location': list(camera.location),
            'rotation_euler': list(camera.rotation_euler), 'projection': data.type,
            'ortho_scale': data.ortho_scale, 'sensor_fit': data.sensor_fit})
    scene.camera = bpy.data.objects['TripoHQReview_quarter_positive']
    scene['review_camera_calibration'] = CONFIG['camera_scope']
    verify_unchanged()
    bpy.ops.wm.save_as_mainfile(filepath=review_path())
    report('review-setup', {'review_source_path': review_path(),
        'source_geometry_modified': False, 'geometry_signature_verified': True,
        'bounds_min': list(lower), 'bounds_max': list(upper), 'dimensions': list(span),
        'long_axis': long_axis, 'front_sign_provisional': CONFIG['front_long_axis_sign'],
        'cameras': cameras, 'engine': scene.render.engine,
        'view_transform': scene.view_settings.view_transform, 'look': scene.view_settings.look,
        'exposure': scene.view_settings.exposure, 'resolution': CONFIG['resolution'],
        'camera_calibration': CONFIG['camera_scope'],
        'physical_scale': 'Not calibrated; canonical dimensions recorded only as future constraints'})


def reload_saved():
    require_loaded(review_path())
    require_new_report('reload-saved')
    if bpy.data.is_dirty:
        raise RuntimeError('Unsaved changes require explicit ownership review before reload')
    if bpy.ops.wm.open_mainfile(filepath=review_path(), load_ui=False,
                              use_scripts=False) != {'FINISHED'}:
        raise RuntimeError('Owned source reload failed')
    report('reload-saved', {'load_ui': False, 'use_scripts': False})


def verify_saved():
    require_loaded(review_path())
    require_new_report('saved-verification')
    geometry, images = verify_unchanged()
    report('saved-verification', {'review_source_path': review_path(), 'geometry_byte_arrays_verified': True,
        'packed_texture_bytes_verified': True, 'geometry': geometry, 'images': images,
        'auto_execute': bpy.context.preferences.filepaths.use_scripts_auto_execute,
        'physical_scale': 'Not calibrated', 'semantic_parts': 'Unverified',
        'rigs': [r for r in geometry if r['type'] == 'ARMATURE'],
        'actions': [a.name for a in bpy.data.actions]})


def finalize_review():
    require_loaded(review_path())
    require_new_report('rendered-checkpoint')
    verify_unchanged()
    target = review_path()[:-6] + '_rendered.blend'
    bpy.ops.wm.save_as_mainfile(filepath=target)
    report('rendered-checkpoint', {'rendered_source_path': target,
        'geometry_byte_arrays_verified': True, 'packed_texture_bytes_verified': True,
        'render_camera': bpy.context.scene.camera.name,
        'material_override': bpy.context.view_layer.material_override.name
                             if bpy.context.view_layer.material_override else None,
        'purpose': 'Preserve owned post-render state before loading a separate candidate'})


def render(view, mode='pbr'):
    require_loaded(review_path())
    prefix = 'clay-' if mode == 'clay' else 'parts-id-' if mode == 'parts-id' else ''
    stage = 'render-' + prefix + view
    require_new_report(stage)
    if view not in ('quarter_positive', 'quarter_negative', 'side',
                    'axis_positive', 'axis_negative'):
        raise RuntimeError('Unknown diagnostic camera')
    verify_unchanged()
    output = CONFIG['evidence_absolute'] + '/renders/' + prefix + view + '.png'
    scene = bpy.context.scene
    scene.camera = bpy.data.objects['TripoHQReview_' + view]
    scene.render.filepath = str(output)
    layer = bpy.context.view_layer
    previous_override = layer.material_override
    color_records = []
    if mode == 'clay':
        clay = bpy.data.materials.get('TripoHQReview_Clay')
        if clay is None:
            clay = bpy.data.materials.new('TripoHQReview_Clay')
            clay.use_nodes = True
            shader = next(node for node in clay.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
            shader.inputs['Base Color'].default_value = (.45, .45, .45, 1)
            shader.inputs['Roughness'].default_value = .6
            shader.inputs['Metallic'].default_value = 0
        layer.material_override = clay
    elif mode == 'parts-id':
        material = bpy.data.materials.get('TripoHQReview_PartsID')
        if material is None:
            material = bpy.data.materials.new('TripoHQReview_PartsID')
            material.use_nodes = True
            shader = next(node for node in material.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
            shader.inputs['Roughness'].default_value = .7
            shader.inputs['Metallic'].default_value = 0
            info = material.node_tree.nodes.new('ShaderNodeObjectInfo')
            material.node_tree.links.new(info.outputs['Color'], shader.inputs['Base Color'])
        for obj in source_objects():
            if obj.type != 'MESH':
                continue
            index = int(obj.name.split('_')[-1])
            rgba = colorsys.hsv_to_rgb((index * .6180339887498949) % 1, .75, .85) + (1,)
            color_records.append({'object': obj.name, 'old_rgba': list(obj.color), 'review_rgba': list(rgba)})
            obj.color = rgba
        layer.material_override = material
    try:
        if bpy.ops.render.render(write_still=True) != {'FINISHED'}:
            raise RuntimeError('Actual render did not finish')
    finally:
        layer.material_override = previous_override
        for record in color_records:
            bpy.data.objects[record['object']].color = record['old_rgba']
    verify_unchanged()
    report(stage, {'view': view, 'mode': mode, 'image_path': output, 'camera': scene.camera.name,
        'camera_location': list(scene.camera.location),
        'camera_rotation_euler': list(scene.camera.rotation_euler),
        'ortho_scale': scene.camera.data.ortho_scale,
        'engine': scene.render.engine, 'resolution': CONFIG['resolution'],
        'source_geometry_modified': False, 'geometry_byte_arrays_verified': True,
        'material_override_restored': layer.material_override == previous_override,
        'part_id_legend': color_records,
        'object_colors_restored': all(list(bpy.data.objects[r['object']].color) == r['old_rgba'] for r in color_records)})

verify_saved()
