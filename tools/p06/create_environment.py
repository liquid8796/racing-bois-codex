"""Original canyon kit; run only through the live Blender MCP after hero handoff.

Concept: ArtSource/Concepts/P06/canyon-v1.png, inspected before authoring.
No source-game images/meshes are loaded. Texture signals are analytic/seeded.
Material UV reuse between disconnected repeated components is intentional.
"""
import bpy, bmesh, math, json, random
from array import array
from mathutils import Vector

ROOT='D:/Project/Unity/racing-bois/'
OUT=ROOT+'Assets/RacingBois/Art/P06/Environment/'
DOC=ROOT+'docs/p06/environment/'
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'_local/p06-before-environment.blend')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for material in list(bpy.data.materials):
    if material.users==0:bpy.data.materials.remove(material)
for image in list(bpy.data.images):
    if image.users==0:bpy.data.images.remove(image)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1

def bv(p):return Vector((-p[0],-p[2],p[1]))

def signal(u,v,seed=0):
    return (.47*math.sin(math.tau*(u*13+v*7)+seed)+.28*math.sin(math.tau*(u*29-v*17)+seed*.3)+.15*math.cos(math.tau*(u*71+v*61))+.10*math.sin(math.tau*(u*151-v*139)))

def sample(kind,u,v):
    n=signal(u,v,3);grain=signal(u*3,v*3,7);metal=0;rough=.87;height=n*.025
    if kind=='rock':
        strata=math.sin(math.tau*(v*21+.05*math.sin(u*math.tau*4)))
        seams=math.exp(-abs(math.sin(math.tau*(v*13+.017*math.sin(u*math.tau*7))))*38)
        shade=.09*n+.025*grain+.045*strata-.07*seams
        color=(.47+shade,.245+shade*.72,.105+shade*.42);height=.08*n+.05*strata-.22*seams;rough=.84+.05*n
    elif kind=='foliage':
        dry=u>.5;shade=.045*n+.025*grain
        color=((.49 if dry else .18)+shade,(.36 if dry else .225)+shade,(.16 if dry else .11)+shade*.5);height=n*.06
    elif kind=='roadside':
        tile=int(u*4)+4*int(v*4);fu=(u*4)%1;fv=(v*4)%1
        colors=[(.17,.11,.065),(.38,.42,.45),(.88,.46,.07),(.015,.019,.018),(.53,.62,.61),(.11,.14,.145),(.65,.62,.52),(.12,.18,.21)]
        shade=.025*n;c=colors[tile%8]
        if tile%8==0:
            wood=math.sin(fu*math.tau*37+.5*math.sin(fv*math.tau*2));wood2=math.exp(-abs(wood)*10);shade=.035*n-.05*wood2;height=.05*n-.09*wood2
        color=tuple(x+shade for x in c);metal=.8 if tile%8 in [1,5] else 0;rough=.37 if tile%8 in [1,4] else .72
        if tile==2 and abs(fu-(.63-.48*(1-abs(fv-.5)*2)))<.135 and .1<fv<.9:color=(.012,.014,.013)
    elif kind=='asphalt':
        speck=max(0,grain-.6);crack=math.exp(-abs(math.sin(math.tau*(u*3+v*2+.12*math.sin(v*math.tau*5))))*100)
        shade=.013*n+.018*grain+.025*speck-.014*crack;color=(.095+shade,.108+shade,.113+shade);height=.12*grain-.10*crack;rough=.83+.05*n
    else:
        shade=.032*n+.018*grain;color=(.35+shade,.255+shade*.85,.135+shade*.55);height=.09*n+.07*grain;rough=.94
    return tuple(min(.98,max(.001,c)) for c in color),height,metal,min(.98,max(.05,rough))

