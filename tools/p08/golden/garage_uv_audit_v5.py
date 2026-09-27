import bpy,json

def uv_area(mesh,layer,poly):
    points=[layer.data[i].uv for i in poly.loop_indices]
    return abs(sum(points[i].x*points[(i+1)%len(points)].y-points[(i+1)%len(points)].x*points[i].y for i in range(len(points)))*.5)

rows=[]
for o in bpy.data.objects:
    if o.type!='MESH' or not o.name.startswith('Garage_L'):continue
    mesh=o.data; layers=[]
    for layer in mesh.uv_layers:
        degenerate=[p.index for p in mesh.polygons if uv_area(mesh,layer,p)<1e-14 and p.area>1e-12]
        outside=sum(1 for p in layer.data if p.uv.x<0 or p.uv.x>1 or p.uv.y<0 or p.uv.y>1)
        layers.append({'name':layer.name,'zeroAreaFaces':len(degenerate),'zeroAreaFaceSample':degenerate[:8],'outsideUnitLoops':outside})
    rows.append({'name':o.name,'vertices':len(mesh.vertices),'faces':len(mesh.polygons),'loops':len(mesh.loops),'layers':layers})
materials=[]
for name in ['Garage_Floor','Garage_PowderSteel','Garage_ToolSteel','Garage_HelmetShell']:
    material=bpy.data.materials.get(name)
    if material is None:continue
    bs=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    slots={}
    for socket in ['Metallic','Roughness','IOR','Coat Weight','Coat Roughness','Coat IOR']:
        value=bs.inputs.get(socket)
        if value is not None:slots[socket]={'value':value.default_value,'linked':value.is_linked}
    materials.append({'name':name,'principled':slots,'normalStrengths':[n.inputs['Strength'].default_value for n in material.node_tree.nodes if n.type=='NORMAL_MAP']})
scene=bpy.context.scene
print('GARAGE_V5_AUDIT '+json.dumps({'source':bpy.data.filepath,'objects':rows,'materials':materials,'camera':{'name':scene.camera.name,'location':list(scene.camera.location),'rotation':list(scene.camera.rotation_euler),'lens':scene.camera.data.lens},'render':{'filepath':scene.render.filepath,'x':scene.render.resolution_x,'y':scene.render.resolution_y,'view':scene.view_settings.view_transform,'exposure':scene.view_settings.exposure},'lights':[{'name':o.name,'type':o.data.type,'power':o.data.energy,'color':list(o.data.color)} for o in bpy.data.objects if o.type=='LIGHT']}))
