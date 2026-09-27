"""Original Canyon golden segment. Execute only through direct Blender MCP port9877.

The locked concept was visually inspected before this recipe was written. Geometry
uses metres, +Z forward in design coordinates. The 80m road is a review specimen,
not a promoted production route. All rock, rail and vegetation forms are real mesh.
"""
import bpy, bmesh, math, random, json
from mathutils import Vector, noise

ROOT='D:/Project/Unity/racing-bois/'
LIBRARY=ROOT+'ArtSource/P08/Golden/Canyon/'
SRC=LIBRARY+'V13/'
TEX=ROOT+'Assets/RacingBois/Art/P08/Golden/Canyon/Textures/'
OUT=ROOT+'Assets/RacingBois/Art/P08/Golden/Canyon/V13/'
DOC=ROOT+'docs/p08/golden/canyon/v13/'
random.seed(71083)

if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.wm.save_as_mainfile(filepath=SRC+'previous-candidate.blend')
for old in list(scene_obj for scene_obj in bpy.context.scene.objects):bpy.data.objects.remove(old,do_unlink=True)
for old in list(bpy.data.meshes):
    if old.users==0:bpy.data.meshes.remove(old)
for material in list(bpy.data.materials):
    if material.users==0 and material.name.startswith('Canyon_'):bpy.data.materials.remove(material)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1536;scene.render.resolution_y=768;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.render.film_transparent=False
scene.view_settings.exposure=.25

def cv(p):return Vector((p[0],p[2],p[1]))
def empty(name,p=(0,0,0),parent=None):
    ob=bpy.data.objects.new(name,None);scene.collection.objects.link(ob);ob.location=cv(p);ob.parent=parent;return ob
root=empty('RB_Golden_Canyon')
empty('Forward',(0,0,5),root);empty('Ground_Origin',(0,0,0),root)
empty('LeftRoadMarker',(-3.7,0,0),root);empty('RightRoadMarker',(3.7,0,0),root)

materials={}
for name in ['Canyon_Sandstone','Canyon_Asphalt','Canyon_Gravel','Canyon_Galvanized','Canyon_Reflector','Canyon_YellowPaint','Canyon_WhitePaint','Canyon_Sage','Canyon_DryGrass','Canyon_Wood','Canyon_Cliff01','Canyon_Cliff02','Canyon_Cliff03']:
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    ns=mat.node_tree.nodes;links=mat.node_tree.links
    shader=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
    nodes={}
    for channel in ['BaseColor','Normal','Roughness','MetallicSmoothness']:
        im=bpy.data.images.load((OUT+'Textures/' if name in ['Canyon_YellowPaint','Canyon_WhitePaint'] and channel=='BaseColor' else TEX)+name+'_'+channel+'.png',check_existing=True)
        im.reload()
        if channel!='BaseColor':im.colorspace_settings.name='Non-Color'
        im.pack();n=ns.new('ShaderNodeTexImage');n.image=im;n.extension='REPEAT';nodes[channel]=n
    links.new(nodes['BaseColor'].outputs['Color'],shader.inputs['Base Color'])
    links.new(nodes['Roughness'].outputs['Color'],shader.inputs['Roughness'])
    sep=ns.new('ShaderNodeSeparateColor');links.new(nodes['MetallicSmoothness'].outputs['Color'],sep.inputs['Color']);links.new(sep.outputs['Red'],shader.inputs['Metallic'])
    norm=ns.new('ShaderNodeNormalMap');norm.inputs['Strength'].default_value=.72 if name=='Canyon_Sandstone' else .5
    links.new(nodes['Normal'].outputs['Color'],norm.inputs['Color']);links.new(norm.outputs['Normal'],shader.inputs['Normal'])
    materials[name]=mat

def Mesh(name,material):return {'name':name,'material':material,'v':[],'f':[],'uv':[]}
def polygon(m,points,uv=None):
    base=len(m['v']);m['v'].extend([tuple(cv(p)) for p in points]);m['f'].append(tuple(range(base,base+len(points))))
    m['uv'].append(uv if uv else [(p[0]/2,p[2]/2) for p in points])
