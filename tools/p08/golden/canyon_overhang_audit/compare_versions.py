"""Read frozen source versions and original CC0 scans; never save/export geometry."""
import bpy, bmesh, json, math
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT='D:/Project/Unity/racing-bois/'
FINAL=ROOT+'ArtSource/P08/Golden/Canyon/V17/RB_Golden_Canyon_V17_05.blend'
if bpy.data.filepath.replace('\\','/')!=FINAL:
    raise RuntimeError('Owned frozen05 is not open; do not replace unrelated work.')
names=['Canyon_L0_Far_%02d'%index for index in range(33,45)]
clouds={}
versions=[]
raw_scans=[]
rays=[]

def bounds(points):
    low=[min(point[axis] for point in points) for axis in range(3)]
    high=[max(point[axis] for point in points) for axis in range(3)]
    return low,high

def profile(points):
    low,high=bounds(points)
    result=[]
    for band in range(10):
        selected=[point for point in points if min(9,int((point[2]-low[2])/(high[2]-low[2])*10))==band]
        if selected:
            a,b=bounds(selected)
            result.append({'heightFraction':[band/10,(band+1)/10],'vertices':len(selected),
                           'minXYZ':a,'maxXYZ':b})
    return result

def inspect(obj,include_cloud):
    points=[list(obj.matrix_world@vertex.co) for vertex in obj.data.vertices]
    low,high=bounds(points)
    mesh=obj.data;mesh.calc_loop_triangles()
    bm=bmesh.new();bm.from_mesh(mesh)
    boundary=sum(1 for edge in bm.edges if edge.is_boundary)
    nonmanifold=sum(1 for edge in bm.edges if not edge.is_manifold)
    bm.free()
    material_counts={}
    for triangle in mesh.loop_triangles:
        material=mesh.materials[triangle.material_index].name
        material_counts[material]=material_counts.get(material,0)+1
    item={'object':obj.name,'vertices':len(points),'triangles':len(mesh.loop_triangles),
          'minimumBlender':low,'maximumBlender':high,'sizeBlender':[high[axis]-low[axis] for axis in range(3)],
          'matrixWorld':[list(row) for row in obj.matrix_world],
          'boundaryEdges':boundary,'nonManifoldEdges':nonmanifold,'trianglesByMaterial':material_counts,
          'verticalProfileBands':profile(points)}
    if include_cloud:
        item['worldVertices']=points
    return item,points

