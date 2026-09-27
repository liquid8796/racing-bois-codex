"""Read-only local CC0 cliff surface sampling; remove only owned imports."""
import bpy,json,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root='D:/Project/Unity/racing-bois/'
if bpy.data.filepath.replace('\\','/')!=root+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_05.blend':
    raise RuntimeError('Expected owned frozen05.')
before_objects=set(bpy.data.objects);before_meshes=set(bpy.data.meshes)
before_materials=set(bpy.data.materials);before_images=set(bpy.data.images)
states=[(obj,obj.hide_get(),obj.select_get()) for obj in bpy.context.view_layer.objects]
active=bpy.context.view_layer.objects.active
source=root+'ArtSource/P08/Golden/Canyon/SourceModels/namaqualand_cliff_01/namaqualand_cliff_01_fbx.fbx'
try:
    bpy.ops.import_scene.fbx(filepath=source,use_anim=False,use_image_search=False)
    imported=[obj for obj in set(bpy.data.objects)-before_objects if obj.type=='MESH']
    if len(imported)!=1:raise RuntimeError('Expected one local CC0 scan.')
    obj=imported[0];mesh=obj.data;mesh.calc_loop_triangles()
    vertices=[obj.matrix_world@v.co for v in mesh.vertices]
    triangles=[tuple(t.vertices) for t in mesh.loop_triangles]
    bvh=BVHTree.FromPolygons(vertices,triangles,all_triangles=True)
    minimum=[min(v[i] for v in vertices) for i in range(3)]
    maximum=[max(v[i] for v in vertices) for i in range(3)]
    domain=[minimum[0]+.12*(maximum[0]-minimum[0]),maximum[0]-.12*(maximum[0]-minimum[0]),
            minimum[2]+.13*(maximum[2]-minimum[2]),maximum[2]-.13*(maximum[2]-minimum[2])]
    fields=[];width=64;height=40
    for side in [-1,1]:
        rows=[];missing=0
        for row in range(height):
            line=[];z=domain[2]+(domain[3]-domain[2])*row/(height-1)
            for col in range(width):
                x=domain[0]+(domain[1]-domain[0])*col/(width-1)
                origin=Vector((x,minimum[1]-1 if side==-1 else maximum[1]+1,z))
                hit,normal,face,distance=bvh.ray_cast(origin,Vector((0,-side,0)),maximum[1]-minimum[1]+2)
                if hit is None:line.append(None);missing+=1;continue
                tri=mesh.loop_triangles[face];a,b,c=[vertices[i] for i in tri.vertices]
                va=b-a;vb=c-a;vp=hit-a
                d00=va.dot(va);d01=va.dot(vb);d11=vb.dot(vb);d20=vp.dot(va);d21=vp.dot(vb)
                den=d00*d11-d01*d01
                if den<=1e-20:raise RuntimeError('Degenerate source interpolation triangle.')
                b1=(d11*d20-d01*d21)/den;b2=(d00*d21-d01*d20)/den
                uv=[mesh.uv_layers[0].data[i].uv for i in tri.loops]
                sample_uv=uv[0]*(1-b1-b2)+uv[1]*b1+uv[2]*b2
                line.append([hit.y,float(sample_uv.x),float(sample_uv.y),float(normal.y)])
            rows.append(line)
        fields.append({'rayOriginSide':side,'missingSamples':missing,'samples':rows})
    materials=[]
    for name in ['Canyon_Sandstone','Canyon_Cliff01','Canyon_Cliff02']:
        mat=bpy.data.materials[name]
        materials.append({'name':name,'images':[{'node':node.name,'image':node.image.name,'path':node.image.filepath} for node in mat.node_tree.nodes if node.type=='TEX_IMAGE' and node.image]})
    result={'source':source,'vertices':len(vertices),'triangles':len(triangles),'sourceBounds':[minimum,maximum],
            'sampleDomainXZMetres':domain,'width':width,'height':height,'fields':fields,'existingMaterials':materials,
            'sourceSaved':False,'scope':'Local CC0 surface data only; no visual or production acceptance.'}
finally:
    for obj in set(bpy.data.objects)-before_objects:bpy.data.objects.remove(obj,do_unlink=True)
    for mesh in set(bpy.data.meshes)-before_meshes:
        if mesh.users==0:bpy.data.meshes.remove(mesh)
    for mat in set(bpy.data.materials)-before_materials:
        if mat.users==0:bpy.data.materials.remove(mat)
    for im in set(bpy.data.images)-before_images:
        if im.users==0:bpy.data.images.remove(im)
    for obj,hidden,selected in states:obj.hide_set(hidden);obj.select_set(selected)
    bpy.context.view_layer.objects.active=active
    if set(bpy.data.objects)!=before_objects or set(bpy.data.meshes)!=before_meshes or set(bpy.data.materials)!=before_materials or set(bpy.data.images)!=before_images:
        raise RuntimeError('Owned import cleanup membership mismatch.')
print('CANYON_CC0_DETAIL06 '+json.dumps(result))
