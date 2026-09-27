import bpy,bmesh,math,json
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/';assert '/Ash/V5/' in bpy.data.filepath.replace('\\','/')
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
collection=bpy.data.collections['AshV5_Equipment'];leather=bpy.data.materials['AshV5_HarnessLeather'];metal=bpy.data.materials['AshV5_DarkFastener']
skin=bpy.data.objects['AshV5_L0_Skin'].data
skin_tree=BVHTree.FromPolygons([v.co for v in skin.vertices],[tuple(p.vertices) for p in skin.polygons if skin.materials[p.material_index].name=='AshV4_Skin_Baked' and min(skin.vertices[i].co.z for i in p.vertices)>1.55],all_triangles=False)
LEVEL=0;created=[]
def mesh(name,verts,faces,mat):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update();bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new('AshV5_L'+str(LEVEL)+'_'+name,data);collection.objects.link(obj);obj.parent=rig;data.materials.append(mat);uv=data.uv_layers.new(name='UV0')
    for p in data.polygons:
        p.use_smooth=True;t=p.normal.orthogonal().normalized();b=p.normal.cross(t).normalized()
        for loop in p.loop_indices:
            v=data.vertices[data.loops[loop].vertex_index].co;uv.data[loop].uv=(v.dot(t),v.dot(b))
    g=obj.vertex_groups.new(name='RB_P06_Rider_L0_Head');g.add(list(range(len(verts))),1,'REPLACE');m=obj.modifiers.new('Preserved Ash head rig','ARMATURE');m.object=rig
    obj.hide_render=LEVEL!=0;obj.hide_set(LEVEL!=0);created.append(obj);return obj
def strip(name,points,normal,width,depth):
    verts=[];faces=[];sides=8 if LEVEL==0 else 6
    for i,p in enumerate(points):
        tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized();a=tangent.cross(normal).normalized();b=tangent.cross(a).normalized()
        for j in range(sides):
            angle=j*math.tau/sides;verts.append(p+a*width*math.cos(angle)+b*depth*math.sin(angle))
            if i:faces.append(((i-1)*sides+j,(i-1)*sides+(j+1)%sides,i*sides+(j+1)%sides,i*sides+j))
    faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(points)-1)*sides+j for j in range(sides))]);return mesh(name,verts,faces,leather)
reports=[]
for LEVEL in range(3):
    old=bpy.data.objects.get('AshV5_L'+str(LEVEL)+'_ShapedNoseBridge')
    if old:bpy.data.objects.remove(old,do_unlink=True)
    shell=bpy.data.objects['AshV5_L'+str(LEVEL)+'_HelmetShell'];tree=BVHTree.FromPolygons([v.co for v in shell.data.vertices],[tuple(p.vertices) for p in shell.data.polygons],all_triangles=False)
    endpoints=[]
    for sign in [-1,1]:
        p,n,index,d=tree.ray_cast(Vector((sign*.046,-1,1.793)),Vector((0,1,0)),2);c=p+n*.012;n=Vector((n.x*.60,n.y,n.z*.87)).normalized();h=(Vector((1,0,0))-n*n.x).normalized();v=n.cross(h).normalized()
        endpoints.append(c+h*(-sign*.037)+v*(-.011)-n*.0004)
        anchor=c+h*(sign*.040)-n*.006
        phi=sign*.91;z=1.754+.035*math.cos(phi);direction=Vector((math.sin(phi),-math.cos(phi),0))
        target,tn,index,d=tree.ray_cast(Vector((0,-.041,z))+direction*.4,-direction,.8);target+=tn*.003
        points=[anchor.lerp(target,i/12)+n*.0015*math.sin(i/12*math.pi) for i in range(13)]
        strip('GoggleSideAttachment',points,n,.0075,.0010)
        for angle,offset in [(1.02,.20),(1.12,.10),(1.25,.04)]:
            phi=sign*angle
            a=abs(phi);sm=max(0,min(1,(a-.58)/.65));sm=sm*sm*(3-2*sm);theta=1.27+.86*sm-offset
            guide=Vector((.112*math.sin(theta)*math.sin(phi),-.041-.124*math.sin(theta)*math.cos(phi),1.706+.148*math.cos(theta)))
            normal=Vector((guide.x/(.112**2),(guide.y+.041)/(.124**2),(guide.z-1.706)/(.148**2))).normalized();center=guide+normal*.001
            tangent=normal.orthogonal().normalized();across=normal.cross(tangent).normalized();verts=[];faces=[];count=16 if LEVEL==0 else 10
            for layer,radius in [(0,.0035),(1,.0030)]:
                for i in range(count):t=i*math.tau/count;verts.append(center+normal*(layer*.0012)+radius*(tangent*math.cos(t)+across*math.sin(t)))
            for i in range(count):j=(i+1)%count;faces.append((i,j,j+count,i+count))
            faces.extend([tuple(range(count-1,-1,-1)),tuple(range(count,count*2))]);mesh('HelmetEdgeRivet',verts,faces,metal)
    bridge=[endpoints[0].lerp(endpoints[1],i/16)+Vector((0,-.003*math.sin(i/16*math.pi),-.006*math.sin(i/16*math.pi))) for i in range(17)]
    strip('FittedNoseBridge',bridge,Vector((0,-1,0)),.0045,.0012)
    jaw=[]
    for sign in [-1,1]:
        phi=sign*1.55;theta=2.08
        anchor=Vector((.112*math.sin(theta)*math.sin(phi),-.041-.124*math.sin(theta)*math.cos(phi),1.706+.148*math.cos(theta)))
        controls=[anchor,Vector((sign*.077,-.056,1.603)),Vector((sign*.047,-.115,1.590)),Vector((sign*.025,-.130,1.575)),Vector((0,-.134,1.568))]
        points=[]
        for k in range(len(controls)-1):
            p0=controls[max(0,k-1)];p1=controls[k];p2=controls[k+1];p3=controls[min(k+2,len(controls)-1)]
            for j in range(8):
                t=j/8;points.append(.5*(2*p1+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
        points.append(controls[-1]);verts=[];faces=[];sides=8
        for i,p in enumerate(points):
            t=i/(len(points)-1);normal=Vector((sign*max(.08,1-t),-.35*(1-t),-.75*t)).normalized()
            tangent=(points[min(i+1,len(points)-1)]-points[max(i-1,0)]).normalized();a=tangent.cross(normal).normalized();b=tangent.cross(a).normalized()
            for j in range(sides):
                angle=j*math.tau/sides;verts.append(p+a*.0045*math.cos(angle)+b*.0009*math.sin(angle))
                if i:faces.append(((i-1)*sides+j,(i-1)*sides+(j+1)%sides,i*sides+(j+1)%sides,i*sides+j))
        faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(points)-1)*sides+j for j in range(sides))]);mesh('JawFollowingChinStrap',verts,faces,leather)
        jaw.append([list(p) for p in controls])
    reports.append({'lod':LEVEL,'bridgeEndpoints':[list(p) for p in endpoints],'helmetAnchoredStrapGuides':jaw,'jawClearanceStillNeedsVisualCheck':True})
rig.animation_data.action=bpy.data.actions['RB_Idle'];bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V5/RB_Golden_Ash_V5.blend',compress=False)
print('ASH_V5_CONNECTIONS '+json.dumps({'levels':reports,'parts':len(created),'allNewGeometryBoundToExistingHead':True,'visualAccepted':False}))
