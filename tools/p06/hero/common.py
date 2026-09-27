"""Shared original P06 authoring helpers. Execute within the live Blender MCP."""
import bpy,bmesh,math,json
from array import array
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/'
OUT=ROOT+'Assets/RacingBois/Art/P06/Hero/'
def bv(v):return Vector((-v[0],-v[2],v[1]))
def begin(name):
    bpy.ops.wm.save_as_mainfile(filepath=ROOT+'_local/p06-before-'+name+'.blend')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
    return s
def atlas(name,palette,size=1024,surface_source=None):
    images={}
    for kind in ['BaseColor','Normal','MetallicSmoothness','Roughness']:
        if surface_source and kind!='BaseColor':
            images[kind]=bpy.data.images.load(OUT+surface_source+'_'+kind+'.png',check_existing=True)
            images[kind].colorspace_settings.name='Non-Color'
            continue
        dim=size if kind=='BaseColor' else size//2
        pixels=array('f')
        for y in range(dim):
            for x in range(dim):
                tile=x//(dim//4)+(y//(dim//4))*4
                color,metal,rough,surface=palette[tile]
                grain=math.sin(x*2.17+math.sin(y*.53))*math.cos(y*2.33+x*.12)
                weave=math.sin(x*math.pi*.5)*math.sin(y*math.pi*.5)
                relief=grain*.015
                if surface=='cloth':relief=weave*.028+grain*.016
                elif surface=='leather':relief=grain*.026+math.sin(x*.12)*math.sin(y*.12)*.012
                elif surface=='brushed':relief=math.sin(y*1.71+math.sin(x*.13))*.025
                elif surface=='rubber':relief=grain*.02
                elif surface=='paint':relief=grain*.002
                rr=max(0,min(1,rough-relief))
                if kind=='BaseColor':value=tuple(max(.001,min(.99,c+relief)) for c in color)+(1,)
                elif kind=='MetallicSmoothness':value=(metal,1,0,1-rr)
                elif kind=='Roughness':value=(rr,rr,rr,1)
                else:
                    nx=relief*.55;ny=math.sin(y*2.33+x*.12)*relief*.5;length=math.sqrt(nx*nx+ny*ny+1)
                    value=(.5+.5*nx/length,.5+.5*ny/length,.5+.5/length,1)
                pixels.extend(value)
        img=bpy.data.images.new(name+'_'+kind,dim,dim,alpha=True)
        if kind!='BaseColor':img.colorspace_settings.name='Non-Color'
        img.pixels.foreach_set(pixels);img.filepath_raw=OUT+name+'_'+kind+'.png';img.file_format='PNG';img.save();img.pack();images[kind]=img
    mat=bpy.data.materials.new(name);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;s=next(node for node in n if node.type=='BSDF_PRINCIPLED')
    for kind,dest in [('BaseColor','Base Color'),('Roughness','Roughness')]:
        node=n.new('ShaderNodeTexImage');node.image=images[kind];l.new(node.outputs['Color'],s.inputs[dest])
    node=n.new('ShaderNodeTexImage');node.image=images['Normal'];normal=n.new('ShaderNodeNormalMap');l.new(node.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],s.inputs['Normal'])
    node=n.new('ShaderNodeTexImage');node.image=images['MetallicSmoothness'];sep=n.new('ShaderNodeSeparateColor');l.new(node.outputs['Color'],sep.inputs['Color']);l.new(sep.outputs['Red'],s.inputs['Metallic'])
    return mat
def empty(name,parent=None,pos=(0,0,0)):
    o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.location=bv(pos)
    if parent:o.parent=parent
    return o