def quad(m,a,b,c,d,uv=None):polygon(m,[a,b,c,d],uv)
parts=[]
def finish(m):
    if not m['v']:return
    mesh=bpy.data.meshes.new(m['name']);mesh.from_pydata(m['v'],[],m['f']);mesh.update()
    layer=mesh.uv_layers.new(name='UV0_SurfaceMetres')
    for poly,uv in zip(mesh.polygons,m['uv']):
        for loop,p in zip(poly.loop_indices,uv):layer.data[loop].uv=p
    obj=bpy.data.objects.new(m['name'],mesh);scene.collection.objects.link(obj);obj.parent=root;obj.data.materials.append(materials[m['material']])
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if m['material'] in ['Canyon_Sage','Canyon_Asphalt','Canyon_Gravel','Canyon_YellowPaint','Canyon_WhitePaint']:
        for face in bm.faces:
            if face.normal.z<0:face.normal_flip()
    bm.to_mesh(mesh);bm.free()
    if m['material']=='Canyon_Sandstone':
        for poly in mesh.polygons:poly.use_smooth=True
    parts.append(obj)

def box(m,center,size,yaw=0):
    x,h,z=center;w,t,d=[v/2 for v in size];c,s=math.cos(yaw),math.sin(yaw)
    points=[]
    for a,b,q in [(-w,-t,-d),(w,-t,-d),(w,t,-d),(-w,t,-d),(-w,-t,d),(w,-t,d),(w,t,d),(-w,t,d)]:points.append((x+a*c+q*s,h+b,z-a*s+q*c))
    for f in [(0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(0,1,5,4),(3,7,6,2)]:polygon(m,[points[i] for i in f],[(0,0),(1,0),(1,1),(0,1)])

def stem(m,a,b,radius,sides=5):
    a=Vector(a);b=Vector(b);axis=(b-a).normalized();normal=axis.cross(Vector((1,0,0)))
    if normal.length<.1:normal=axis.cross(Vector((0,0,1)))
    normal.normalize();other=axis.cross(normal).normalized();rings=[]
    for endpoint,r in [(a,radius),(b,radius*.6)]:rings.append([endpoint+(normal*math.cos(i*2*math.pi/sides)+other*math.sin(i*2*math.pi/sides))*r for i in range(sides)])
    for i in range(sides):j=(i+1)%sides;quad(m,rings[0][i],rings[0][j],rings[1][j],rings[1][i],[(i/sides,0),(j/sides,0),(j/sides,1),(i/sides,1)])
    polygon(m,list(reversed(rings[0])));polygon(m,rings[1])

def rock(m,center,size,seed,segments=3):
    # Six shared cube-surface grids with chamfered edges and continuous erosion.
    rng=random.Random(seed);rotation=rng.uniform(-.16,.16);phase=Vector((seed*.143,seed*.247,seed*.075))
    def point(u,v,face):
        p=Vector((u,v,1)) if face==0 else Vector((u,v,-1)) if face==1 else Vector((u,1,v)) if face==2 else Vector((u,-1,v)) if face==3 else Vector((1,u,v)) if face==4 else Vector((-1,u,v))
        inner=Vector([max(-.5,min(.5,w)) for w in p]);delta=p-inner
        p=inner+delta.normalized()*.42
        erosion=noise.noise_vector(p*1.8+phase)*.24
        p+=erosion
        # Greater irregularity at bedding planes prevents a manufactured cube wall.
        p.x+=.12*math.sin(p.z*5+seed);p.y+=.13*math.sin(p.x*4+seed*.5)
        x=p.x*size[0]/2;h=p.z*size[1]/2;z=p.y*size[2]/2
        return (center[0]+x*math.cos(rotation)+z*math.sin(rotation),center[1]+h,center[2]-x*math.sin(rotation)+z*math.cos(rotation))
    for face in range(6):
        for a in range(segments):
            for b in range(segments):
                u=-1+a*2/segments;v=-1+b*2/segments;step=2/segments
                ps=[point(u,v,face),point(u+step,v,face),point(u+step,v+step,face),point(u,v+step,face)]
                # Intentional tiled, world-scale mineral texture; no baked lighting.
                uv=[(p[2]/2.4,p[1]/2.4) if face>=4 else (p[0]/2.4,p[1]/2.4) if face>=2 else (p[0]/2.4,p[2]/2.4) for p in ps]
                polygon(m,ps,uv)

def center(s):return -18*(1-math.cos(max(0,min(80,s))*math.pi/160))
def tangent(s):return -18*math.pi/160*math.sin(max(0,min(80,s))*math.pi/160)
def road(s,lateral,height=0):
    angle=math.atan(tangent(s));return (center(s)+lateral*math.cos(angle),height,s-lateral*math.sin(angle))
def shoulder_height(s,w):
    excess=abs(w)-4
    if w<0:return max(0,excess)*.62 + noise.noise(Vector((w*.4,s*.16,8)))*min(.45,max(0,excess)*.1)
    return -max(0,excess)*.62+noise.noise(Vector((w*.27,s*.13,2)))*min(1.5,max(0,excess)*.22)

# Eight removable 10m road modules, matching centre-line curvature and shoulders.
for tile in range(8):
    m=Mesh('Canyon_L0_Road_%02d'%tile,'Canyon_Asphalt')
    for j in range(20):
        s=tile*10+j*.5;t=s+.5
        for k in range(8):
            a=-3.7+k*.925;b=a+.925
            quad(m,road(s,a),road(t,a),road(t,b),road(s,b),[(a/3,s/3),(a/3,t/3),(b/3,t/3),(b/3,s/3)])
    finish(m)

for side in [-1,1]:
    ground=Mesh('Canyon_L0_Shoulder_'+str(side),'Canyon_Gravel')
    for j in range(96):
        s=-8+j;t=s+1
        for k in range(24 if side>0 else 10):
            a=side*(3.64+k*.65);b=side*(3.64+(k+1)*.65)
            ps=[road(s,a,shoulder_height(s,a)-.018),road(t,a,shoulder_height(t,a)-.018),road(t,b,shoulder_height(t,b)-.018),road(s,b,shoulder_height(s,b)-.018)]
            polygon(ground,ps,[(p[0]/2,p[2]/2) for p in ps])
    finish(ground)

# Wear is actual missing paint segments, restrained so lane legibility survives.
for kind,offsets,width in [('Canyon_YellowPaint',[-.11,.11],.078),('Canyon_WhitePaint',[-3.5,3.5],.13)]:
    paint=Mesh('Canyon_L0_'+kind,kind)
    for offset in offsets:
        for j in range(3200):
            s=j*.025;t=s+.0253
            wear=noise.noise(Vector((s*13,offset*35,4)))
            if wear>.36 and random.random()<.35:continue
            trim=max(0,wear)*.013
            quad(paint,road(s,offset-width/2+trim,.008),road(t,offset-width/2,.008),road(t,offset+width/2-trim,.008),road(s,offset+width/2,.008))
    finish(paint)

# Real corrugated W-beam, separate folded end and I-section posts, bolts, reflectors.
beam=Mesh('Canyon_L0_Guardrail_Beam','Canyon_Galvanized');rail=Mesh('Canyon_L0_Guardrail_Posts','Canyon_Galvanized');reflectors=Mesh('Canyon_L0_Reflectors','Canyon_Reflector')
profile=[(-.15,.028),(-.11,-.022),(-.07,.027),(0,.046),(.07,.027),(.11,-.022),(.15,.028)]
for j in range(160):
    s=j*.5;t=s+.5
    for k in range(len(profile)-1):
        h,a=profile[k];hh,b=profile[k+1]
        quad(beam,road(s,4.02+a,.85+h),road(t,4.02+a,.85+h),road(t,4.02+b,.85+hh),road(s,4.02+b,.85+hh),[(s/2,k/6),(t/2,k/6),(t/2,(k+1)/6),(s/2,(k+1)/6)])
for s in range(0,81,2):
    x,h,z=road(s,4.11,.48);yaw=math.atan(tangent(s))
    box(rail,(x,h,z),(.085,.99,.025),yaw)
    for delta in [-.055,.055]:
        xx,hh,zz=road(s,4.11+delta,.48);box(rail,(xx,hh,zz),(.023,.99,.11),yaw)
    xx,hh,zz=road(s,4.11,-.005);box(rail,(xx,hh,zz),(.24,.055,.26),yaw)
    if s%4==0:
        p=road(s,3.961,.82);box(reflectors,p,(.015,.095,.14),yaw)
    for height in [.76,.94]:
        p=road(s,3.958,height);box(rail,p,(.012,.018,.023),yaw)
finish(beam);finish(rail);finish(reflectors)

# Continuous eroded bedrock faces with deep physical joints. The face is a
# surface, not stacked cubes: irregular bedding crosses and ends at fractures.
def fracture_wall(name,bx,bz,width,height,depth,seed,along_road=False):
    m=Mesh(name,'Canyon_Sandstone');rng=random.Random(seed)
    joints=[0.0];running=0
    while running<width:
        running+=rng.uniform(1.3,4.3);joints.append(running)
    spacing=.16 if along_road else 1.1
    steps=int(width/spacing);rows=int(height/spacing)
    def surface(u,v):
        t=u*width
        g=bz+t if along_road else t
        column=int((g+.5*math.sin(g*.32))/2.8)
        phase=(g+.5*math.sin(g*.32))%2.8
        joint=min(phase,2.8-phase)
        top=20+3*math.sin(g*.063)+noise.noise(Vector((g*.08,2,0)))*1.4 if along_road else height+min(.4,noise.noise(Vector((g*.09,seed*.1,0))))*5
        h=v*top
        bed_h=2.15+.34*math.sin(column*2.4+seed)
        bedding=(h+.32*math.sin(g*.41+column))%bed_h
        distance=min(bedding,bed_h-bedding)
        row=int((h+.32*math.sin(g*.41+column))/bed_h)
        block_offset=noise.noise(Vector((column*.57,row*.91,4)))*.45
        broad=noise.noise(Vector((g*.18,h*.06,4)))*.55+block_offset
        erosion=noise.noise(Vector((g*1.4,h*1.2,8)))*.16
        detail=noise.noise(Vector((g*5,h*3.5,5)))*.05
        seam=-.8*math.exp(-(joint/.21)**2)-.42*math.exp(-(distance/.18)**2)
        ledge=.09*math.sin(h*2.6+g*.04)+.035*math.sin(h*5.1+g*.36)
        x=bx+broad+erosion+detail+seam+ledge
        if along_road:x+=center(bz+t)
        return (x,h,bz+t)
    for a in range(steps):
        for b in range(rows):
            ps=[surface(a/steps,b/rows),surface((a+1)/steps,b/rows),surface((a+1)/steps,(b+1)/rows),surface(a/steps,(b+1)/rows)]
            polygon(m,ps,[(p[2]/2.1,p[1]/2.1) for p in ps])
    # Back, top and ends close the cliff volume. These are modular solid landforms.
    for a in range(steps):
        p=surface(a/steps,1);q=surface((a+1)/steps,1)
        polygon(m,[p,q,(q[0]-depth,q[1],q[2]),(p[0]-depth,p[1],p[2])])
    for t in [0,1]:
        p=surface(t,0);q=surface(t,1);polygon(m,[p,q,(q[0]-depth,q[1],q[2]),(p[0]-depth,p[1],p[2])])
    finish(m)
# Scanned CC0 forms are locally assembled and reshaped into the concept geology.
# Preserve their UVs, then explicitly reduce to desktop candidate LOD0.
scan_templates=[]
for scan_index,slug in enumerate(['namaqualand_cliff_01','namaqualand_cliff_02','namaqualand_boulder_02'],1):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=LIBRARY+'SourceModels/'+slug+'/'+slug+'_fbx.fbx',use_anim=False)
    imported=list(set(bpy.data.objects)-before)
    model=next(obj for obj in imported if obj.type=='MESH')
    model.data.materials.clear();model.data.materials.append(materials['Canyon_Cliff%02d'%scan_index])
    bpy.ops.object.select_all(action='DESELECT');model.select_set(True);bpy.context.view_layer.objects.active=model
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    reduction=model.modifiers.new('Preserve scan silhouette desktop budget','DECIMATE');reduction.ratio=.015 if scan_index==3 else .24 if scan_index==1 else .15;reduction.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=reduction.name)
    model.hide_render=True;model.hide_set(True);scan_templates.append(model)
