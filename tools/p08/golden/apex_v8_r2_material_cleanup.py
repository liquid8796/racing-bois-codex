"""Remove only hidden prior-candidate components in the task-owned scene.

All V8/R1 files remain immutable. This repairs the first R2 in-memory build.
"""
import bpy
root=bpy.data.objects['RB_Golden_Apex_v8_r2']
for obj in list(bpy.data.objects):
    if obj.name.startswith('Source_'):bpy.data.objects.remove(obj,do_unlink=True)
for data in list(bpy.data.meshes):
    if data.users==0:bpy.data.meshes.remove(data)
for mat in list(bpy.data.materials):
    if mat.name.startswith('Apex_') and mat.users==0:bpy.data.materials.remove(mat)
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    for mat in obj.data.materials:
        base=mat.name.split('.')[0]
        if base!=mat.name:
            if bpy.data.materials.get(base):raise RuntimeError('Conflicting live material '+base)
            mat.name=base
print('R2 material identities normalized without changing R1 files.')
