"""Geometry-first helmet/goggle refit from the locked Ash reference; V6 only."""
import bpy,bmesh,math,json
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/';assert '/Ash/V6/' in bpy.data.filepath.replace('\\','/')
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
previous=bpy.data.collections.get('AshV6_Equipment')
if previous:
    for obj in list(previous.objects):
        assert obj.name.startswith('AshV6_L'),'Unexpected object in V6 equipment collection'
        bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.collections.remove(previous)
collection=bpy.data.collections.new('AshV6_Equipment');scene.collection.children.link(collection)
def material(name,color,rough,metal=0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m
enamel=bpy.data.materials['AshV4_HelmetEnamel_Baked']
leather=material('AshV6_HarnessLeather',(.032,.018,.010),.64)
foam=material('AshV6_OpticalGasket',(.014,.013,.011),.81)
metal=material('AshV6_FrameBronze',(.24,.17,.086),.34,.82)
hardware=material('AshV6_DarkFastener',(.055,.052,.046),.43,.80)
glass=bpy.data.materials['AshV2_AmberLens_Baked']
objects=[];LEVEL=0
def build(name,verts,faces,mat,uv=None):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new('AshV6_L'+str(LEVEL)+'_'+name,data);collection.objects.link(obj);obj.parent=rig;data.materials.append(mat)
    layer=data.uv_layers.new(name='UV0')
    for p in data.polygons:
        p.use_smooth=True
        for j,i in enumerate(p.loop_indices):
            if uv:layer.data[i].uv=uv[data.loops[i].vertex_index]
            else:layer.data[i].uv=(.45+.03*math.cos(j*math.tau/len(p.vertices)),.45+.03*math.sin(j*math.tau/len(p.vertices)))
    group=obj.vertex_groups.new(name='RB_P06_Rider_L0_Head');group.add(list(range(len(verts))),1,'REPLACE')
    mod=obj.modifiers.new('Preserved Ash head rig','ARMATURE');mod.object=rig
    obj.hide_render=LEVEL!=0;obj.hide_set(LEVEL!=0);obj['v6_geometry_candidate']=True;objects.append(obj);return obj
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
center=Vector((0,-.041,1.706));rx=.112;ry=.124;rz=.148
def edge_theta(phi):
    a=abs((phi+math.pi)%math.tau-math.pi)
    brow_curve=.085*math.sin(min(1,a/.70)*math.pi*.5)**2*(1-smooth((a-.70)/.40))
    return 1.27+brow_curve+.86*smooth((a-.58)/.65)-.22*smooth((a-1.75)/(math.pi-1.75))
def shell_point(phi,t):return center+Vector((rx*math.sin(t)*math.sin(phi),-ry*math.sin(t)*math.cos(phi),rz*math.cos(t)))
def shell_normal(p):
    q=p-center;return Vector((q.x/(rx*rx),q.y/(ry*ry),q.z/(rz*rz))).normalized()
def ribbon_sweep(name,points,width,depth,mat,sides=8):
    verts=[];faces=[];uv=[]
    for i,(p,n) in enumerate(points):
        t=(points[min(len(points)-1,i+1)][0]-points[max(0,i-1)][0]).normalized();a=t.cross(n).normalized();b=t.cross(a).normalized()
        for j in range(sides):
            angle=math.tau*j/sides;verts.append(p+a*width*math.cos(angle)+b*depth*math.sin(angle));uv.append((j/sides,i/max(1,len(points)-1)))
            if i:faces.append(((i-1)*sides+j,(i-1)*sides+(j+1)%sides,i*sides+(j+1)%sides,i*sides+j))
    faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(points)-1)*sides+j for j in range(sides))])
    return build(name,verts,faces,mat,uv)
