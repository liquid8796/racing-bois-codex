"""Original workshop geometry from the inspected, hash-locked garage concept.

Run only through the direct task-owned Blender MCP port9877. This recipe uses
metres, explicit modular ownership, real closed geometry and tiled PBR inputs.
"""
import bpy,bmesh,math,json,random
from mathutils import Vector

ROOT='D:/Project/Unity/racing-bois/'
assert '/Canyon/V16/' in bpy.data.filepath.replace('\\','/') or '/Garage/' in bpy.data.filepath.replace('\\','/'), 'Preserve the previous task source before rebuilding'
for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
for mesh in list(bpy.data.meshes):
    if mesh.users==0:bpy.data.meshes.remove(mesh)
for mat in list(bpy.data.materials):
    if mat.users==0:bpy.data.materials.remove(mat)
for image in list(bpy.data.images):
    if image.users==0 and image.source=='FILE':bpy.data.images.remove(image)
scene=bpy.context.scene;scene.name='RB_Golden_Garage_Authoring'
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
root=bpy.data.objects.new('RB_Golden_Garage',None);scene.collection.objects.link(root)
materials={};modules={};LEVEL=0;PARTS=[]

def coord(p):return Vector((p[0],p[2],p[1]))

def material(name,normal_strength=1):
    m=bpy.data.materials.new(name);m.use_nodes=True
    nodes=m.node_tree.nodes;links=m.node_tree.links;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    prefix=ROOT+'Assets/RacingBois/Art/P08/Golden/Garage/V1/Textures/'+name
    for suffix,socket,linear in [('BaseColor','Base Color',False),('Roughness','Roughness',True)]:
        image=bpy.data.images.load(prefix+'_'+suffix+'.png',check_existing=True);image.reload();image.colorspace_settings.name='Non-Color' if linear else 'sRGB';image.pack()
        tex=nodes.new('ShaderNodeTexImage');tex.image=image;links.new(tex.outputs['Color'],bs.inputs[socket])
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(prefix+'_MetallicSmoothness.png',check_existing=True);tex.image.reload();tex.image.colorspace_settings.name='Non-Color';tex.image.pack()
    sep=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],sep.inputs['Color']);links.new(sep.outputs['Red'],bs.inputs['Metallic'])
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(prefix+'_Normal.png',check_existing=True);tex.image.reload();tex.image.colorspace_settings.name='Non-Color';tex.image.pack()
    normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=normal_strength;links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal'])
    if name=='Garage_Lamp':
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(prefix+'_Emission.png',check_existing=True);tex.image.reload();tex.image.pack();links.new(tex.outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=6
    materials[name]=m;return m

for name in ['Floor','Concrete','PowderSteel','ToolSteel','Rubber','Wood','Cardboard','Amber','Cable','Lamp']:
    material('Garage_'+name,.35 if name=='Floor' else .6 if name=='Concrete' else 1)

def finish(obj,mat,bevel=0,tile=1):
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel and LEVEL<2:
        mod=obj.modifiers.new('Manufactured edge radius','BEVEL');mod.width=bevel;mod.segments=3 if LEVEL==0 else 1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    mesh=obj.data;mesh.materials.append(materials['Garage_'+mat]);mesh.validate(clean_customdata=False);mesh.update()
    uv=mesh.uv_layers.active or mesh.uv_layers.new(name='UV_MetricTile')
    for poly in mesh.polygons:
        normal=poly.normal
        if abs(normal.x)>=max(abs(normal.y),abs(normal.z)):axes=(1,2)
        elif abs(normal.y)>=abs(normal.z):axes=(0,2)
        else:axes=(0,1)
        for i in poly.loop_indices:
            p=obj.matrix_world@mesh.vertices[mesh.loops[i].vertex_index].co
            uv.data[i].uv=(p[axes[0]]/tile,p[axes[1]]/tile)
    PARTS.append(obj);return obj

def box(p,size,mat='PowderSteel',bevel=.004,tile=1):
    bpy.ops.mesh.primitive_cube_add(size=1,location=coord(p));o=bpy.context.object;o.dimensions=coord(size)
    return finish(o,mat,bevel,tile)

def cylinder(a,b,r,mat='ToolSteel',vertices=16):
    av=coord(a);bv=coord(b);v=bv-av
    bpy.ops.mesh.primitive_cylinder_add(vertices=max(6,vertices//(LEVEL+1)),radius=r,depth=v.length,end_fill_type='NGON',location=(av+bv)*.5)
    o=bpy.context.object;o.rotation_euler=v.to_track_quat('Z','Y').to_euler()
    o=finish(o,mat,min(r*.12,.0015))
    for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
    return o

def tube_ring(p,r,thickness,mat='ToolSteel'):
    bpy.ops.mesh.primitive_torus_add(major_radius=r,minor_radius=thickness,major_segments=[32,16,8][LEVEL],minor_segments=[8,6,4][LEVEL],location=coord(p),rotation=(math.pi/2,0,0))
    return finish(bpy.context.object,mat)

def start():
    PARTS.clear()

def end(name):
    assert PARTS,name
    bpy.ops.object.select_all(action='DESELECT')
    for o in PARTS:o.select_set(True)
    bpy.context.view_layer.objects.active=PARTS[0]
    if len(PARTS)>1:bpy.ops.object.join()
    o=bpy.context.object
    o.name='Garage_L%d_%s'%(LEVEL,name);o.data.name=o.name+'_Mesh';o.parent=root
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    # Recenter module coordinates without changing world geometry.
    centre=sum((o.matrix_world@v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
    old=o.matrix_world.copy();new=old.copy();new.translation=centre
    inv=new.inverted()
    for v in o.data.vertices:v.co=inv@(old@v.co)
    o.matrix_world=new
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    o.data.validate(clean_customdata=False);o.data.update()
    modules.setdefault(name,[]).append(o.name)
    o.hide_render=LEVEL>0;o.hide_set(LEVEL>0);return o

def caster(x,y,z,r=.037):
    box((x,y+r+.038,z),(.027,.045,.055),bevel=.002)
    cylinder((x-.018,y+r,z),(x+.018,y+r,z),r,'Rubber',20)
    if LEVEL<2:cylinder((x-.021,y+r,z),(x+.021,y+r,z),r*.35,'ToolSteel',12)

def cabinet(name,x,z,width,height,drawers):
    start();depth=.46;bottom=.12
    box((x,(height+bottom)*.5,z),(width,height-bottom,depth),bevel=.009)
    box((x,height+.025,z),(width+.035,.05,depth+.035),'Wood',.005)
    for i in range(drawers):
        dy=(height-bottom-.035)/drawers;yy=height-.025-(i+.5)*dy
        box((x,yy,z-depth*.5-.011),(width-.035,dy-.008,.019),bevel=.002)
        if LEVEL<2:box((x,yy+dy*.26,z-depth*.5-.027),(width-.075,.012,.018),'ToolSteel',.002)
    for xx in [x-width*.40,x+width*.40]:
        for zz in [z-depth*.37,z+depth*.37]:caster(xx,0,zz)
    end(name)

def spanner(x,y,z,length):
    # Closed U-shaped forged jaw, open at the top. This is actual thickness,
    # not a painted tool silhouette or a cylinder pretending to be a wrench.
    outer=length*.10;inner=outer*.54;thick=.006
    pts=[];n=[20,12,8][LEVEL]
    for i in range(n+1):
        a=math.radians(42+276*i/n);pts.append((math.sin(a)*outer,math.cos(a)*outer))
    for i in range(n,-1,-1):
        a=math.radians(42+276*i/n);pts.append((math.sin(a)*inner,math.cos(a)*inner))
    count=len(pts);verts=[]
    for dz in [-thick/2,thick/2]:
        for px,py in pts:verts.append(coord((x+px,y+length*.5+py,z+dz)))
    faces=[tuple(range(count-1,-1,-1)),tuple(range(count,count*2))]
    for i in range(count):j=(i+1)%count;faces.append((i,j,j+count,i+count))
    mesh=bpy.data.meshes.new('ForgedOpenJaw');mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new('ForgedOpenJaw',mesh);scene.collection.objects.link(o);finish(o,'ToolSteel')
    box((x,y,z),(outer*.60,length,.006),'ToolSteel',.002)
    tube_ring((x,y-length*.5,z),outer*.65,outer*.23)

for LEVEL in range(3):
    # Slab seams are deliberate physical joins; metric UV tiling is intentional.
    for ix in range(3):
        for iz in range(3):
            start();box((-4+4*ix,-.09,-4+4*iz),(3.998,.18,3.998),'Floor',.0008,2);end('Floor_%d_%d'%(ix,iz))
    # Back panels use large poured modules with sparse formwork ties.
    for ix in range(8):
        for iy in range(2):
            start();x=-5.25+ix*1.5;y=.8+iy*1.6
            box((x,y,4.53),(1.497,1.597,.18),'Concrete',.0018,2.2)
            if LEVEL<2:
                for xx in [x-.57,x+.57]:
                    for yy in [y-.57,y+.57]:cylinder((xx,yy,4.435),(xx,yy,4.431),.009,'PowderSteel',10)
            end('BackPanel_%d_%d'%(ix,iy))
    # Forward left wall creates the dark architectural frame in the concept.
    for ix in range(3):
        start();box((-5.4+ix*1.1,1.65,3.5),(1.097,3.3,.3),'Concrete',.002,2.2);end('NearLeftPanel_%d'%ix)
    for i,x in enumerate([-2.28,.02,1.16,3.85,5.45]):
        start();z=3.70 if i==0 else 4.23
        box((x,1.65,z),(.10,3.3,.22),bevel=.005)
        box((x,1.65,z-.12),(.21,3.3,.025),bevel=.002)
        box((x,1.65,z+.12),(.21,3.3,.025),bevel=.002)
        box((x,.018,z),(.32,.035,.35),bevel=.002)
        if LEVEL<2:
            for dx in [-.12,.12]:
                for dz in [-.13,.13]:cylinder((x+dx,.035,z+dz),(x+dx,.043,z+dz),.014,'ToolSteel',8)
        end('SteelColumn_%d'%i)
    start();box((.82,1.65,4.24),(.44,3.3,.46),'Concrete',.003,2.2);end('ConcretePier')
    for i,z in enumerate([.2,2.1,4.1]):
        start();box((0,3.26,z),(12,.15,.07),bevel=.003)
        box((0,3.34,z),(12,.025,.22),bevel=.003);end('RoofCrossBeam_%d'%i)
    start();box((0,3.53,.6),(12,.18,7.8),'Concrete',.003,2.2);end('Ceiling')
    # Left workshop island: two tool cabinets, open shelving and a hardwood top.
    cabinet('LeftRollingChest',-1.83,3.94,.51,.91,7)
    cabinet('BenchLeftPedestal',-1.27,4.04,.30,.90,4)
    cabinet('BenchRightPedestal',-.16,4.04,.30,.90,4)
    start();box((-1.04,.957,4.02),(2.18,.046,.54),'Wood',.004)
    for yy in [.19,.50]:box((-.72,yy,4.07),(.75,.026,.40),'Wood',.002)
    for xx in [-1.10,-.34]:box((xx,.53,4.21),(.026,.84,.026),bevel=.002)
    end('Workbench')
    start();box((-1.45,1.41,4.34),(1.04,.62,.024),bevel=.006)
    # Fine peg heads catch the warm practical light without an alpha sheet.
    if LEVEL<2:
        for ix in range(15):
            for iy in range(8):
                if (ix+iy)%3==0:cylinder((-1.92+ix*.068,1.15+iy*.071,4.323),(-1.92+ix*.068,1.15+iy*.071,4.317),.004,'ToolSteel',8)
    for i in range(9):
        length=.37-i*.017;spanner(-1.90+i*.107,1.40,4.295,length)
        if LEVEL<2:cylinder((-1.90+i*.107,1.60,4.322),(-1.90+i*.107,1.60,4.285),.0035,'ToolSteel',8)
    end('ToolboardAndWrenches')
    # Machinist vice with fixed and sliding jaw, threaded spindle and handle.
    start();box((-.25,1.004,3.96),(.22,.034,.19),bevel=.005)
    box((-.25,1.061,3.97),(.13,.086,.18),bevel=.004)
    for xx in [-.33,-.16]:
        box((xx,1.118,3.98),(.045,.07,.19),bevel=.003)
        box((xx,1.141,3.977),(.012,.024,.19),'ToolSteel',.001)
    cylinder((-.43,1.066,3.97),(-.12,1.066,3.97),.013,'ToolSteel',16)
    cylinder((-.45,1.015,3.97),(-.45,1.12,3.97),.006,'ToolSteel',10);end('MachinistVice')
    start()
    for i,x in enumerate([-.92,-.77,-.62]):
        h=[.20,.23,.16][i];cylinder((x,.985,4.11),(x,.985+h,4.11),.041,'ToolSteel',24)
        cylinder((x,.985+h,4.11),(x,1.015+h,4.11),.014,'PowderSteel',12)
    for j,p in enumerate([(-.92,.25,4.04),(-.61,.26,4.05),(-.72,.55,4.04)]):
        box(p,(.23,.12,.21),'Cardboard',.002)
        if LEVEL<2:box((p[0],p[1]+.061,p[2]),(.026,.001,.21),'Amber',0)
    end('BenchContainers')
    # Right low multi-drawer rolling tool chest.
    cabinet('RightRollingChest',2.86,4.03,1.30,.87,9)
    start();box((3.13,1.009,4.04),(.40,.22,.29),bevel=.008)
    box((3.13,1.125,4.04),(.425,.02,.30),bevel=.003)
    box((3.13,1.169,4.04),(.14,.017,.021),'ToolSteel',.002)
    for xx in [3.045,3.215]:box((xx,1.144,4.04),(.018,.065,.021),'ToolSteel',.002)
    for xx in [2.51,2.62]:
        cylinder((xx,.92,4.07),(xx,1.04,4.07),.029,'PowderSteel',18)
        cylinder((xx,1.04,4.07),(xx,1.075,4.07),.012,'ToolSteel',12)
    end('RightChestTools')
    # Open rack at the extreme right of the reference, with visible bracing.
    start()
    for xx in [4.70,5.68]:
        for zz in [3.86,4.38]:box((xx,1.08,zz),(.035,2.16,.035),bevel=.003)
    for yy in [.13,.69,1.25,1.85]:
        box((5.19,yy,4.12),(1.04,.035,.58),'Wood',.003)
        for zz in [3.84,4.4]:box((5.19,yy-.03,zz),(1.06,.06,.024),bevel=.002)
    cylinder((4.71,.15,4.39),(5.67,1.83,4.39),.012,'PowderSteel',12)
    end('StorageRack')
    start()
    for j,p in enumerate([(4.99,.33,4.09),(5.42,.31,4.13),(5.15,.83,4.14),(5.45,.81,4.09),(4.96,1.40,4.15),(5.42,1.39,4.11)]):
        box(p,(.32,.28,.36),'Cardboard' if j<4 else 'PowderSteel',.003)
        if LEVEL<2:box((p[0],p[1],p[2]-.183),(.055,.025,.004),'ToolSteel',.001)
    box((3.61,.25,3.95),(.22,.50,.25),'Cardboard',.003);end('RackStorage')
    # Wall conduits, switches and compact wall mounted distribution enclosures.
    for i,x in enumerate([-2.15,1.33,3.70,4.49]):
        start();z=4.335 if i else 3.80
        cylinder((x,.09,z),(x,3.15,z),.008,'Cable',12)
        box((x,.99,z-.036),(.095,.14,.07),'Amber' if i==2 else 'PowderSteel',.004)
        if LEVEL<2:
            box((x,1.015,z-.075),(.024,.026,.012),'Amber',.001)
            for yy in [.28,.74,1.45,2.29,2.88]:box((x,yy,z-.01),(.03,.012,.012),'ToolSteel',.001)
        end('Conduit_%d'%i)
    # Separate closed fixture meshes. Emission and real area lights both used.
    for i,p in enumerate([(-1.75,2.16,4.17),(-.45,2.04,4.17),(1.51,1.89,4.22),(3.27,2.21,4.17),(5.16,2.04,3.84),(-1.10,3.21,2.45)]):
        width=[.73,.36,.25,.76,.54,.42][i]
        start();box(p,(width+.07,.053,.075),bevel=.006)
        box((p[0],p[1]-.012,p[2]-.042),(width,.024,.023),'Lamp',.006)
        if LEVEL<2:
            for dx in [-width*.35,width*.35]:box((p[0]+dx,p[1],p[2]+.07),(.025,.024,.14),bevel=.003)
        end('WarmStrip_%d'%i)

# Semantic markers make export handedness measurable in the native importer.
for name,p in [('Forward',(0,0,2)),('Ground_Origin',(0,0,0)),('LeftRoadMarker',(-1,0,0)),('RightRoadMarker',(1,0,0))]:
    o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);o.parent=root;o.location=coord(p)

def area(name,p,target,power,size,size_y,color):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='RECTANGLE';data.size=size;data.size_y=size_y;data.color=color
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=coord(p);o.rotation_euler=(coord(target)-o.location).to_track_quat('-Z','Y').to_euler();return o

for i,p in enumerate([(-1.75,2.14,4.09),(-.45,2.02,4.09),(1.51,1.87,4.14),(3.27,2.19,4.09),(5.16,2.02,3.76),(-1.10,3.17,2.41)]):
    width=[.73,.36,.25,.76,.54,.42][i]
    area('Practical_%d'%i,p,(p[0],.3,p[2]-.5),[100,55,35,110,60,70][i],width,.04,(1,.63,.30))
area('DoorSoftAmbient',(.2,2.9,-2.8),(.2,.7,3.7),110,5,3,(.76,.81,1))
world=bpy.data.worlds.new('Garage_NightAmbient');world.use_nodes=True;world.node_tree.nodes.get('Background').inputs[0].default_value=(.10,.12,.16,1);world.node_tree.nodes.get('Background').inputs[1].default_value=.1;scene.world=world
camera_data=bpy.data.cameras.new('Garage_ConceptCamera');camera=bpy.data.objects.new('Garage_ConceptCamera',camera_data);scene.collection.objects.link(camera)
camera.location=coord((0,.97,-7));camera.rotation_euler=(coord((0,.13,4.2))-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.lens=40;camera_data.sensor_width=36;scene.camera=camera
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.3
scene.render.image_settings.file_format='PNG';scene.render.filepath=ROOT+'docs/p08/golden/garage/v1/gameplay.png'
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Garage/V1/RB_Golden_Garage.blend')
print('GARAGE_BUILD '+json.dumps({'modules':modules,'concept':'ArtSource/Concepts/P08/Golden/garage-environment-v1.png','visualAccepted':False,'cameraUnity':{'position':[0,.97,-7],'target':[0,.13,4.2],'lensMm':40,'sensorMm':36},'renderCPUThreads':4}))
