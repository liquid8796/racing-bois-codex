import bpy,json
from mathutils import Vector
if '/Ash/V8/' not in bpy.data.filepath.replace('\\','/'):
    raise RuntimeError('Owned V8 source required')
scene=bpy.context.scene
skin=bpy.data.objects['AshV7_L0_Skin']
evaluated=skin.evaluated_get(bpy.context.evaluated_depsgraph_get())
points=[evaluated.matrix_world@Vector(value) for value in evaluated.bound_box]
slots=[]
for index,material in enumerate(skin.data.materials):
    polygons=[p for p in skin.data.polygons if p.material_index==index]
    vertices={v for p in polygons for v in p.vertices}
    slots.append(dict(index=index,material=material.name,polygons=len(polygons),vertices=len(vertices)))
def tree(layer):
    return dict(name=layer.name,excluded=layer.exclude,hideViewport=layer.hide_viewport,hideRender=layer.collection.hide_render,
                objects=len(layer.collection.objects),children=[tree(c) for c in layer.children])
print('ASH_V8_ACTOR '+json.dumps(dict(bounds=dict(minimum=[min(p[i] for p in points) for i in range(3)],maximum=[max(p[i] for p in points) for i in range(3)]),
    vertices=len(skin.data.vertices),polygons=len(skin.data.polygons),materials=slots,
    shapeKeys=[key.name for key in skin.data.shape_keys.key_blocks] if skin.data.shape_keys else [],
    collections=tree(bpy.context.view_layer.layer_collection),
    cameras=[dict(name=o.name,location=list(o.location),rotation=list(o.rotation_euler),kind=o.data.type,scale=o.data.ortho_scale) for o in scene.objects if o.type=='CAMERA'])))
