"""Read-only clarification of candidate03 mesh-local volume measurements."""
import bpy,json
if not bpy.data.filepath.replace('\\','/').endswith('/Canyon/V19/RB_Golden_Canyon_V19_03.blend'):
    raise RuntimeError('Expected frozen candidate03.')
rows=[]
for index in range(33,45):
    for level in range(3):
        obj=bpy.data.objects['Canyon_L%d_Far_%02d'%(level,index)]
        rows.append({'object':obj.name,'worldMatrixDeterminant':obj.matrix_world.determinant(),
                     'materials':[slot.material.name for slot in obj.material_slots],
                     'primaryUvLayer':obj.data.uv_layers[0].name})
print('CANYON_V19_TRANSFORMS03 '+json.dumps({'source':bpy.data.filepath,'rows':rows,
    'sourceSaved':False,'visualAccepted':False,
    'volumeClarification':'Original author audit volume is mesh-local. World volume uses absolute matrix determinant.',
    'spacingClarification':'Original author intervals measure the undeformed reference plan; row scale, talus expansion and relief alter actual surface distances.'}))
