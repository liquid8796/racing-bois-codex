import bpy,bmesh,math,json
from mathutils import Vector,noise
ROOT='D:/Project/Unity/racing-bois/';scene=bpy.context.scene;root=bpy.data.objects['RB_Golden_MenuEnvironment']
R=Vector((-.52999894,.84799830,0));D=Vector((-.84799830,-.52999894,0));UP=Vector((0,0,1))
def p(u,y,d):return R*u+D*d+UP*y
def recalc(mesh):
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
heights={'LeftMiddle':41,'MiddleRidge':38,'MiddleRecess':29,'RightRidge':36,'FarLeft':38,'FarCenter':45,'FarRight':55,'FarHorizon':67}
for key,wanted in heights.items():
    sample=bpy.data.objects['Menu_L0_'+key];lo=min(v.co.z for v in sample.data.vertices);hi=max(v.co.z for v in sample.data.vertices)
    for level in range(3):
        obj=bpy.data.objects['Menu_L%d_'%level+key]
        for v in obj.data.vertices:v.co.z=lo+(v.co.z-lo)*wanted/(hi-lo)
        recalc(obj.data)
def ground_height(u,d):
    if d<=1.8:return -.025+.007*noise.noise(Vector((u*.5,d*.5,11)))
    drop=min(1,(d-1.8)/17)
    h=-.025-32*(drop*drop*(3-2*drop))+noise.noise(Vector((u*.035,d*.025,12)))*drop*3
    # A continuous talus bed supports the road bench; it stays beneath the road
    # and its descending authored shoulder instead of exposing a floating ribbon.
    if d>10:
        nearest=999;road_y=-8
        for n in range(96):
            s=n;uu=-16-13*math.sin(s*math.pi/42)+.02*s;dd=18+s*1.6
            distance=math.hypot(u-uu,d-dd)
            if distance<nearest:nearest=distance;road_y=-8-.055*s
        h=max(h,road_y-.35-.78*max(0,nearest-3.6))
    return h
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    key=obj.name.split('_',2)[2]
    if key in ['Pullout','EdgeGravel','NearValley']:
        for v in obj.data.vertices:
            u=v.co.dot(R);d=v.co.dot(D)
            if key=='Pullout':d=-16+(d+16)*17.6/21.5
            elif key=='EdgeGravel':d=1.6+(d-5.5)*2.4/4.5
            else:d=4+(d-10)*156/150
            v.co=p(u,ground_height(u,d),d)
        recalc(obj.data)
    elif key.startswith('EdgeStone_') or key.startswith('RightOverlookStone_'):
        lo=Vector([min(v.co[i] for v in obj.data.vertices) for i in range(3)]);hi=Vector([max(v.co[i] for v in obj.data.vertices) for i in range(3)]);center=(lo+hi)*.5
        d=center.dot(D);u=center.dot(R)
        if key.startswith('EdgeStone_'):new_d=1.6+(d-5.5)*2.4/4.5;new_u=u
        else:new_d=2.0+(d-5.7);new_u=u-3.1
        translation=R*(new_u-u)+D*(new_d-d)+UP*(ground_height(new_u,new_d)-lo.z)
        for v in obj.data.vertices:v.co+=translation
        recalc(obj.data)
fog=bpy.data.objects.get('Canyon_AerialPerspective')
if fog:
    fog.location=p(100,70,470);fog.rotation_euler=(0,0,math.atan2(R.y,R.x));fog.scale=(1000,900,180)
    for node in fog.data.materials[0].node_tree.nodes:
        if node.type=='VOLUME_SCATTER':node.inputs['Density'].default_value=.0013
for obj in scene.objects:
    if obj.type=='LIGHT' and obj.data.type=='SUN':obj.data.energy=1.5;obj.data.color=(1,.88,.71)
scene.render.filepath=ROOT+'docs/p08/golden/menu-environment/v1/composition-02.png'
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/MenuEnvironment/V1/RB_Golden_MenuEnvironment.blend')
print('MENU_COMPOSITION_02 '+json.dumps({'pulloutEdgeDepth':1.6,'roadBelowStandingPlane':True,'recedingCliffSilhouette':heights,'visualAccepted':False}))
bpy.ops.render.render(write_still=True)
