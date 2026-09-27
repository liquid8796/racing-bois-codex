"""Dedicated menu overlook from locked main-v2; direct Blender9877 only."""
import bpy,bmesh,math,json,random
from mathutils import Vector,Matrix,noise
ROOT='D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\','/').endswith('Canyon/V16/RB_Golden_Canyon.blend')
scene=bpy.context.scene;source_root=bpy.data.objects['RB_Golden_Canyon']
sources={o.name:o for o in source_root.children_recursive if o.type=='MESH'}
scene.name='RB_MenuOverlook_Authoring'
root=bpy.data.objects.new('RB_Golden_MenuEnvironment',None);scene.collection.objects.link(root)
R=Vector((-.52999894,.84799830,0));D=Vector((-.84799830,-.52999894,0));UP=Vector((0,0,1))
def cv(p):return Vector((p[0],p[2],p[1]))
def p(u,y,d):return R*u+D*d+UP*y
made=[]
def normals(mesh):
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
def clone(suffix,key,transform):
    group=[]
    for level in range(3):
        old=sources['Canyon_L%d_'%level+suffix];obj=old.copy();obj.data=old.data.copy();scene.collection.objects.link(obj)
        obj.parent=root;obj.name='Menu_L%d_'%level+key;obj.matrix_world=Matrix.Identity(4)
        for wanted,original in zip(obj.data.vertices,old.data.vertices):wanted.co=transform(old.matrix_world@original.co)
        normals(obj.data);obj.hide_set(level!=0);obj.hide_render=level!=0
        made.append(obj);group.append(obj)
    return group
def source_center(s):return -18*(1-math.cos(max(0,min(80,s))*math.pi/160))
def source_tangent(s):return -18*math.pi/160*math.sin(max(0,min(80,s))*math.pi/160)
def curve(s):return Vector((-16-13*math.sin(s*math.pi/42)+.02*s,18+s*1.6,-8-.055*s))
def warp(v):
    s=v.y
    for step in range(5):
        angle=math.atan(source_tangent(s));w=(v.x-source_center(s))/math.cos(angle);s=v.y+w*math.sin(angle)
    c=curve(s);t=curve(s+.01)-curve(s-.01);normal=Vector((t.y,-t.x,0)).normalized()
    return p(c.x+normal.x*w,c.z+v.z,c.y+normal.y*w)
# Distant route and its authored structural rail move together. Nothing crosses
# the hero standing plane; the closest road elevation is eight metres below it.
for suffix in list(sources):
    if '_L0_' not in suffix:continue
    key=suffix.split('_L0_',1)[1]
    if any(key.startswith(prefix) for prefix in ['Road_','Shoulder_','Canyon_WhitePaint','Canyon_YellowPaint','Guardrail_','Reflectors_','Sage_Tile','Branches_Tile','Grass_Tile']):
        clone(key,'Valley_'+key,warp)

def scan(suffix,key,u,d,bottom,width,depth,height,yaw=0):
    original=sources['Canyon_L0_'+suffix]
    vs=[original.matrix_world@v.co for v in original.data.vertices]
    lo=Vector([min(v[i] for v in vs) for i in range(3)]);hi=Vector([max(v[i] for v in vs) for i in range(3)])
    center=(lo+hi)*.5;size=hi-lo;c=math.cos(yaw);s=math.sin(yaw)
    def transform(v):
        a=(v.x-center.x)/size.x*depth;b=(v.y-center.y)/size.y*width
        # Source visible cliff +X faces the menu camera (-D). Rotation is proper,
        # never a negative-scale mirror, and every LOD uses the same reference.
        uu=b*c+a*s;dd=b*s-a*c
        return p(u+uu,bottom+(v.z-lo.z)/size.z*height,d+dd)
    return clone(suffix,key,transform)

formations=[
 ('Cliff_00','LeftNear',-33,47,-26,38,17,59,-.08),
 ('Cliff_02','LeftMiddle',-28,77,-30,43,20,61,.06),
 ('Cliff_03','MiddleRidge',-9,118,-31,59,29,65,-.1),
 ('Cliff_05','MiddleRecess',28,165,-33,65,34,54,.15),
 ('Cliff_04','RightRidge',87,245,-35,114,45,70,-.06),
 ('Bend_01','RightLowLedge',19,65,-33,39,31,19,.05),
 ('Bend_03','LeftLowLedge',-46,98,-35,50,26,27,-.1),
 ('Bend_05','ValleyTerrace',12,128,-34,73,40,25,.1),
 ('Far_33','FarLeft',-100,360,-33,200,64,98,.0),
 ('Far_35','FarCenter',48,480,-35,255,85,107,.08),
 ('Far_39','FarRight',255,610,-40,310,115,120,-.08),
 ('Far_43','FarHorizon',30,820,-42,520,175,147,.04),
]
for args in formations:scan(*args)