def finish(o,name,tile,mat,bevel=0):
    o.name=name;bpy.context.view_layer.objects.active=o
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    if bevel:
        m=o.modifiers.new('Manufactured roundover','BEVEL');m.width=bevel;m.segments=3
        bpy.ops.object.modifier_apply(modifier=m.name)
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.035);bpy.ops.object.mode_set(mode='OBJECT')
    for uv in o.data.uv_layers.active.data:uv.uv=((tile%4+.06+.88*uv.uv.x)/4,(tile//4+.06+.88*uv.uv.y)/4)
    o.data.uv_layers.active.name='UV0_MaterialAtlas_IntentionalReuse'
    o.data.materials.clear();o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
    o['atlas_tile']=tile;o['original_geometry']=True
    return o
def box(name,pos,size,tile,mat,bevel=.012):
    bpy.ops.mesh.primitive_cube_add(size=1,location=bv(pos));o=bpy.context.object;o.dimensions=(size[0],size[2],size[1]);return finish(o,name,tile,mat,bevel)
def sphere(name,pos,size,tile,mat,segments=24,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,radius=1,location=bv(pos));o=bpy.context.object;o.scale=(size[0]/2,size[2]/2,size[1]/2);return finish(o,name,tile,mat)
def rod(name,a,b,r,tile,mat,sides=12):
    a,b=bv(a),bv(b);d=b-a;bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=d.length,location=(a+b)*.5)
    o=bpy.context.object;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return finish(o,name,tile,mat)
def torus(name,pos,major,minor,tile,mat,segments=40,minor_segments=8,axis='X'):
    rotation=(0,math.pi/2,0) if axis=='X' else ((math.pi/2,0,0) if axis=='Y' else (0,0,0))
    bpy.ops.mesh.primitive_torus_add(major_segments=segments,minor_segments=minor_segments,major_radius=major,minor_radius=minor,location=bv(pos),rotation=rotation)
    return finish(bpy.context.object,name,tile,mat)
def tube(name,points,r,tile,mat,sides=8):
    verts=[];faces=[]
    for i,p in enumerate(points):
        t=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)]);t.normalize();helper=Vector((0,1,0)) if abs(t.y)<.9 else Vector((1,0,0));a=t.cross(helper).normalized();b=t.cross(a).normalized()
        for j in range(sides):verts.append(bv(Vector(p)+r*(a*math.cos(j*math.tau/sides)+b*math.sin(j*math.tau/sides))))
        if i:
            for j in range(sides):faces.append(((i-1)*sides+j,(i-1)*sides+(j+1)%sides,i*sides+(j+1)%sides,i*sides+j))
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))]);mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);return finish(o,name,tile,mat)
def join(parts,name,parent,pivot=(0,0,0)):
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name=name
    bpy.context.scene.cursor.location=bv(pivot);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');bpy.context.view_layer.update();world=o.matrix_world.copy();o.parent=parent;o.matrix_world=world;return o
def lod_copy(obj,name,ratio,parent):
    o=obj.copy();o.data=obj.data.copy();bpy.context.scene.collection.objects.link(o);world=o.matrix_world.copy();o.parent=parent;o.matrix_world=world;o.name=name;bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('LOD topology simplification','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name);o.hide_render=True;return o
def uv_intersection_area(first,second):
    clip=list(second);result=list(first)
    if (clip[1][0]-clip[0][0])*(clip[2][1]-clip[0][1])-(clip[1][1]-clip[0][1])*(clip[2][0]-clip[0][0])<0:clip.reverse()
    for i in range(3):
        a,b=clip[i],clip[(i+1)%3];current=result;result=[]
        if not current:break
        previous=current[-1];dp=(b[0]-a[0])*(previous[1]-a[1])-(b[1]-a[1])*(previous[0]-a[0])
        for point in current:
            dc=(b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0])
            if (dp>=-1e-12)!=(dc>=-1e-12) and abs(dp-dc)>1e-20:
                t=dp/(dp-dc);result.append((previous[0]+t*(point[0]-previous[0]),previous[1]+t*(point[1]-previous[1])))
            if dc>=-1e-12:result.append(point)
            previous=point;dp=dc
    return abs(sum(result[i][0]*result[(i+1)%len(result)][1]-result[(i+1)%len(result)][0]*result[i][1] for i in range(len(result)))*.5) if len(result)>=3 else 0
