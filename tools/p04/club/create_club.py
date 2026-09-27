"""Original fictional game prop, modeled after club-concept-v1.png was inspected.

Every vertex and texture sample is newly authored in Blender. The reference
image guides shape/color only; it is not projected onto geometry or copied.
"""
import bpy
import bmesh
import math
import json
from mathutils import Vector

ROOT='D:/Project/Unity/racing-bois/'
OUT=ROOT+'Assets/RacingBois/Art/Weapons/Club/'
# The MCP bridge was started with factory defaults and inspected before this
# reset. Preserve that initial scene as a task-local checkpoint as requested.
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'_local/blender-before-club.blend')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1

def sample(u,v):
    if u < .67:
        # Longitudinal flowing grain and two elliptical knots, all analytic.
        bend=.007*math.sin(v*7.4)+.003*math.sin(v*31)+.0015*math.sin(v*67+u*8)
        flow=(u+bend)*310
        fibers=math.exp(-abs(math.sin(flow))*13)
        broad=.5+.5*math.sin(u*39+math.sin(v*5.3)*1.7)
        fine=.5+.5*math.sin(u*960+math.sin(v*20)*3)
        knot=0.0
        for ku,kv in [(.29,.58),(.53,.81)]:
            dx=(u-ku)*1.9;dy=(v-kv)*.40;radius=math.sqrt(dx*dx+dy*dy)
            envelope=math.exp(-radius*radius*600)
            knot+=envelope*(.25+.75*math.exp(-abs(math.sin(radius*450))*8))
        shade=.10*broad+.018*fine-.12*fibers-.30*knot
        color=(.66+shade,.355+shade*.72,.12+shade*.40,1)
        height=.06*fine-.08*fibers-.12*knot
        roughness=.50+.06*(1-broad)
        return color,height,0.0,roughness
    if v < .465:
        weave=(.5+.5*math.sin(u*610))*(.5+.5*math.sin(v*930))
        seam=(v*24+(u-.70)*1.8)%1
        edge=math.exp(-min(seam,1-seam)*55)
        shade=.028+.027*weave-.012*edge
        return (shade,shade*1.02,shade*1.07,1),.25*weave-.35*edge,0,.83
    amber=.5+.5*math.sin(u*20)
    return (.77+.10*amber,.255+.085*amber,.022,1),.01,.35,.28

def generate_texture(name,size,kind):
    image=bpy.data.images.new(name,size,size,alpha=True)
    if kind!='base':image.colorspace_settings.name='Non-Color'
    pixels=[]
    for y in range(size):
        v=(y+.5)/size
        for x in range(size):
            u=(x+.5)/size;color,height,metal,rough=sample(u,v)
            if kind=='base':value=color
            elif kind=='normal':
                delta=1/512
                nx=(sample(u-delta,v)[1]-sample(u+delta,v)[1])*.70
                ny=(sample(u,v-delta)[1]-sample(u,v+delta)[1])*.70
                inv=1/math.sqrt(nx*nx+ny*ny+1)
                value=(.5+.5*nx*inv,.5+.5*ny*inv,.5+.5*inv,1)
            elif kind=='mask':value=(metal,1,0,1-rough)
            else:value=(rough,rough,rough,1)
            pixels.extend(value)
    image.pixels=pixels;image.filepath_raw=OUT+name+'.png';image.file_format='PNG';image.save();image.pack();return image

base=generate_texture('RB_Club_BaseColor',512,'base')
normal=generate_texture('RB_Club_Normal',256,'normal')
mask=generate_texture('RB_Club_MetallicSmoothness',256,'mask')
roughness=generate_texture('RB_Club_Roughness',256,'roughness')
material=bpy.data.materials.new('RB_Club_WoodClothAmber');material.use_nodes=True
nodes=material.node_tree.nodes;links=material.node_tree.links;shader=nodes.get('Principled BSDF')
color_node=nodes.new('ShaderNodeTexImage');color_node.image=base;links.new(color_node.outputs['Color'],shader.inputs['Base Color'])
normal_node=nodes.new('ShaderNodeTexImage');normal_node.image=normal
normal_map=nodes.new('ShaderNodeNormalMap');links.new(normal_node.outputs['Color'],normal_map.inputs['Color']);links.new(normal_map.outputs['Normal'],shader.inputs['Normal'])
mask_node=nodes.new('ShaderNodeTexImage');mask_node.image=mask
separate=nodes.new('ShaderNodeSeparateColor');links.new(mask_node.outputs['Color'],separate.inputs['Color']);links.new(separate.outputs['Red'],shader.inputs['Metallic'])
rough_node=nodes.new('ShaderNodeTexImage');rough_node.image=roughness;links.new(rough_node.outputs['Color'],shader.inputs['Roughness'])

def bv(p):return(-p[0],-p[2],p[1])
def empty(name,parent=None,point=(0,0,0)):
    obj=bpy.data.objects.new(name,None);scene.collection.objects.link(obj);obj.parent=parent;obj.location=bv(point);return obj

