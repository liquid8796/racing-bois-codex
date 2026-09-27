"""Read-only saved-revision observations; no visual-acceptance inference."""
import bpy,bmesh,json,math
ROOT='D:/Project/Unity/racing-bois/'
source=ROOT+'ArtSource/P08/Golden/Ash/RB_Golden_Ash.blend'
bpy.ops.wm.open_mainfile(filepath=source,load_ui=False,use_scripts=False)
root=bpy.data.objects['RB_Golden_Ash'];rig=bpy.data.objects['RB_P06_Rider_Rig']
def path(obj):
    names=[]
    while obj and obj!=root:names.append(obj.name);obj=obj.parent
    return '/'.join(reversed(names))
records=[]
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    obj.data.calc_loop_triangles();bad_weights=0;max_influences=0;degenerate=0
    for vertex in obj.data.vertices:
        weights=[g.weight for g in vertex.groups if g.weight>1e-7];max_influences=max(max_influences,len(weights))
        if not weights or abs(sum(weights)-1)>1e-4 or len(weights)>4:bad_weights+=1
    for tri in obj.data.loop_triangles:
        a,b,c=[obj.data.vertices[i].co for i in tri.vertices]
        if (b-a).cross(c-a).length<1e-11:degenerate+=1
    bm=bmesh.new();bm.from_mesh(obj.data)
    nonmanifold=sum(not e.is_manifold for e in bm.edges);bm.free()
    keys=obj.data.shape_keys.key_blocks
    expressions={key:sum((keys[key].data[i].co-v.co).length_squared>1e-12 for i,v in enumerate(obj.data.vertices)) for key in ['Happy','Focused']}
    uv=obj.data.uv_layers.active
    records.append({'name':obj.name,'path':path(obj),'vertices':len(obj.data.vertices),'triangles':len(obj.data.loop_triangles),'materials':[m.name for m in obj.data.materials],
      'nonmanifoldEdges':nonmanifold,'degenerateTriangles':degenerate,'badWeights':bad_weights,'maxInfluences':max_influences,'expressionVertices':expressions,
      'uvLoops':len(uv.data) if uv else 0,'finiteUV':all(math.isfinite(v) for item in uv.data for v in item.uv) if uv else False})
bones=[]
for bone in rig.data.bones:
    names=[bone.name];parent=bone.parent
    while parent:names.append(parent.name);parent=parent.parent
    bones.append(path(rig)+'/'+'/'.join(reversed(names)))
result={'source':str(source),'meshes':records,'rigPath':path(rig),'bonePaths':bones,'boneCount':len(bones),'visualAcceptance':'failed: actual face and body previews remain mannequin-like; garment panels intersect','animationContactAcceptance':'not attempted after visual rejection','productionReady':False,
  'uvPolicy':'Dedicated head sphere UV; original full-field garment/surface textures intentionally tiled/shared across components. Final visual density and overlap review remains required.'}
print('ASH_SOURCE_OBSERVATIONS '+json.dumps(result))