for section in range(7):
    template=scan_templates[1 if section%3!=2 else 0]
    obj=template.copy();obj.data=template.data.copy();scene.collection.objects.link(obj);obj.name='Canyon_L0_Cliff_%02d'%section;obj.parent=root
    obj.hide_set(False);obj.hide_render=False
    obj.location=(center(section*15)-13.4,section*15+2,1.5)
    obj.rotation_euler=(0,0,math.pi/2+math.radians((section%3-1)*4))
    obj.scale=(1.02 if section%3!=2 else 1.9,1.45,2.15 if section%3!=2 else 3.0)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    parts.append(obj)

# Talus blocks and roadside fragments follow the ground, never float above it.
debris=Mesh('Canyon_L0_Talus','Canyon_Sandstone')
for i in range(290):
    s=random.uniform(-5,86);side=-1 if random.random()<.68 else 1;w=side*random.uniform(4.0,8.3 if side<0 else 6.1)
    scale=random.uniform(.12,.48) if i>75 else random.uniform(.5,1.65)
    x,h,z=road(s,w,shoulder_height(s,w))
    if i<75:
        template=scan_templates[2];obj=template.copy();obj.data=template.data.copy();scene.collection.objects.link(obj);obj.name='Canyon_L0_Boulder_%02d'%i;obj.parent=root;obj.hide_set(False);obj.hide_render=False
        factor=scale*.52;obj.location=(x,z,h+.02);obj.rotation_euler=(random.uniform(-.2,.2),random.uniform(-.15,.15),random.uniform(-math.pi,math.pi));obj.scale=(factor,factor*random.uniform(.7,1.2),factor*random.uniform(.8,1.3))
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);parts.append(obj)
    else:rock(debris,(x,h+scale*.3,z),(scale*1.4,scale,scale*1.1),6000+i,1)