def nearest(after,before):
    tree=KDTree(len(before))
    for index,point in enumerate(before):
        tree.insert(Vector(point),index)
    tree.balance()
    distances=sorted(tree.find(Vector(point))[2] for point in after)
    return {'maximum':distances[-1],'mean':sum(distances)/len(distances),
            'median':distances[len(distances)//2],'p95':distances[int((len(distances)-1)*.95)],
            'p99':distances[int((len(distances)-1)*.99)],'points':len(distances)}

try:
    for version in ['V13','V14','V15','V16','V17-05']:
        path=FINAL if version=='V17-05' else ROOT+'ArtSource/P08/Golden/Canyon/'+version+'/RB_Golden_Canyon.blend'
        bpy.ops.wm.open_mainfile(filepath=path)
        rows=[];clouds[version]={}
        for name in names:
            obj=bpy.data.objects.get(name)
            if obj is None or obj.type!='MESH':
                raise RuntimeError('Expected frozen formation absent: '+version+'/'+name)
            item,points=inspect(obj,name in ['Canyon_L0_Far_33','Canyon_L0_Far_34'])
            rows.append(item);clouds[version][name]=points
        versions.append({'version':version,'source':path,'objects':rows})

    # Identify actual material ownership at the conspicuous top lips in the
    # unchanged05 gameplay camera. Non-landform volume sheets are stepped past.
    scene=bpy.context.scene;camera=scene.camera
    frame=camera.data.view_frame(scene=scene)
    x0,x1=min(point.x for point in frame),max(point.x for point in frame)
    y0,y1=min(point.y for point in frame),max(point.y for point in frame)
    depsgraph=bpy.context.evaluated_depsgraph_get()
    for u in [.32,.36,.40,.45,.50,.55,.60,.65,.70]:
        for v in [.04,.10,.18,.28]:
            direction=(camera.matrix_world.to_quaternion()@Vector((x0+(x1-x0)*u,y1-(y1-y0)*v,frame[0].z))).normalized()
            origin=camera.matrix_world.translation.copy();hit_data=None;skipped=[]
            for step in range(20):
                hit,point,normal,face,obj,matrix=scene.ray_cast(depsgraph,origin,direction,distance=2500)
                if not hit:
                    break
                if obj.name.startswith('Canyon_L0_'):
                    material_index=obj.data.polygons[face].material_index
                    hit_data={'object':obj.name,'polygon':face,'material':obj.data.materials[material_index].name,
                              'pointBlender':list(point),'normalBlender':list(normal)}
                    break
                skipped.append(obj.name);origin=point+direction*.01
            rays.append({'uvTopLeft':[u,v],'hit':hit_data,'skipped':skipped})

    for slug in ['namaqualand_cliff_01','namaqualand_cliff_02']:
        before_objects=set(bpy.data.objects);before_meshes=set(bpy.data.meshes)
        before_materials=set(bpy.data.materials);before_images=set(bpy.data.images)
        path=ROOT+'ArtSource/P08/Golden/Canyon/SourceModels/'+slug+'/'+slug+'_fbx.fbx'
        try:
            bpy.ops.import_scene.fbx(filepath=path,use_anim=False,use_image_search=False)
            imported=[obj for obj in set(bpy.data.objects)-before_objects if obj.type=='MESH']
            if len(imported)!=1:
                raise RuntimeError('Expected one original CC0 scan mesh: '+slug)
            item,points=inspect(imported[0],True)
            raw_scans.append({'slug':slug,'source':path,'mesh':item})
        finally:
            for obj in set(bpy.data.objects)-before_objects:
                bpy.data.objects.remove(obj,do_unlink=True)
            for mesh in set(bpy.data.meshes)-before_meshes:
                if mesh.users==0:bpy.data.meshes.remove(mesh)
            for material in set(bpy.data.materials)-before_materials:
                if material.users==0:bpy.data.materials.remove(material)
            for image in set(bpy.data.images)-before_images:
                if image.users==0:bpy.data.images.remove(image)

    comparisons=[]
    for name in names:
        closure=nearest(clouds['V15'][name],clouds['V14'][name])
        old=clouds['V16'][name];new=clouds['V17-05'][name]
        old_low,old_high=bounds(old);new_low,new_high=bounds(new)
        scale=[(new_high[axis]-new_low[axis])/(old_high[axis]-old_low[axis]) for axis in range(3)]
        if len(old)!=len(new):raise RuntimeError('V17 changed far-formation vertex population: '+name)
        predicted=[]
        for point in old:
            predicted.append([new_low[axis]+(point[axis]-old_low[axis])*scale[axis] for axis in range(3)])
        residual=max((Vector(actual)-Vector(expected)).length for actual,expected in zip(new,predicted))
        open_predicted=[]
        for point in clouds['V14'][name]:
            open_predicted.append([new_low[axis]+(point[axis]-old_low[axis])*scale[axis] for axis in range(3)])
        comparisons.append({'object':name,
            'v13ToV14NearestMetres':nearest(clouds['V14'][name],clouds['V13'][name]),
            'v14ToV15ClosureNearestMetres':closure,
            'v15ToV16NormalizationNearestMetres':nearest(clouds['V16'][name],clouds['V15'][name]),
            'v16ToV17DiagonalScaleXYZ':scale,'v16ToV17MaximumAffineFitResidualMetres':residual,
            'maximumClosureExtensionBoundAfterAffineMetres':closure['maximum']*max(scale)+residual,
            'v17ClosedToTransformedV14OpenNearestMetres':nearest(new,open_predicted)})
    report={'scope':'Read-only actual frozen mesh comparison. Original CC0 scans imported temporarily; no source saves, geometry edits, exports or Assets writes.',
            'versions':versions,'originalScans':raw_scans,'comparisons':comparisons,'frozen05CameraRays':rays,
            'visualAccepted':False,'original05ReloadedAtEnd':True}
finally:
    bpy.ops.wm.open_mainfile(filepath=FINAL)
print('CANYON_OVERHANG_CAUSAL_AUDIT '+json.dumps(report))