def export(root,name,animation=False):
    for obj in root.children_recursive:
        if obj.type!='MESH':continue
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        # Drop only collapsed, negligible detail components at reduced LOD.
        bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();unseen=set(v.index for v in bm.verts);remove=[]
        while unseen:
            pending=[bm.verts[next(iter(unseen))]];vertices=set();faces=set()
            while pending:
                v=pending.pop()
                if v in vertices:continue
                vertices.add(v);unseen.discard(v.index);faces.update(v.link_faces);pending.extend(e.other_vert(v) for e in v.link_edges if e.other_vert(v) not in vertices)
            volume=0
            for face in faces:
                for i in range(1,len(face.verts)-1):volume+=face.verts[0].co.dot(face.verts[i].co.cross(face.verts[i+1].co))/6
            if volume<=1e-13:remove.extend(vertices)
        if remove:bmesh.ops.delete(bm,geom=remove,context='VERTS')
        bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
        # Smart unwrap triangulated, final topology, retaining the material tile
        # for each surface. This avoids projection folds on nonplanar quads.
        uv=obj.data.uv_layers.active
        tiles=[min(15,max(0,int(uv.data[p.loop_indices[0]].uv.x*4)+4*int(uv.data[p.loop_indices[0]].uv.y*4))) for p in obj.data.polygons]
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(50),island_margin=.01);bpy.ops.object.mode_set(mode='OBJECT')
        uv=obj.data.uv_layers.active
        for polygon,tile in zip(obj.data.polygons,tiles):
            for index in polygon.loop_indices:
                value=uv.data[index].uv;value.x=(tile%4+.06+.88*value.x)/4;value.y=(tile//4+.06+.88*value.y)/4
        # Very thin bevel islands can still fold in smart projection. Isolate
        # only those triangles in a reserved strip of their same material tile.
        triangles=[];repair=set()
        for polygon in obj.data.polygons:
            points=[tuple(uv.data[i].uv) for i in polygon.loop_indices]
            if abs(sum(points[i][0]*points[(i+1)%3][1]-points[(i+1)%3][0]*points[i][1] for i in range(3)))*.5<1e-12:repair.add(polygon.index)
            bounds=(min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points));triangles.append((bounds[0],polygon.index,points,bounds))
        triangles.sort()
        for i,first in enumerate(triangles):
            a=first[3]
            for second in triangles[i+1:]:
                b=second[3]
                if b[0]>=a[2]-1e-12:break
                if a[3]<=b[1]+1e-12 or b[3]<=a[1]+1e-12:continue
                if uv_intersection_area(first[2],second[2])>1e-9:repair.add(second[1])
        reserved={}
        for index in sorted(repair):reserved.setdefault(tiles[index],[]).append(index)
        for tile,indices in reserved.items():
            for j,index in enumerate(indices):
                x=(tile%4+.012)/4;y=(tile//4+.06+.88*j/len(indices))/4;h=.88/len(indices)/4*.8;w=.028/4
                for loop,value in zip(obj.data.polygons[index].loop_indices,[(x,y),(x+w,y),(x,y+h)]):uv.data[loop].uv=value
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for o in root.children_recursive:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=OUT+name+'.fbx',use_selection=True,object_types={'MESH','EMPTY','ARMATURE'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,add_leaf_bones=False,bake_anim=animation,bake_anim_use_all_actions=animation,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,path_mode='AUTO')
def studio(target=(0,.65,0),camera_pos=(3,1.8,3.7),resolution=(1280,900)):
    s=bpy.context.scene;world=bpy.data.worlds.new('P06 soft studio');s.world=world;world.use_nodes=True;world.node_tree.nodes.get('Background').inputs[0].default_value=(.11,.13,.16,1);world.node_tree.nodes.get('Background').inputs[1].default_value=.65
    for name,pos,power,size in [('Key',(3,4,2),700,4),('Rim',(-3,3,-2),1000,3),('Fill',(0,2,4),300,3)]:
        data=bpy.data.lights.new(name,'AREA');o=bpy.data.objects.new(name,data);s.collection.objects.link(o);o.location=bv(pos);data.energy=power;data.shape='DISK';data.size=size;o.rotation_euler=(bv(target)-o.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('Review');o=bpy.data.objects.new('Review',data);s.collection.objects.link(o);o.location=bv(camera_pos);o.rotation_euler=(bv(target)-o.location).to_track_quat('-Z','Y').to_euler();data.lens=58;s.camera=o
    s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=resolution[0];s.render.resolution_y=resolution[1];s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def save_render(name):
    s=bpy.context.scene;s.render.filepath=ROOT+'docs/p06/hero/'+name+'-render.png';bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P06/Hero/'+name+'.blend');bpy.ops.render.render(write_still=True)