finish(debris)

# Continuous basin closes all below-horizon sightlines; dense mesh near road,
# progressively larger cells beyond gameplay distances.
land=Mesh('Canyon_L0_DistantGround','Canyon_Gravel')
xs=list(range(-200,-60,20))+list(range(-60,120,4))+list(range(120,401,16))+[500,650]
zs=list(range(22,160,4))+list(range(160,501,12))+[550,620,700,800,950,1100]
def basin_height(x,z):
    floor=-31+noise.noise(Vector((x*.018,z*.021,6)))*5
    far_rise=max(0,z-500)*.1
    return floor+far_rise
for iz in range(len(zs)-1):
    for ix in range(len(xs)-1):
        ps=[]
        for dx,dz in [(0,0),(1,0),(1,1),(0,1)]:
            x=xs[ix+dx];z=zs[iz+dz];ps.append((x,basin_height(x,z),z))
        polygon(land,ps,[(p[0]/3,p[2]/3) for p in ps])
finish(land)
# Several receding geological layers replace the single repeated curtain wall.
# Coordinates are deliberately composed around the concept's bend and open valley.
formations=[]
for i in range(9):
    formations.append(('Bend',-62+i*14,108+(i%3)*12,-20,1.65,2.7,5.1,0))
for i in range(11):
    formations.append(('LowerLedge',25+i*11,83+(i%4)*19,-30,1.15,1.8,2.5,0))
