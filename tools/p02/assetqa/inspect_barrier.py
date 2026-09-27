"""Read-only Blender MCP inspection; no operators, scene edits or saves."""
import bpy
import bmesh
import math
import json

EPS = 1e-10

def area2(poly):
    return sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1]
               for i in range(len(poly))) if len(poly)>=3 else 0.0

def cross2(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])

def intersection_area(first,second):
    output=list(first)
    clip=list(second)
    if area2(clip)<0:
        clip.reverse()
    for i in range(3):
        a,b=clip[i],clip[(i+1)%3]
        current=output
        output=[]
        if not current:
            break
        prev=current[-1]
        dp=cross2(a,b,prev)
        for point in current:
            dc=cross2(a,b,point)
            prev_inside=dp>=-1e-12
            inside=dc>=-1e-12
            if inside!=prev_inside:
                denom=dp-dc
                if abs(denom)>1e-20:
                    t=dp/denom
                    output.append((prev[0]+t*(point[0]-prev[0]),prev[1]+t*(point[1]-prev[1])))
            if inside:
                output.append(point)
            prev=point
            dp=dc
    return abs(area2(output))*.5

def inspect_mesh(obj):
    mesh=obj.data
    # Loop triangulation is a derived read cache. It neither edits topology nor
    # writes .blend files. bmesh is a private detached inspection copy.
    mesh.calc_loop_triangles()
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    nonmanifold=[e.index for e in bm.edges if not e.is_manifold]
    inconsistent=[e.index for e in bm.edges if e.is_manifold and not e.is_contiguous]
    loose_vertices=[v.index for v in bm.verts if not v.link_faces]
    zero_faces=[f.index for f in bm.faces if f.calc_area()<=1e-10]
    volume=bm.calc_volume(signed=True)
    seen=set()
    components=[]
    for vertex in bm.verts:
        if vertex.index in seen:
            continue
        queue=[vertex]
        count=0
        while queue:
            at=queue.pop()
            if at.index in seen:
                continue
            seen.add(at.index)
            count+=1
            queue.extend(e.other_vert(at) for e in at.link_edges)
        components.append(count)
    coordinates={}
    duplicates=[]
    for v in mesh.vertices:
        key=tuple(round(float(c),7) for c in v.co)
        if key in coordinates:
            duplicates.append([coordinates[key],v.index])
        else:
            coordinates[key]=v.index
    uv=mesh.uv_layers.active
    uv_triangles=[]
    uv_area=0
    uv_degenerate=[]
    mesh_degenerate=[]
    out_of_bounds=[]
    for tri_index,tri in enumerate(mesh.loop_triangles):
        if tri.area<=1e-10:
            mesh_degenerate.append(tri_index)
        points=[tuple(float(c) for c in uv.data[loop].uv) for loop in tri.loops] if uv else []
        if points:
            tri_area=abs(area2(points))*.5
            uv_area+=tri_area
            if tri_area<=1e-10:
                uv_degenerate.append(tri_index)
            if any(c < -1e-7 or c > 1+1e-7 for p in points for c in p):
                out_of_bounds.append(tri_index)
            uv_triangles.append({'index':tri_index,'polygon':tri.polygon_index,'points':points,
                                 'bounds':(min(p[0] for p in points),min(p[1] for p in points),
                                           max(p[0] for p in points),max(p[1] for p in points))})
    overlaps=[]
    for i,first in enumerate(uv_triangles):
        a=first['bounds']
        for second in uv_triangles[i+1:]:
            b=second['bounds']
            if a[2]<=b[0]+1e-12 or b[2]<=a[0]+1e-12 or a[3]<=b[1]+1e-12 or b[3]<=a[1]+1e-12:
                continue
            intersection=intersection_area(first['points'],second['points'])
            if intersection>1e-9:
                overlaps.append({'triangles':[first['index'],second['index']],
                                 'polygons':[first['polygon'],second['polygon']],
                                 'intersection_uv_area':intersection})
    # Union adjacent mesh faces only when both shared endpoints have the same UV.
    parent=list(range(len(mesh.polygons)))
    def find(x):
        while parent[x]!=x:
            x=parent[x]
        return x
    edge_uv={}
    for poly in mesh.polygons:
        loops=list(poly.loop_indices)
        for k,li in enumerate(loops):
            other=loops[(k+1)%len(loops)]
            a=mesh.loops[li].vertex_index
            b=mesh.loops[other].vertex_index
            ua=tuple(round(float(x),7) for x in uv.data[li].uv)
            ub=tuple(round(float(x),7) for x in uv.data[other].uv)
            key=(min(a,b),max(a,b))
            record=(poly.index,ua if a<b else ub,ub if a<b else ua)
            if key in edge_uv:
                prior=edge_uv[key]
                if prior[1:]==record[1:]:
                    parent[find(poly.index)]=find(prior[0])
            else:
                edge_uv[key]=record
    islands=len({find(i) for i in range(len(mesh.polygons))})
    bounds=[list(v) for v in obj.bound_box]
    minimum=[min(v[i] for v in bounds) for i in range(3)]
    maximum=[max(v[i] for v in bounds) for i in range(3)]
    result={'name':obj.name,'mesh_name':mesh.name,'vertices':len(mesh.vertices),
            'edges':len(mesh.edges),'polygons':len(mesh.polygons),'triangles':len(mesh.loop_triangles),
            'dimensions_m':list(obj.dimensions),'location':list(obj.location),
            'rotation_radians':list(obj.rotation_euler),'scale':list(obj.scale),
            'parent':obj.parent.name if obj.parent else None,'local_bounds_min':minimum,'local_bounds_max':maximum,
            'transform_determinant':obj.matrix_world.determinant(),
            'nonmanifold_edges':nonmanifold,'inconsistent_winding_edges':inconsistent,
            'loose_vertices':loose_vertices,'duplicate_vertex_position_pairs':duplicates,
            'zero_area_faces':zero_faces,'zero_area_triangles':mesh_degenerate,
            'connected_components_vertices':components,'signed_volume_m3':volume,
            'uv_layers':[u.name for u in mesh.uv_layers], 'uv_islands':islands,
            'uv_total_triangle_area':uv_area,'uv_out_of_bounds_triangles':out_of_bounds,
            'uv_degenerate_triangles':uv_degenerate,'uv_positive_area_overlap_pairs':overlaps,
            'materials':[m.name if m else None for m in mesh.materials],
            'material_indices_used':sorted({p.material_index for p in mesh.polygons}),
            'unapplied_modifiers':[m.name for m in obj.modifiers],
            'smooth_faces':sum(p.use_smooth for p in mesh.polygons),
            'authored_from_scratch_property':obj.get('authored_from_scratch'),
            'source_recipe_property':obj.get('source_recipe')}
    bm.free()
    return result

