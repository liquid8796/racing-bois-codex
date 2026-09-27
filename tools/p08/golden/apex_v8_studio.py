"""Physical neutral cyclorama for repeatable actual renders; not exported."""
import bpy, math
from mathutils import Vector
scene=bpy.context.scene
floor=bpy.data.objects.get('Studio floor not exported')
if floor:floor.hide_render=True
backdrop=bpy.data.objects.get('Apex V8 studio cyclorama')
if backdrop is None:
    profile=[(-12,-.003),(3,-.003)]
    for i in range(1,33):
        a=i*math.pi/64
        profile.append((3+2*math.sin(a),-.003+2*(1-math.cos(a))))
    profile.append((5,9))
    vertices=[];faces=[]
    for y,z in profile:vertices.extend([(-12,y,z),(12,y,z)])
    for i in range(len(profile)-1):faces.append((2*i,2*i+1,2*i+3,2*i+2))
    data=bpy.data.meshes.new('Cyclorama review geometry');data.from_pydata(vertices,[],faces);data.update()
    backdrop=bpy.data.objects.new('Apex V8 studio cyclorama',data);scene.collection.objects.link(backdrop)
    mat=bpy.data.materials.get('Studio_Only_Ground')
    if mat:backdrop.data.materials.append(mat)
    for poly in data.polygons:poly.use_smooth=True
camera=scene.camera
backdrop.rotation_euler.z=math.atan2(camera.location.x,-camera.location.y)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.26
print('V8 neutral review cyclorama ready; no model geometry changed.')