for i in range(13):
    formations.append(('Opposite',65+i*17,225+(i%4)*23,-30,2.3,3.6,7.1,0))
for i in range(12):
    formations.append(('Far',-110+i*42,510+(i%4)*54,-18,5.0,5.8,12.5,0))
for section,(layer,x,z,y,sx,sy,sz,yaw) in enumerate(formations):
    template=scan_templates[section%2]
    obj=template.copy();obj.data=template.data.copy();scene.collection.objects.link(obj);obj.name='Canyon_L0_'+layer+'_%02d'%section;obj.parent=root;obj.hide_set(False);obj.hide_render=False
    obj.location=(x,z,y);obj.rotation_euler=(0,0,math.radians(((section*7)%5-2)*5+yaw));obj.scale=(sx,sy,sz)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    # Irregular eroded plateau tops; avoid cloning the same pointed scan silhouette.
    cap=(3.0 if section%2==0 else 5.0)*sz*(.9+.14*math.sin(section*1.91))
    for vertex in obj.data.vertices:
        if vertex.co.z>cap:vertex.co.z=cap+(vertex.co.z-cap)*.22
        vertex.co.x+=math.sin(vertex.co.z*.11+section)*.15*sz
    modifier=obj.modifiers.new('Distance-appropriate geological silhouette','DECIMATE');modifier.ratio=.06 if layer=='Far' else .12 if layer=='Opposite' else .22;modifier.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=modifier.name)
    parts.append(obj)