reports=[]
for LEVEL,cols,rows,optics in [(0,72,22,64),(1,48,15,40),(2,24,10,24)]:
    verts=[];faces=[];uv=[]
    for layer in range(2):
        for r in range(rows):
            fraction=.014+.986*r/(rows-1)
            for j in range(cols):
                phi=math.tau*j/cols;p=shell_point(phi,edge_theta(phi)*fraction);n=shell_normal(p)
                verts.append(p-n*(.0048*layer));uv.append((.025+.95*j/cols,.025+.95*fraction))
                if r:
                    a=layer*rows*cols+(r-1)*cols+j;b=layer*rows*cols+(r-1)*cols+(j+1)%cols;c=b+cols;d=a+cols
                    faces.append((a,b,c,d) if layer==0 else (d,c,b,a))
        cap=[layer*rows*cols+j for j in range(cols)];faces.append(tuple(reversed(cap)) if layer==0 else tuple(cap))
    total=rows*cols
    for j in range(cols):a=(rows-1)*cols+j;b=(rows-1)*cols+(j+1)%cols;faces.append((a,b,b+total,a+total))
    shell=build('HelmetShell',verts,faces,enamel,uv)
    tree=BVHTree.FromPolygons([v.co for v in shell.data.vertices],[tuple(p.vertices) for p in shell.data.polygons],all_triangles=False)
    rim=[]
    for j in range(cols+1):
        phi=math.tau*j/cols;p=shell_point(phi,edge_theta(phi));n=shell_normal(p);rim.append((p-n*.0019,n))
    ribbon_sweep('RolledHelmetGasket',rim,.0038,.0030,foam,8 if LEVEL==0 else 6)
    for sign in [-1,1]:
        pad=[]
        for i in range(20 if LEVEL==0 else 12):
            fraction=i/(19 if LEVEL==0 else 11);phi=sign*(.69+.69*fraction);p=shell_point(phi,edge_theta(phi));n=shell_normal(p)
            pad.append((p-n*.010,n))
        ribbon_sweep('LayeredCheekPad',pad,.010,.0048,foam,10 if LEVEL==0 else 6)
    # The strap is projected to the shell for every sample/row. It never
    # vanishes inside a stale fixed ellipse. Rear continuation remains a
    # reference ambiguity, so this is an unaccepted construction candidate.
    verts=[];faces=[];uv=[];ncols=96 if LEVEL==0 else 56 if LEVEL==1 else 32
    for layer in range(2):
        for row in range(3):
            for i in range(ncols):
                phi=.91+(math.tau-1.82)*i/(ncols-1);z=1.754+.035*math.cos(phi)+(row-1)*.009
                d=Vector((math.sin(phi),-math.cos(phi),0));p,n,index,dist=tree.ray_cast(Vector((0,center.y,z))+d*.4,-d,.8)
                assert p is not None,'Strap surface projection failed'
                verts.append(p+n*(.0040-.0018*layer));uv.append((i/(ncols-1),row*.5))
                if row and i:
                    a=layer*3*ncols+(row-1)*ncols+i-1;b=a+1;c=b+ncols;didx=a+ncols
                    faces.append((a,b,c,didx) if layer==0 else (didx,c,b,a))
    count=3*ncols;border=list(range(ncols))+[ncols*2-1,ncols*3-1]+list(range(ncols*3-2,ncols*2-1,-1))+[ncols]
    for i,a in enumerate(border):b=border[(i+1)%len(border)];faces.append((a,b,b+count,a+count))
    build('ShellFittedGoggleBand',verts,faces,leather,uv)
    def outline(theta,half_x=.041,half_z=.022):
        c=math.cos(theta);s=math.sin(theta);power=2/3.4
        return Vector((math.copysign(abs(c)**power,c)*half_x,math.copysign(abs(s)**power,s)*half_z))
    goggle_centers=[]
    for sign in [-1,1]:
        p,n,index,dist=tree.ray_cast(Vector((sign*.044,-1,1.793)),Vector((0,1,0)),2)
        assert p is not None
        center_lens=p+n*.012;n=Vector((n.x*.60,n.y,n.z*.87)).normalized();h=(Vector((1,0,0))-n*n.x).normalized();v=n.cross(h).normalized();goggle_centers.append(center_lens)
        # Thin stamped lip: a closed annular profile, not a thick round tube.
        verts=[];faces=[];profiles=[(.0013,.0005),(-.0013,.0005),(-.0013,-.0012),(.0013,-.0012)]
        for expansion,depth in profiles:
            for i in range(optics):
                q=outline(math.tau*i/optics,.042+expansion,.023+expansion);verts.append(center_lens+h*q.x+v*q.y+n*depth)
        for r in range(4):
            for i in range(optics):j=(i+1)%optics;faces.append((r*optics+i,r*optics+j,((r+1)%4)*optics+j,((r+1)%4)*optics+i))
        build('StampedGoggleRim',verts,faces,metal)
        # Dark backing reaches the actual shell around its whole outline.
        verts=[];faces=[]
        for layer in range(4):
            for i in range(optics):
                q=outline(math.tau*i/optics,.0445 if layer in [0,3] else .0385,.0255 if layer in [0,3] else .0195)
                point=center_lens+h*q.x+v*q.y-n*.0018
                if layer>=2:
                    near,normal,index,distance=tree.find_nearest(point-n*.015)
                    assert near is not None;point=near+normal*.0018
                verts.append(point)
        for r in range(4):
            for i in range(optics):j=(i+1)%optics;faces.append((r*optics+i,r*optics+j,((r+1)%4)*optics+j,((r+1)%4)*optics+i))
        build('ConformingGoggleSocket',verts,faces,foam)
        # Actual closed optical lens with continuous curvature.
        verts=[];faces=[];uv=[];rings=6 if LEVEL==0 else 4 if LEVEL==1 else 3
        for layer in range(2):
            start=len(verts);verts.append(center_lens+n*(.0032-layer*.0016));uv.append((.6006,.5186))
            for ring in range(1,rings+1):
                radius=ring/rings
                for i in range(optics):
                    q=outline(math.tau*i/optics,.0408,.0214)*radius
                    verts.append(center_lens+h*q.x+v*q.y+n*(.0032*(1-radius*radius)-layer*.0016));uv.append((.6006+q.x*.24,.5186+q.y*.28))
                    if ring==1:face=(start,start+1+i,start+1+(i+1)%optics)
                    else:
                        a=start+1+(ring-1)*optics+i;b=start+1+(ring-1)*optics+(i+1)%optics;face=(a,b,b-optics,a-optics)
                    faces.append(face if layer==0 else tuple(reversed(face)))
        per=1+rings*optics
        for i in range(optics):a=1+(rings-1)*optics+i;b=1+(rings-1)*optics+(i+1)%optics;faces.append((a,a+per,b+per,b))
        build('CurvedAmberOptic',verts,faces,glass,uv)
    bridge=[]
    for i in range(13):
        t=i/12;x=-.011+.022*t;z=1.793-.006*math.sin(t*math.pi);bridge.append((Vector((x,-.164,z)),Vector((0,-1,0))))
    ribbon_sweep('ShapedNoseBridge',bridge,.0048,.0018,leather,6)
    reports.append({'lod':LEVEL,'goggleCenters':[list(p) for p in goggle_centers],'helmetOuterRadii':[rx,ry,rz],'metalLipWidth':.0026,'lensOutlineFullSize':[.0816,.0428],'strapWidth':.018,'shellThickness':.0048})
rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',compress=False)
print('ASH_V6_EQUIPMENT '+json.dumps({'specifications':reports,'objects':len(objects),'geometryOnlyCandidate':True,'productionAccepted':False,'newImageGenerationUsed':False}))