def texture_set(name,kind,size):
    base=array('f');mask=array('f');roughmap=array('f');heights=array('f')
    for y in range(size):
        for x in range(size):
            color,h,m,r=sample(kind,(x+.5)/size,(y+.5)/size)
            base.extend((*color,1));mask.extend((m,1,0,1-r));roughmap.extend((r,r,r,1));heights.append(h)
    normal=array('f')
    for y in range(size):
        for x in range(size):
            dx=(heights[y*size+(x+1)%size]-heights[y*size+(x-1)%size])*.5
            dy=(heights[((y+1)%size)*size+x]-heights[((y-1)%size)*size+x])*.5
            nx=-dx*size*.028;ny=-dy*size*.028;length=math.sqrt(nx*nx+ny*ny+1)
            normal.extend((.5+.5*nx/length,.5+.5*ny/length,.5+.5/length,1))
    images={}
    for suffix,pixels in [('BaseColor',base),('Normal',normal),('MetallicSmoothness',mask),('Roughness',roughmap)]:
        im=bpy.data.images.new(name+'_'+suffix,size,size,alpha=True)
        if suffix!='BaseColor':im.colorspace_settings.name='Non-Color'
        im.pixels.foreach_set(pixels);im.filepath_raw=OUT+im.name+'.png';im.file_format='PNG';im.save();im.pack();images[suffix]=im
    mat=bpy.data.materials.new(name);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;p=n.get('Principled BSDF')
    for suffix,dest in [('BaseColor','Base Color'),('Roughness','Roughness')]:
        t=n.new('ShaderNodeTexImage');t.image=images[suffix];l.new(t.outputs['Color'],p.inputs[dest])
    t=n.new('ShaderNodeTexImage');t.image=images['Normal'];normal_node=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],normal_node.inputs['Color']);l.new(normal_node.outputs[0],p.inputs['Normal'])
    t=n.new('ShaderNodeTexImage');t.image=images['MetallicSmoothness'];sep=n.new('ShaderNodeSeparateColor');l.new(t.outputs[0],sep.inputs[0]);l.new(sep.outputs['Red'],p.inputs['Metallic'])
    return mat

rockmat=texture_set('RB_P06_Sandstone','rock',1024)
foliage=texture_set('RB_P06_Foliage','foliage',512)
roadside=texture_set('RB_P06_Roadside','roadside',1024)
texture_set('RB_P06_Asphalt','asphalt',512);texture_set('RB_P06_Gravel','gravel',512)

def empty(name):
    o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);return o

def finish(o,name,mat,tile=None,bevel=0,smooth=True):
    o.name=name;bpy.context.view_layer.objects.active=o
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    if bevel:
        m=o.modifiers.new('Edge roundover','BEVEL');m.width=bevel;m.segments=2;bpy.ops.object.modifier_apply(modifier=m.name)
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(65),island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
    if tile is not None:
        for uv in o.data.uv_layers.active.data:uv.uv=((tile%4+.035+.93*uv.uv.x)/4,(tile//4+.035+.93*uv.uv.y)/4)
    o.data.uv_layers.active.name='UV0_IntentionalComponentMaterialReuse'
    o.data.materials.clear();o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=smooth
    o['uv_reuse']='Disconnected repeated components reuse material surface UV intentionally'
    return o

def box(name,pos,size,mat,tile,bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=1,location=bv(pos));o=bpy.context.object;o.dimensions=(size[0],size[2],size[1]);return finish(o,name,mat,tile,bevel,False)

def rod(name,a,b,r,mat,tile=None,sides=10):
    a,b=bv(a),bv(b);d=b-a;bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=d.length,location=(a+b)*.5);o=bpy.context.object;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return finish(o,name,mat,tile)

def ellipsoid(name,pos,size,mat,segments=8,rings=4,dry=False):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,radius=1,location=bv(pos));o=bpy.context.object;o.scale=(size[0]/2,size[2]/2,size[1]/2);finish(o,name,mat)
    for uv in o.data.uv_layers.active.data:uv.uv.x=.015+uv.uv.x*.47+(.5 if dry else 0)
    return o

