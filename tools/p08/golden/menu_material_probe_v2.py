import bpy,json
root=bpy.data.objects['RB_Golden_MenuEnvironment'];rows=[]
for obj in root.children_recursive:
    if obj.type!='MESH' or 'EdgeStone_1' not in obj.name:continue
    indices={}
    for poly in obj.data.polygons:indices[poly.material_index]=indices.get(poly.material_index,0)+1
    rows.append({'name':obj.name,'dataName':obj.data.name,'meshMaterials':[m.name if m else None for m in obj.data.materials],
      'objectSlots':[{'index':s.slot_index,'link':s.link,'name':s.material.name if s.material else None} for s in obj.material_slots],
      'polygonIndices':indices,'activeIndex':obj.active_material_index,'polygons':len(obj.data.polygons)})
print('MENU_MATERIAL_PROBE '+json.dumps({'filepath':bpy.data.filepath,'rows':rows}))
