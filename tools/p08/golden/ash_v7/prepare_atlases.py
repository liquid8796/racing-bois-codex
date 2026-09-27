import bpy,bmesh,json
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
collection=bpy.data.collections['AshV7_Equipment'];source=bpy.data.collections.new('AshV7_Equipment_Source');bpy.context.scene.collection.children.link(source);rows=[]
for level in range(3):
 parts=[o for o in collection.objects if o.name.startswith('AshV7_L'+str(level)+'_')];glass=[o for o in parts if 'CurvedAmberOptic' in o.name];opaque=[o for o in parts if o not in glass]
 for obj in parts:
  backup=obj.copy();backup.data=obj.data.copy();backup.name='Authored_'+obj.name;source.objects.link(backup);backup.hide_render=True;backup.hide_set(True)
 for group,suffix in [(opaque,'Equipment'),(glass,'Glass')]:
  bpy.ops.object.select_all(action='DESELECT')
  for obj in group:obj.hide_set(False);obj.select_set(True)
  active=group[0];bpy.context.view_layer.objects.active=active;bpy.ops.object.join();active.name='AshV7_L'+str(level)+'_'+suffix
  for mod in list(active.modifiers):active.modifiers.remove(mod)
  # Test the actual Blender triangulation, repair only a bad quad diagonal.
  active.data.calc_loop_triangles();bad=set()
  for tri in active.data.loop_triangles:
   a,b,c=[active.data.vertices[i].co for i in tri.vertices]
   if (b-a).cross(c-a).length_squared<=1e-16:bad.add(tri.polygon_index)
  if bad:
   bm=bmesh.new();bm.from_mesh(active.data);bm.faces.ensure_lookup_table();faces=[bm.faces[i] for i in bad];assert all(len(f.verts)==4 for f in faces);bmesh.ops.triangulate(bm,faces=faces,quad_method='ALTERNATE');bm.to_mesh(active.data);bm.free()
  while len(active.data.uv_layers)>1:active.data.uv_layers.remove(active.data.uv_layers[-1])
  active.data.uv_layers[0].name='UV0';active.data.uv_layers.active_index=0
  if suffix=='Equipment':
   bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.151917,island_margin=.006,area_weight=0,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT');active['atlas_resolution']=[2048,1024,512][level]
  else:
   mod=active.modifiers.new('Preserved head rig','ARMATURE');mod.object=rig
  active.hide_render=level!=0;active.hide_set(level!=0)
  rows.append({'lod':level,'part':suffix,'retriangulatedQuads':len(bad),'vertices':len(active.data.vertices)})
source.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7_AtlasSource.blend',compress=False)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_ATLASES '+json.dumps({'parts':rows,'glassExcludedFromOpaqueAtlases':True,'visualAccepted':False}))