def height(u,d):
    if d<=7.5:return -.025 + .007*noise.noise(Vector((u*.5,d*.5,11)))
    drop=min(1,(d-7.5)/18)
    return -.025-32*(drop*drop*(3-2*drop))+noise.noise(Vector((u*.035,d*.025,12)))*drop*3

def ground(key,umin,umax,dmin,dmax,steps,material):
    for level,step in enumerate(steps):
        nx=max(1,int(math.ceil((umax-umin)/step)));ny=max(1,int(math.ceil((dmax-dmin)/step)))
        verts=[];uvs=[]
        for j in range(ny+1):
            d=dmin+(dmax-dmin)*j/ny
            for i in range(nx+1):
                u=umin+(umax-umin)*i/nx;verts.append(p(u,height(u,d),d));uvs.append((u/2,d/2))
        faces=[]
        for j in range(ny):
            for i in range(nx):
                a=j*(nx+1)+i;b=a+1;c=a+nx+2;e=a+nx+1
                faces.extend([(a,b,c),(a,c,e)])
        mesh=bpy.data.meshes.new('Menu_L%d_'%level+key);mesh.from_pydata(verts,[],faces);mesh.update()
        layer=mesh.uv_layers.new(name='UV0_SurfaceMetres')
        for loop in mesh.loops:layer.data[loop.index].uv=uvs[loop.vertex_index]
        obj=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(obj);obj.parent=root;mesh.materials.append(bpy.data.materials[material])
        for face in mesh.polygons:face.use_smooth=True
        obj.hide_set(level!=0);obj.hide_render=level!=0;made.append(obj)
ground('Pullout',-34,26,-16,5.5,[.5,1,2],'Canyon_Asphalt')
ground('EdgeGravel',-34,26,5.5,10,[.35,.7,1.4],'Canyon_Gravel')
ground('NearValley',-90,130,10,160,[2,4,8],'Canyon_Gravel')
ground('FarValley',-240,460,160,920,[12,24,48],'Canyon_Gravel')

# Irregular small foreground fragments and a low right overlook edge. Existing
# authored rocks carry their UV/material/three-LOD data; none is a picture card.
random.seed(91027)
for index in range(26):
    u=random.uniform(-17,10);d=random.uniform(5.8,10);scale=random.uniform(.08,.27)
    scan('Boulder_%02d'%(index%55),'EdgeStone_%02d'%index,u,d,height(u,d),scale*1.8,scale*1.3,scale,random.uniform(-1.8,1.8))
for index in range(5):
    scan('Bend_%02d'%(index%3),'RightOverlookStone_%02d'%index,4.7+index*.55,5.7+index*.10,-.06,.60,.68,.54,random.uniform(-.18,.18))

for obj in list(source_root.children_recursive):bpy.data.objects.remove(obj,do_unlink=True)
bpy.data.objects.remove(source_root,do_unlink=True)
for obj in list(scene.objects):
    if obj.type=='EMPTY' and obj!=root and obj.parent is None:bpy.data.objects.remove(obj,do_unlink=True)
for name,point in [('Forward',(0,0,3)),('Ground_Origin',(0,0,0)),('LeftRoadMarker',(-1,0,0)),('RightRoadMarker',(1,0,0))]:
    obj=bpy.data.objects.new(name,None);scene.collection.objects.link(obj);obj.parent=root;obj.location=cv(point)
camera=scene.camera;camera.name='Menu_ConceptCamera';camera.location=cv((2.97608256,1.50701666,1.88716865))
direction=cv((-1.6,-.32,-1)).normalized();camera.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
camera.data.sensor_fit='HORIZONTAL';camera.data.sensor_width=36;camera.data.lens=36/(2*math.tan(math.radians(35)/2)*(16/9));camera.data.shift_x=-.2219;camera.data.shift_y=.0
camera.data.clip_start=.03;camera.data.clip_end=2200
for obj in scene.objects:
    if obj.type=='LIGHT' and obj.data.type=='SUN':
        lightdirection=p(.7,.28,.25).normalized();obj.rotation_euler=(-lightdirection).to_track_quat('-Z','Y').to_euler();obj.data.energy=2.0;obj.data.angle=math.radians(1.5);obj.data.color=(1,.76,.49)
# Existing licensed physical HDR world and aerial perspective remain actual
# lighting/volume inputs. Root calibrates the Unity sky to this menu camera.
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.exposure=.0
scene.render.filepath=ROOT+'docs/p08/golden/menu-environment/v1/composition-01.png'
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/MenuEnvironment/V1/RB_Golden_MenuEnvironment.blend')
print('MENU_ENVIRONMENT_BUILT '+json.dumps({'meshes':len(made),'modules':len(made)//3,'cameraPositionUnity':[2.97608256,1.50701666,1.88716865],'modelRotationEuler':[0,0,0],'visualAccepted':False}))
bpy.ops.render.render(write_still=True)
