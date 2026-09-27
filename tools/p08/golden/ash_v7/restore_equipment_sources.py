"""Remove only the old baked equipment/snap, retain body, clone real authoring parts."""
import bpy,json
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];reports=[]
for level in range(3):
 obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];old=obj.data;obsolete=set(obj['v7_obsolete_snap_vertices']);keep=[]
 for p in old.polygons:
  if old.materials[p.material_index].name.startswith('AshV6_Equipment') or any(i in obsolete for i in p.vertices):continue
  keep.append(p)
 used=sorted(set(i for p in keep for i in p.vertices));mapping={i:j for j,i in enumerate(used)};positions=[old.vertices[i].co.copy() for i in used]
 weights=[[(obj.vertex_groups[g.group].name,g.weight) for g in old.vertices[i].groups] for i in used];expressions={k.name:[k.data[i].co.copy() for i in used] for k in old.shape_keys.key_blocks}
 faces=[(tuple(mapping[i] for i in p.vertices),p.material_index,p.use_smooth) for p in keep];uvs={l.name:[[l.data[i].uv.copy() for i in p.loop_indices] for p in keep] for l in old.uv_layers};mats=list(old.materials);names=[g.name for g in obj.vertex_groups]
 obj.shape_key_clear();mesh=bpy.data.meshes.new(obj.name+'_RetainedBody');mesh.from_pydata(positions,[],[p[0] for p in faces]);mesh.update();obj.data=mesh;obj.vertex_groups.clear()
 for name in names:obj.vertex_groups.new(name=name)
 for mat in mats:mesh.materials.append(mat)
 for p,data in zip(mesh.polygons,faces):p.material_index=data[1];p.use_smooth=data[2]
 for name,values in uvs.items():
  layer=mesh.uv_layers.new(name=name)
  for p,points in zip(mesh.polygons,values):
   for loop,point in zip(p.loop_indices,points):layer.data[loop].uv=point
 for i,values in enumerate(weights):
  for name,w in values:obj.vertex_groups[name].add([i],w,'REPLACE')
 for name,positions in expressions.items():
  key=obj.shape_key_add(name=name,from_mix=False);key.value=0
  for v,p in zip(key.data,positions):v.co=p
 for tag in ['v7_collar_vertices','v7_tab_vertices','v7_snap_vertices']:obj[tag]=[mapping[i] for i in obj[tag] if i in mapping]
 obj['v7_obsolete_snap_vertices']=[];reports.append({'lod':level,'retainedBodyVertices':len(mesh.vertices),'obsoleteSnapRemoved':len(obsolete)})
collection=bpy.data.collections.new('AshV7_Equipment');bpy.context.scene.collection.children.link(collection)
glass=bpy.data.materials.new('AshV7_AmberGlass_Source');glass.use_nodes=True;bs=glass.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.26,.095,.016,1);bs.inputs['Roughness'].default_value=.105;bs.inputs['Metallic'].default_value=0;bs.inputs['IOR'].default_value=1.47;bs.inputs['Alpha'].default_value=.38
glass['unity_surface']='URP Lit Transparent, Alpha blend, opacity0.38, metallic0, smoothness0.895';glass['constant_pbr_size']=512
created=[]
for old in list(bpy.data.collections['AshV6_Equipment_Source'].objects):
 obj=old.copy();obj.data=old.data.copy();obj.name=old.name.replace('Authored_AshV6_','AshV7_',1);collection.objects.link(obj);level=int(obj.name.split('_L')[1][0]);obj.hide_render=level!=0;obj.hide_set(level!=0)
 if 'CurvedAmberOptic' in obj.name:obj.data.materials.clear();obj.data.materials.append(glass)
 created.append(obj.name)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_SOURCE_PARTS '+json.dumps({'body':reports,'parts':len(created),'transparentGlassSource':glass.name,'oldV6MaterialsOrMapsModified':False,'visualAccepted':False}))