for template in scan_templates:bpy.data.objects.remove(template,do_unlink=True)

# Geometry sage: woody branches and lanceolate leaves, not repeated green spheres.
leaves=Mesh('Canyon_L0_Sage','Canyon_Sage');wood=Mesh('Canyon_L0_Branches','Canyon_Wood');grass=Mesh('Canyon_L0_Grass','Canyon_DryGrass')
for plant in range(300):
    s=random.uniform(-4,86);side=-1 if random.random()<.54 else 1;w=side*random.uniform(4.4,7.0 if side<0 else 8)
    x,y,z=road(s,w,shoulder_height(s,w));scale=random.uniform(.8,1.65)
    near=s<24
    for b in range(20 if near else 14):
        phi=random.uniform(0,2*math.pi);rad=random.uniform(.13,.5)*scale;h=random.uniform(.35,.75)*scale
        a=Vector((x,y,z));tip=Vector((x+math.cos(phi)*rad,y+h,z+math.sin(phi)*rad))
        stem(wood,a,tip,.0018*scale,3)
        for sprig in range(3 if near else 2):
            t=.28+sprig*.22+random.uniform(-.07,.07)
            origin=a.lerp(tip,t);theta=phi+random.uniform(-1.6,1.6)
            growth=Vector((math.cos(theta)*random.uniform(.09,.22),random.uniform(.12,.23),math.sin(theta)*random.uniform(.09,.22)))*scale
            endpoint=origin+growth
            stem(wood,origin,endpoint,.00085*scale,3)
            leaf_count=11 if near else 9
            for j in range(leaf_count):
                p=origin.lerp(endpoint,.12+j*.8/leaf_count+random.uniform(-.025,.025))
                angle=theta+(j%2)*math.pi+random.uniform(-.5,.5)
                direction=Vector((math.cos(angle),random.uniform(.2,.8),math.sin(angle))).normalized()
                cross=Vector((-math.sin(angle),0,math.cos(angle)))
                length=random.uniform(.045,.082)*scale;width=random.uniform(.010,.015)*scale
                pts=[p,p+direction*length*.25+cross*width*.7,p+direction*length*.65+cross*width,p+direction*length,p+direction*length*.65-cross*width,p+direction*length*.25-cross*width*.7]
                polygon(leaves,pts,[(.5,0),(1,.25),(1,.65),(.5,1),(0,.65),(0,.25)])