root=bpy.data.objects.get('RB_RoadBarrier')
lods=[bpy.data.objects.get('RB_Barrier_LOD'+str(i)) for i in range(3)]
assert root and all(lods)
mesh_results=[inspect_mesh(obj) for obj in lods]
image_results=[]
for image in bpy.data.images:
    if not image.name.startswith('RB_Barrier_'):
        continue
    pixels=list(image.pixels)
    channels=[]
    for channel in range(4):
        values=pixels[channel::4]
        channels.append({'min':min(values),'max':max(values),'mean':sum(values)/len(values)})
    image_results.append({'name':image.name,'dimensions':list(image.size),
                          'filepath':image.filepath,'colorspace':image.colorspace_settings.name,
                          'channels':image.channels,'pixel_channel_stats':channels,
                          'source':image.source,'is_dirty':image.is_dirty})
material=bpy.data.materials.get('RB_Barrier_PaintedConcrete')
image_nodes=[{'node':n.name,'image':n.image.name if n.image else None} for n in material.node_tree.nodes if n.type=='TEX_IMAGE']
print(json.dumps({'inspection':'READ_ONLY_NO_SCENE_SAVE','blend_path':bpy.data.filepath,
                  'blender_version':bpy.app.version_string,'unit_system':bpy.context.scene.unit_settings.system,
                  'unit_scale':bpy.context.scene.unit_settings.scale_length,
                  'root':{'name':root.name,'type':root.type,'location':list(root.location),
                          'rotation_radians':list(root.rotation_euler),'scale':list(root.scale)},
                  'meshes':mesh_results,'images':image_results,'image_nodes':image_nodes,
                  'material_assignments_shared':len({id(o.data.materials[0]) for o in lods})==1,
                  'mesh_objects_in_scene':[o.name for o in bpy.context.scene.objects if o.type=='MESH']},indent=2))