def mesh_obj(name,verts,faces,mat,tile=None):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata([bv(v) for v in verts],[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);return finish(o,name,mat,tile)

def eroded_chunk(seed,center,width,depth,height,segments=20,rings=20):
    rng=random.Random(seed);phase=rng.random()*math.tau;v=[];f=[]
    for j in range(rings+1):
        y=height*j/rings;profile=1-.15*(j/rings)+.08*math.sin(j*.83+phase)
        # Fine terraces erode the same continuous volume, not disconnected stacked blocks.
        profile+=.035*math.sin(j*2.5)
        for k in range(segments):
            a=k*math.tau/segments;radius=profile*(1+.065*math.sin(a*5+phase)+.04*math.sin(a*9+j*.3))
            v.append((center[0]+math.cos(a)*width*.5*radius,center[1]+y,center[2]+math.sin(a)*depth*.5*radius))
            if j:
                p=(j-1)*segments+k;q=(j-1)*segments+(k+1)%segments;f.append((p,q,q+segments,p+segments))
    f.extend([tuple(reversed(range(segments))),tuple(rings*segments+k for k in range(segments))])
    obj=mesh_obj('Eroded sandstone',v,f,rockmat)
    # Cylindrical sides keep authored strata horizontal; reserve two separate cap islands.
    for polygon in obj.data.polygons:
        coords=[]
        for idx in polygon.loop_indices:
            point=obj.data.vertices[obj.data.loops[idx].vertex_index].co
            x=-point.x-center[0];z=-point.y-center[2];y=point.z-center[1]
            u=(math.atan2(z/depth,x/width)/math.tau)%1
            if u>1-.00001:u=0
            coords.append((idx,x,y,z,u))
        if polygon.index<rings*segments:
            seam=max(c[4] for c in coords)-min(c[4] for c in coords)>.5
            for idx,x,y,z,u in coords:
                if seam and u<.5:u+=1
                obj.data.uv_layers.active.data[idx].uv=(.01+.98*u,.20+.78*y/height)
        else:
            cx=.25 if polygon.index==rings*segments else .75
            for idx,x,y,z,u in coords:obj.data.uv_layers.active.data[idx].uv=(cx+x/width*.12,.085+z/depth*.12)
    return obj

def combine(parts,name,parent):
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name=name;scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');o.parent=parent;return o

def clean_lod_components(mesh):
    # Collapse simplification may flatten a tiny twig/blade to two opposed faces.
    # Remove those zero-volume components rather than shipping invisible geometry.
    bm=bmesh.new();bm.from_mesh(mesh);seen=set();discard=[]
    for vertex in bm.verts:
        if vertex in seen:continue
        stack=[vertex];seen.add(vertex);vertices=[];faces=set()
        while stack:
            v=stack.pop();vertices.append(v);faces.update(v.link_faces)
            for e in v.link_edges:
                neighbor=e.other_vert(v)
                if neighbor not in seen:seen.add(neighbor);stack.append(neighbor)
        origin=sum((v.co for v in vertices),Vector())/len(vertices);volume=0
        for face in faces:
            a=face.verts[0].co-origin
            for i in range(1,len(face.verts)-1):volume+=a.dot((face.verts[i].co-origin).cross(face.verts[i+1].co-origin))/6
        if abs(volume)<1e-9 or len(faces)<4:discard.extend(vertices)
        elif volume<0:bmesh.ops.reverse_faces(bm,faces=list(faces))
    if discard:bmesh.ops.delete(bm,geom=discard,context='VERTS')
    bm.to_mesh(mesh);bm.free();mesh.update()

def reduce_grass_components(mesh,ratio):
    bm=bmesh.new();bm.from_mesh(mesh);seen=set();components=[]
    for vertex in bm.verts:
        if vertex in seen:continue
        stack=[vertex];seen.add(vertex);component=[]
        while stack:
            v=stack.pop();component.append(v)
            for edge in v.link_edges:
                neighbor=edge.other_vert(v)
                if neighbor not in seen:seen.add(neighbor);stack.append(neighbor)
        components.append(component)
    count=max(3,round(len(components)*ratio));keep={int(i*len(components)/count) for i in range(count)}
    discard=[v for i,component in enumerate(components) if i not in keep for v in component]
    if discard:bmesh.ops.delete(bm,geom=discard,context='VERTS')
    bm.to_mesh(mesh);bm.free();mesh.update()

reports=[];roots=[]
def register(name,parts,ratios=(.43,.15)):
    root=empty(name);roots.append(root);base=combine(parts,name+'_L0_Mesh',root)
    for level,ratio in enumerate(ratios,1):
        o=base.copy();o.data=base.data.copy();scene.collection.objects.link(o);o.parent=root;o.name=name+'_L'+str(level)+'_Mesh'
        bpy.context.view_layer.objects.active=o
        if name.endswith('DryGrass'):reduce_grass_components(o.data,ratio)
        else:
            m=o.modifiers.new('LOD simplification','DECIMATE');m.ratio=ratio;m.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=m.name);clean_lod_components(o.data)
        o.hide_render=True
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for o in root.children:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=OUT+name+'.fbx',use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,bake_anim=False,add_leaf_bones=False)
    lods=[]
    for o in root.children:
        o.data.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(o.data)
        lods.append({'name':o.name,'triangles':len(o.data.loop_triangles),'vertices':len(o.data.vertices),'nonManifoldEdges':sum(not e.is_manifold for e in bm.edges),'degenerateFaces':sum(f.calc_area()<1e-10 for f in bm.faces),'looseVertices':sum(not v.link_faces for v in bm.verts),'uvOutside01':sum(not(-1e-5<=uv.uv.x<=1.00001 and -1e-5<=uv.uv.y<=1.00001) for uv in o.data.uv_layers.active.data)})
        bm.free()
    assert all(x['nonManifoldEdges']==0 and x['degenerateFaces']==0 and x['looseVertices']==0 and x['uvOutside01']==0 for x in lods),lods
    reports.append({'asset':name,'lods':lods,'material':base.data.materials[0].name,'pivot':'ground center','uvReuse':'Intentional surface reuse between disconnected components and between LODs','source':'canyon-v1.png inspected before modeling'})
    return root

