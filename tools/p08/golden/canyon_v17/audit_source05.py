"""Read actual current source geometry; this does not grant visual acceptance."""
import bpy,math,json
if not bpy.data.filepath.replace('\\','/').endswith('/Canyon/V17/RB_Golden_Canyon_V17_05.blend'):
    raise RuntimeError('Expected frozen05 for descriptor-bound measurements.')
root=bpy.data.objects['RB_Golden_Canyon']
objects=[o for o in root.children_recursive if o.type=='MESH']
report={'schema':1,'visualAccepted':False,'objects':[],'boundsMin':[float('inf')]*3,'boundsMax':[float('-inf')]*3,'markers':{},'lodTriangles':[0,0,0],'frontFaceViolations':0}
for name in ['Forward','Ground_Origin','LeftRoadMarker','RightRoadMarker']:
    p=root.matrix_world.inverted()@bpy.data.objects[name].matrix_world.translation
    report['markers'][name]=[p.x,p.z,p.y]
for obj in objects:
    mesh=obj.data;mesh.calc_loop_triangles();zero=sum(1 for poly in mesh.polygons if poly.area<1e-12)
    nonfinite=sum(1 for v in mesh.vertices if not all(math.isfinite(float(c)) for c in v.co))
    uv=mesh.uv_layers.active
    invalid_uv=sum(1 for item in uv.data if not all(math.isfinite(float(c)) for c in item.uv)) if uv else -1
    level=0 if '_L0_' in obj.name else 1 if '_L1_' in obj.name else 2
    report['lodTriangles'][level]+=len(mesh.loop_triangles)
    for vertex in mesh.vertices:
        p=root.matrix_world.inverted()@obj.matrix_world@vertex.co
        p=(p.x,p.z,p.y)
        for axis in range(3):report['boundsMin'][axis]=min(report['boundsMin'][axis],p[axis]);report['boundsMax'][axis]=max(report['boundsMax'][axis],p[axis])
    ground=all(m.name in ['Canyon_Asphalt','Canyon_Gravel','Canyon_YellowPaint','Canyon_WhitePaint'] for m in mesh.materials)
    inverted=sum(1 for p in mesh.polygons if p.normal.z<-.00001) if ground else 0
    report['frontFaceViolations']+=inverted
    report['objects'].append({'groundFacesPointUp':inverted==0 if ground else None,'wrongGroundFaces':inverted,'name':obj.name,'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles),'degenerateFaces':zero,'nonFiniteVertices':nonfinite,'invalidUvs':invalid_uv,'materials':[m.name for m in mesh.materials]})
report['boundsSize']=[report['boundsMax'][i]-report['boundsMin'][i] for i in range(3)]
report['geometryChecksPassed']=report['frontFaceViolations']==0 and all(x['degenerateFaces']==0 and x['nonFiniteVertices']==0 and x['invalidUvs']==0 for x in report['objects'])
report['source'] = bpy.data.filepath
camera = bpy.context.scene.camera
report['cameraBlender'] = {'position': list(camera.location), 'rotationEulerRadians': list(camera.rotation_euler),
    'focalLengthMm': camera.data.lens, 'sensorWidthMm': camera.data.sensor_width, 'sensorFit': camera.data.sensor_fit,
    'clipStart': camera.data.clip_start, 'clipEnd': camera.data.clip_end,
    'resolution': [bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y],
    'resolutionPercentage': bpy.context.scene.render.resolution_percentage}
print('CANYON_SOURCE_AUDIT05 '+json.dumps(report))