for clump in range(270):
    s=random.uniform(-5,86);side=random.choice([-1,1]);w=side*random.uniform(3.85,6.8)
    x,y,z=road(s,w,shoulder_height(s,w));scale=random.uniform(.7,1.3)
    for blade in range(48):
        a=random.uniform(0,math.pi*2);r=random.uniform(.01,.11)*scale
        h=random.uniform(.13,.52)*scale;lean=random.uniform(.07,.28)*scale;wid=random.uniform(.0025,.006)*scale
        p=Vector((x+math.cos(a)*r,y,z+math.sin(a)*r));sidev=Vector((-math.sin(a)*wid,0,math.cos(a)*wid));mid=p+Vector((math.cos(a)*lean*.35,h*.6,math.sin(a)*lean*.35));tip=p+Vector((math.cos(a)*lean,h,math.sin(a)*lean))
        quad(grass,p-sidev,p+sidev,mid+sidev*.6,mid-sidev*.6,[(0,0),(1,0),(1,.6),(0,.6)])
        polygon(grass,[mid-sidev*.6,mid+sidev*.6,tip],[(0,.6),(1,.6),(.5,1)])
finish(leaves);finish(wood);finish(grass)

# Partition continuous near-road geometry into independently culled10m modules.
# UV loops and authored winding are preserved; no whole400m LOD dependency.
for source in list(parts):
    if not any(token in source.name for token in ['Sage','Branches','Grass','Guardrail','Reflectors','Shoulder','Paint']):continue
    buckets={}
    for poly in source.data.polygons:
        center_y=sum(source.data.vertices[i].co.y for i in poly.vertices)/len(poly.vertices)
        tile=max(0,min(7,int(math.floor(center_y/10))))
        buckets.setdefault(tile,[]).append(poly)
    for tile,polys in buckets.items():
        vertices=[];faces=[];uvs=[];smooth=[];index_map={}
        for poly in polys:
            face=[]
            for index in poly.vertices:
                if index not in index_map:index_map[index]=len(vertices);vertices.append(tuple(source.data.vertices[index].co))
                face.append(index_map[index])
            faces.append(face);uvs.append([tuple(source.data.uv_layers.active.data[i].uv) for i in poly.loop_indices]);smooth.append(poly.use_smooth)
        mesh=bpy.data.meshes.new(source.name+'_Tile%02d'%tile);mesh.from_pydata(vertices,[],faces);mesh.update();layer=mesh.uv_layers.new(name='UV0_SurfaceMetres')
        for face,coordinates,use_smooth in zip(mesh.polygons,uvs,smooth):
            face.use_smooth=use_smooth
            for loop,coordinate in zip(face.loop_indices,coordinates):layer.data[loop].uv=coordinate
        obj=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(obj);obj.parent=root
        for material in source.data.materials:obj.data.materials.append(material)
        if 'Guardrail_Beam' in obj.name:
            bpy.context.view_layer.objects.active=obj;bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
            shell=obj.modifiers.new('Physical3mmgalvanizedsheet','SOLIDIFY');shell.thickness=.003;shell.offset=0;shell.use_rim=True
            bpy.ops.object.modifier_apply(modifier=shell.name)
        parts.append(obj)
    parts.remove(source);bpy.data.objects.remove(source,do_unlink=True)

# Independent LOD mesh ownership. Source modules stay separated for culling/reuse.
audit={'schema':1,'reviewOnly':True,'visualAccepted':False,'metres':True,'roadLengthMetres':80,'concept':'ArtSource/Concepts/P08/Golden/canyon-v2.png','objects':[],'lods':[[],[],[]]}
for obj in list(parts):
    # All mesh normals and UVs are authored before Unity import.
    tri=obj.modifiers.new('Stable export triangles','TRIANGULATE');bpy.context.view_layer.objects.active=obj
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.ops.object.modifier_apply(modifier=tri.name)
    audit['lods'][0].append(obj.name)
    audit['objects'].append({'name':obj.name,'vertices':len(obj.data.vertices),'triangles':len(obj.data.polygons),'materials':[m.name for m in obj.data.materials]})
    for level,ratio in [(1,.5),(2,.2)]:
        lower=obj.copy();lower.data=obj.data.copy();scene.collection.objects.link(lower);lower.name=obj.name.replace('_L0_','_L%d_'%level);lower.parent=root
        bpy.context.view_layer.objects.active=lower;bpy.ops.object.select_all(action='DESELECT');lower.select_set(True)
        d=lower.modifiers.new('LOD silhouette reduction','DECIMATE');d.ratio=ratio;d.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=d.name)
        lower.hide_render=True;lower.hide_set(True);audit['lods'][level].append(lower.name)
        audit['objects'].append({'name':lower.name,'vertices':len(lower.data.vertices),'triangles':len(lower.data.polygons),'materials':[m.name for m in lower.data.materials]})