register('RB_P06_RockA',[eroded_chunk(11,(-.65,0,0),2.7,2.1,4.3),eroded_chunk(18,(.85,0,.15),1.9,2.4,2.8),eroded_chunk(21,(-.1,0,1.0),2.2,1.6,1.45)])
register('RB_P06_RockB',[eroded_chunk(32,(0,0,0),4.8,3.4,2.3,24,15),eroded_chunk(33,(1.5,0,.7),1.8,1.8,1.2,16,10)])

rng=random.Random(530);parts=[]
for i in range(15):
    a=i*2.399;y=.36+rng.random()*.54;r=.13+rng.random()*.30;tip=(math.cos(a)*r,y,math.sin(a)*r)
    parts.append(rod('Sage branch',(0,.06,0),tip,.012,foliage,sides=6))
    for j in range(3):
        p=(tip[0]+math.sin(a+j)*.085,tip[1]-.14+j*.045,tip[2]+math.cos(a-j)*.065)
        parts.append(ellipsoid('Sage leaf cluster',p,(.14,.20,.14),foliage))
register('RB_P06_Sage',parts,(.42,.12))
parts=[];rng=random.Random(811)
for i in range(31):
    a=i*2.399;h=.21+rng.random()*.38;lean=.06+rng.random()*.16;w=.007+rng.random()*.008;cx=math.cos(a)*.065;cz=math.sin(a)*.065
    verts=[(cx-w,0,cz),(cx+w,0,cz),(cx,.01,cz+.012),(cx+math.cos(a)*lean,h,cz+math.sin(a)*lean)]
    leaf=mesh_obj('Dry grass blade',verts,[(0,2,1),(0,1,3),(1,2,3),(2,0,3)],foliage)
    for uv in leaf.data.uv_layers.active.data:uv.uv.x=.51+uv.uv.x*.47
    parts.append(leaf)
register('RB_P06_DryGrass',parts,(.60,.28))

