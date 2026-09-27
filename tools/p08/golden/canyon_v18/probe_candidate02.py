"""Read-only component/material/front-facing evidence for the frozen Far33 experiment."""
import bpy,bmesh,json
from mathutils import Vector

if not bpy.data.filepath.replace('\\','/').endswith('/Canyon/V18/RB_Golden_Canyon_V18_02.blend'):
    raise RuntimeError('Expected owned frozen V18-02.')
rows=[]
for level in range(3):
    obj=bpy.data.objects['Canyon_L%d_Far_33'%level]
    bm=bmesh.new();bm.from_mesh(obj.data)
    remaining=set(bm.faces);components=[]
    while remaining:
        seed=remaining.pop();faces=[seed];stack=[seed]
        while stack:
            face=stack.pop()
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked in remaining:
                        remaining.remove(linked);faces.append(linked);stack.append(linked)
        volume=0.0
        for face in faces:
            a,b,c=[vertex.co for vertex in face.verts]
            volume+=a.dot(b.cross(c))/6
        components.append({'triangles':len(faces),'signedVolume':volume})
    if len(components)!=1 or components[0]['signedVolume']<=0:
        raise RuntimeError('Expected one outward closed mass: '+obj.name)
    rows.append({'object':obj.name,'connectedComponents':components,
        'materialSlots':[material.name for material in obj.data.materials],
        'usedMaterialIndices':sorted(set(face.material_index for face in bm.faces)),
        'primaryUvIndex':obj.data.uv_layers.active_index})
    bm.free()

scene=bpy.context.scene;camera=scene.camera
frame=camera.data.view_frame(scene=scene)
x0,x1=min(point.x for point in frame),max(point.x for point in frame)
y0,y1=min(point.y for point in frame),max(point.y for point in frame)
depsgraph=bpy.context.evaluated_depsgraph_get();rays=[]
for u in [.28,.30,.32,.34,.36,.38,.40]:
    for v in [.04,.10,.18,.28,.36]:
        direction=(camera.matrix_world.to_quaternion()@Vector((x0+(x1-x0)*u,y1-(y1-y0)*v,frame[0].z))).normalized()
        origin=camera.matrix_world.translation.copy();result=None
        for step in range(20):
            hit,point,normal,face,obj,matrix=scene.ray_cast(depsgraph,origin,direction,distance=2500)
            if not hit:break
            if obj.name.startswith('Canyon_L0_'):
                result={'object':obj.name,'material':obj.data.materials[obj.data.polygons[face].material_index].name,
                    'pointBlender':list(point),'normalBlender':list(normal),'normalDotToCamera':normal.dot(-direction)}
                break
            origin=point+direction*.01
        rays.append({'uvTopLeft':[u,v],'hit':result})
print('CANYON_V18_SURFACE02 '+json.dumps({'source':bpy.data.filepath,'components':rows,'cameraRays':rays,
    'sourceSaved':False,'geometryChanged':False,'exportedToAssets':False,'visualAccepted':False}))