# Actual CC0 HDR sky supplies clouds and sky illumination. The scan's measured
# sun azimuth/elevation is rotated to the reference rear-right horizon.
world=bpy.data.worlds.new('Canyon_Atmosphere');scene.world=world;world.use_nodes=True
nodes=world.node_tree.nodes;links=world.node_tree.links
bg=next(n for n in nodes if n.type=='BACKGROUND')
env=nodes.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(OUT+'Sky/qwantani_sunset_puresky_4k.hdr',check_existing=True);env.image.reload();env.image.pack()
coordinates=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeMapping');mapping.inputs['Rotation'].default_value[2]=.632000084608884-1.267
links.new(coordinates.outputs['Generated'],mapping.inputs['Vector']);links.new(mapping.outputs['Vector'],env.inputs['Vector']);links.new(env.outputs['Color'],bg.inputs['Color']);bg.inputs['Strength'].default_value=.85
lamp=bpy.data.lights.new('Canyon_WarmSun','SUN');lamp.energy=1.8;lamp.angle=math.radians(2.4);lamp.color=(1,.83,.62)
sun=bpy.data.objects.new('Canyon_WarmSun',lamp);scene.collection.objects.link(sun)
sun_direction=Vector((math.cos(1.267)*math.cos(.10431),math.sin(1.267)*math.cos(.10431),math.sin(.10431)))
sun.rotation_euler=(-sun_direction).to_track_quat('-Z','Y').to_euler()
camera_data=bpy.data.cameras.new('Canyon_Gameplay');camera=bpy.data.objects.new('Canyon_Gameplay',camera_data);scene.collection.objects.link(camera);scene.camera=camera
camera.location=cv((1.7,1.55,3));target=cv((-2,-2.6,32));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.lens=28;camera_data.clip_end=1000

# Atmospheric depth in authoring scene; root must configure matching Unity fog.
bpy.ops.mesh.primitive_cube_add(size=1,location=(100,650,75));fog=bpy.context.object;fog.name='Canyon_AerialPerspective';fog.scale=(1400,1200,300)
fogmat=bpy.data.materials.new('Canyon_AtmosphericVolume');fogmat.use_nodes=True;fogmat.node_tree.nodes.clear()
volume=fogmat.node_tree.nodes.new('ShaderNodeVolumeScatter');volume.inputs['Color'].default_value=(.60,.58,.53,1);volume.inputs['Density'].default_value=.0008;volume.inputs['Anisotropy'].default_value=.2
output=fogmat.node_tree.nodes.new('ShaderNodeOutputMaterial');fogmat.node_tree.links.new(volume.outputs['Volume'],output.inputs['Volume']);fog.data.materials.append(fogmat)

# Export only the candidate hierarchy; lights/camera are authoring scene evidence.
bpy.ops.object.select_all(action='DESELECT')
for obj in root.children_recursive:obj.hide_set(False);obj.select_set(True)
root.select_set(True);bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=OUT+'RB_Golden_Canyon.fbx',use_selection=True,object_types={'EMPTY','MESH'},axis_forward='-Z',axis_up='Y',use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,path_mode='STRIP',use_custom_props=True)
for obj in root.children_recursive:
    if '_L1_' in obj.name or '_L2_' in obj.name:obj.hide_set(True)
scene.render.filepath=DOC+'gameplay-v13.png'
bpy.ops.wm.save_as_mainfile(filepath=SRC+'RB_Golden_Canyon.blend')
print('CANYON_MODEL_REPORT '+json.dumps(audit))