WOOD=(.025,.025,.645,.975)
GRIP=(.705,.025,.975,.435)
AMBER=(.705,.51,.975,.625)
def lathe(vertices,faces,uv_faces,profile,segments,region):
    rings=[]
    for y,radius in profile:
        ring=[]
        count=1 if radius==0 else segments
        for j in range(count):
            angle=j*2*math.pi/segments
            ring.append(len(vertices));vertices.append(bv((math.cos(angle)*radius,y,math.sin(angle)*radius)))
        rings.append(ring)
    u0,v0,u1,v1=region
    for i in range(len(rings)-1):
        a,b=rings[i],rings[i+1];va=v0+(v1-v0)*i/(len(rings)-1);vb=v0+(v1-v0)*(i+1)/(len(rings)-1)
        for j in range(segments):
            x0=u0+(u1-u0)*j/segments;x1=u0+(u1-u0)*(j+1)/segments;mid=(x0+x1)*.5
            if len(a)==1:
                faces.append((a[0],b[j],b[(j+1)%segments]));uv_faces.append([(mid,va),(x0,vb),(x1,vb)])
            elif len(b)==1:
                faces.append((a[j],b[0],a[(j+1)%segments]));uv_faces.append([(x0,va),(mid,vb),(x1,va)])
            else:
                faces.append((a[j],b[j],b[(j+1)%segments],a[(j+1)%segments]));uv_faces.append([(x0,va),(x0,vb),(x1,vb),(x1,va)])

wood_profiles=[
    [(-.075,0),(-.074,.007),(-.071,.014),(-.065,.017),(-.059,.017),(-.055,.014),(-.051,.012),(.057,.0115),(.120,.014),(.22,.022),(.32,.033),(.39,.042),(.432,.045),(.452,.044),(.465,.034),(.473,.016),(.475,0)],
    [(-.075,0),(-.071,.014),(-.062,.017),(-.054,.012),(.057,.0115),(.17,.018),(.30,.031),(.40,.043),(.45,.044),(.47,.025),(.475,0)],
    [(-.075,0),(-.065,.017),(-.051,.012),(.057,.0115),(.25,.024),(.40,.042),(.46,.04),(.475,0)]]
grip_profiles=[
    [(-.047,0),(-.046,.0140),(-.042,.0148),(-.025,.0141),(-.005,.0147),(.015,.0141),(.035,.0146),(.053,.0148),(.057,.0140),(.0575,0)],
    [(-.047,0),(-.045,.0147),(.003,.0143),(.055,.0147),(.0575,0)],
    [(-.047,0),(-.045,.0147),(.055,.0147),(.0575,0)]]
band_profile=[(-.058,0),(-.057,.0155),(-.056,.0165),(-.049,.0165),(-.048,.0155),(-.047,0)]
root=empty('RB_Club');empty('GripOrigin',root);empty('ClubTip',root,(0,.475,0));empty('ClubButt',root,(0,-.075,0))
reports=[]
for level,segments in [(0,20),(1,12),(2,8)]:
    vertices=[];faces=[];uv_faces=[]
    lathe(vertices,faces,uv_faces,wood_profiles[level],segments,WOOD)
    lathe(vertices,faces,uv_faces,grip_profiles[level],segments,GRIP)
    lathe(vertices,faces,uv_faces,band_profile if level<2 else [(-.058,0),(-.056,.0165),(-.049,.0165),(-.047,0)],segments,AMBER)
    mesh=bpy.data.meshes.new('RB_Club_L'+str(level)+'_Mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
    uv=mesh.uv_layers.new(name='UV0_UniqueSurfaceAtlas')
    for polygon,coordinates in zip(mesh.polygons,uv_faces):
        for index,value in zip(polygon.loop_indices,coordinates):uv.data[index].uv=value
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    mesh.materials.append(material)
    for polygon in mesh.polygons:polygon.use_smooth=True
    obj=bpy.data.objects.new('RB_Club_L'+str(level),mesh);scene.collection.objects.link(obj);obj.parent=root;obj.hide_render=level!=0
    obj['authored_from_scratch']=True;obj['concept']='ArtSource/Concepts/P03P04/club-concept-v1.png'
    mesh.calc_loop_triangles();reports.append({'lod':level,'triangles':len(mesh.loop_triangles),'vertices':len(mesh.vertices),'renderers':1})
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for obj in root.children_recursive:obj.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=OUT+'RB_Club.fbx',use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
world=bpy.data.worlds.new('ClubStudio');scene.world=world;world.use_nodes=True
world.node_tree.nodes.get('Background').inputs[0].default_value=(.055,.070,.09,1);world.node_tree.nodes.get('Background').inputs[1].default_value=.6
for name,location,energy,size in [('Key',(1.1,-1.5,1.8),150,1.5),('Rim',(-1.0,.8,.8),110,1),('Fill',(.3,1.2,.2),50,1)]:
    data=bpy.data.lights.new(name,'AREA');light=bpy.data.objects.new(name,data);scene.collection.objects.link(light);light.location=location
    data.energy=energy;data.size=size;light.rotation_euler=(Vector((0,0,.20))-light.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('ClubReview');camera=bpy.data.objects.new('ClubReview',data);scene.collection.objects.link(camera)
camera.location=(.75,-1.25,.55);camera.rotation_euler=(Vector((0,0,.20))-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=68;scene.camera=camera
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.view_settings.view_transform='AgX'
scene.render.resolution_x=900;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG';scene.render.filepath=ROOT+'docs/p04/club/club-render.png'
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/Weapons/RB_Club.blend')
bpy.ops.render.render(write_still=True)
print(json.dumps({'asset':'RB_Club','concept':'ArtSource/Concepts/P03P04/club-concept-v1.png','source':'ArtSource/Weapons/RB_Club.blend',
    'length_m':.55,'axis':'prefab +Y from grip toward rounded end','pivot':'center of grip at (0,0,0)','butt_y':-.075,'tip_y':.475,
    'lods':reports,'materials':1,'textures':{'base':512,'normal':256,'metallic_smoothness':256,'roughness':256},
    'uv_policy':'Three separate unique atlas rectangles for wood, fabric grip and amber band. LODs intentionally reuse same texture.'}))
