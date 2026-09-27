import bpy,math,random,json
from mathutils import Vector,noise
ROOT='D:/Project/Unity/racing-bois/';scene=bpy.context.scene;root=bpy.data.objects['RB_Golden_MenuEnvironment']
R=Vector((-.52999894,.84799830,0));D=Vector((-.84799830,-.52999894,0));UP=Vector((0,0,1))
def p(u,y,d):return R*u+D*d+UP*y
def ground_height(u,d):
    if d<=1.8:return -.025+.007*noise.noise(Vector((u*.5,d*.5,11)))
    drop=min(1,(d-1.8)/17)
    return -.025-32*(drop*drop*(3-2*drop))+noise.noise(Vector((u*.035,d*.025,12)))*drop*3
random.seed(27190)
clumps=[(random.uniform(-12,5),random.uniform(1.7,3.0),random.uniform(.75,1.25)) for i in range(70)]
for tile in range(4):
    selected=[value for i,value in enumerate(clumps) if i%4==tile]
    for level,count in enumerate([32,14,6]):
        vertices=[];faces=[];uvs=[];random.seed(2100+tile)
        for u,d,scale in selected:
            for blade in range(count):
                angle=random.uniform(0,math.pi*2);radius=random.uniform(.01,.09)*scale
                x=u+math.cos(angle)*radius;z=d+math.sin(angle)*radius;y=ground_height(x,z)
                origin=p(x,y,z);side=(R*(-math.sin(angle))+D*math.cos(angle))*random.uniform(.003,.006)*scale
                lean=(R*math.cos(angle)+D*math.sin(angle))*random.uniform(.05,.2)*scale
                h=random.uniform(.14,.40)*scale;mid=origin+lean*.35+UP*h*.6;tip=origin+lean+UP*h
                start=len(vertices);vertices.extend([origin-side,origin+side,mid+side*.6,mid-side*.6,tip])
                faces.extend([(start,start+1,start+2),(start,start+2,start+3),(start+3,start+2,start+4)])
                uvs.extend([[(0,0),(1,0),(1,.6)],[(0,0),(1,.6),(0,.6)],[(0,.6),(1,.6),(.5,1)]])
        mesh=bpy.data.meshes.new('Menu_L%d_EdgeGrass_%02d'%(level,tile));mesh.from_pydata(vertices,[],faces);mesh.update();uv=mesh.uv_layers.new(name='UV0_SurfaceMetres')
        for face,coords in zip(mesh.polygons,uvs):
            for loop,value in zip(face.loop_indices,coords):uv.data[loop].uv=value
        obj=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(obj);obj.parent=root;mesh.materials.append(bpy.data.materials['Canyon_DryGrass']);obj.hide_set(level!=0);obj.hide_render=level!=0

# Commit the exact audited loop-triangle stream. Reproject only zero-area
# thickness-cap UVs, retaining positions/materials/other UV corners.
rows=[]
for obj in list(root.children_recursive):
    if obj.type!='MESH':continue
    old=obj.data;old.calc_loop_triangles();triangles=list(old.loop_triangles)
    vertices=[tuple(v.co) for v in old.vertices];faces=[tuple(t.vertices) for t in triangles]
    normal_values=[tuple(old.corner_normals[i].vector) for tri in triangles for i in tri.loops]
    layers={layer.name:[tuple(layer.data[i].uv) for tri in triangles for i in tri.loops] for layer in old.uv_layers}
    fixes=0
    for layer_name,values in layers.items():
        for index,tri in enumerate(triangles):
            a,b,c=values[index*3:index*3+3]
            cross=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
            if cross>1e-14:continue
            assert 'Guardrail_Beam' in obj.name,'Unexpected UV repair scope: '+obj.name
            points=[old.vertices[i].co.copy() for i in tri.vertices];origin=points[0]
            normal=(points[1]-origin).cross(points[2]-origin)
            dominant=0
            for axis in range(1,3):
                if abs(normal[axis])>abs(normal[dominant]):dominant=axis
            axes=[i for i in range(3) if i!=dominant]
            values[index*3:index*3+3]=[tuple((point[i]-origin[i])/2 for i in axes) for point in points];fixes+=1
    new=bpy.data.meshes.new(old.name+'_Explicit');new.from_pydata(vertices,[],faces);new.update()
    for material in old.materials:new.materials.append(material)
    for face,tri in zip(new.polygons,triangles):face.material_index=old.polygons[tri.polygon_index].material_index;face.use_smooth=old.polygons[tri.polygon_index].use_smooth
    for name,values in layers.items():
        uv=new.uv_layers.new(name=name,do_init=False)
        for index,value in enumerate(values):uv.data[index].uv=value
    obj.data=new;new.normals_split_custom_set(normal_values);new.update()
    deviation=0
    for expected,actual in zip(normal_values,new.corner_normals):
        a=Vector(expected);b=actual.vector;deviation=max(deviation,math.degrees(math.atan2(a.cross(b).length,a.dot(b))))
    rows.append({'name':obj.name,'triangles':len(faces),'guardrailCapUvRepairs':fixes,'maximumNormalEncodingDeviationDegrees':deviation})
scene.render.filepath=ROOT+'docs/p08/golden/menu-environment/v1/composition-04.png'
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/MenuEnvironment/V1/RB_Golden_MenuEnvironment.blend')
print('MENU_EXPLICIT_TRIANGLES '+json.dumps({'objects':rows,'repairs':sum(r['guardrailCapUvRepairs'] for r in rows),'maximumNormalEncodingDeviationDegrees':max(r['maximumNormalEncodingDeviationDegrees'] for r in rows),'visualAccepted':False}))
bpy.ops.render.render(write_still=True)