parts=[box('Post',(0,.47,z),(.11,.94,.13),roadside,0) for z in [-1.35,1.35]]
# Closed extruded W-beam section; four metre length follows local forward +Z.
profile=[(-.035,.67),(.025,.72),(-.01,.80),(.025,.88),(-.035,.94),(-.06,.94),(-.005,.88),(-.04,.80),(-.005,.72),(-.06,.67)]
verts=[(x,y,z) for z in [-2,2] for x,y in profile];n=len(profile);faces=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]
for i in range(n):faces.append((i,(i+1)%n,(i+1)%n+n,i+n))
parts.append(mesh_obj('W beam',verts,faces,roadside,1))
for z in [-1.35,1.35]:parts.append(rod('Fixing bolt',(.033,.80,z),(.06,.80,z),.018,roadside,5,8))
register('RB_P06_Guardrail',parts,(.68,.38))

parts=[box('Sign post',(x,.86,0),(.065,1.72,.075),roadside,1,.004) for x in [-.22,.22]]
board=box('Chevron board',(0,1.42,0),(.66,.88,.04),roadside,2,.018)
# Planar faces use the same sign tile; intentional front/back reuse.
for polygon in board.data.polygons:
    if abs(polygon.normal.y)<.98:
        for idx in polygon.loop_indices:board.data.uv_layers.active.data[idx].uv.x-=.25
        continue
    for idx in polygon.loop_indices:
        vertex=board.data.vertices[board.data.loops[idx].vertex_index].co
        x=-vertex.x/.66+.5;y=vertex.z/.88+.5
        board.data.uv_layers.active.data[idx].uv=((2+.05+.9*x)/4,(.05+.9*y)/4)
parts.append(board);register('RB_P06_Chevron',parts,(.60,.30))

parts=[rod('Timber pole',(0,0,0),(.04,7.0,0),.105,roadside,0,12),box('Cross arm',(0,6.35,0),(2.25,.14,.14),roadside,0,.012)]
for x in [-.9,0,.9]:
    parts.append(rod('Insulator spindle',(x,6.35,0),(x,6.75,0),.025,roadside,1,8))
    for y in [6.53,6.60,6.67]:parts.append(rod('Ceramic insulator',(x,y-.025,0),(x,y+.025,0),.075,roadside,4,10))
parts.append(rod('Cross brace',(-.8,6.32,0),(0,5.7,0),.027,roadside,5,8))
parts.append(rod('Cross brace',(.8,6.32,0),(0,5.7,0),.027,roadside,5,8))
register('RB_P06_UtilityPole',parts,(.5,.22))

# Source review lineup only; FBX roots were exported at ground origin before this.
for i,root in enumerate(roots):root.location=bv(((i-3)*4.0,0,0))
world=bpy.data.worlds.new('Canyon studio');scene.world=world;world.use_nodes=True;world.node_tree.nodes.get('Background').inputs[0].default_value=(.15,.19,.24,1);world.node_tree.nodes.get('Background').inputs[1].default_value=.7
for name,pos,energy,size in [('Key',(0,12,8),2300,12),('Rim',(-8,8,-4),1800,10)]:
    data=bpy.data.lights.new(name,'AREA');o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=bv(pos);data.energy=energy;data.size=size;o.rotation_euler=(bv((0,2,0))-o.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',data);scene.collection.objects.link(cam);cam.location=bv((16,11,24));cam.rotation_euler=(bv((0,2.2,0))-cam.location).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';data.ortho_scale=30;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.render.resolution_x=1800;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG';scene.render.filepath=DOC+'environment-render.png'
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P06/Environment/RB_P06_CanyonKit.blend')
bpy.ops.render.render(write_still=True)
receipt={'passed':True,'assets':reports,'concept':'ArtSource/Concepts/P06/canyon-v1.png','newOriginalGeometryAndTextures':True,'unit':'meter','forward':'+Z Unity','intentionalUvReuse':True,'lighting':'dynamic; static scenery uses shadows and ambient/probes, not baked lightmaps'}
print(json.dumps(receipt))
