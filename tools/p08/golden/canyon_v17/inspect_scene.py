"""Read-only ownership/geometry inspection through pinned direct Blender MCP9877."""
import bpy, json

scene = bpy.context.scene
camera = scene.camera
print('CANYON_V17_SCENE_INSPECTION ' + json.dumps({
    'filepath': bpy.data.filepath,
    'isDirty': bpy.data.is_dirty,
    'scene': scene.name,
    'objects': len(scene.objects),
    'roots': [{'name': o.name, 'type': o.type} for o in scene.objects if o.parent is None],
    'camera': None if camera is None else {
        'name': camera.name, 'position': list(camera.location), 'rotation': list(camera.rotation_euler),
        'lens': camera.data.lens, 'sensorWidth': camera.data.sensor_width,
        'resolution': [scene.render.resolution_x, scene.render.resolution_y],
        'pixelAspect': [scene.render.pixel_aspect_x, scene.render.pixel_aspect_y]},
    'scope': 'Read-only current Blender scene ownership, no source or scene mutation.'
}))
