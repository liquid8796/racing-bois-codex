"""Read-only Blender MCP mesh audit, independent of the generator's checks."""
import bpy
import bmesh
import json
import math

records=[]
failures=[]
bounds=[]
def object_name(item):return item.name
audited_roots=[name for name in ['RB_Motorcycle','RB_Rider','RB_TrafficCoupe','RB_TrafficVan','RB_Pedestrian','RB_Sandstone','RB_SageScrub'] if bpy.data.objects.get(name) is not None]
if not audited_roots:raise RuntimeError('No authored Racing Bois roots in the current scene')
for root_name in audited_roots:
    root=bpy.data.objects.get(root_name)
    if root is None:raise RuntimeError('Missing authoring root '+root_name)
    vertices=[]
    for obj in root.children_recursive:
        if obj.type=='MESH' and '_L0_' in obj.name:
            transform=root.matrix_world.inverted() @ obj.matrix_world
            for vertex in obj.data.vertices:
                p=transform @ vertex.co;vertices.append((-p.x,p.z,-p.y))
    lower=[min(point[axis] for point in vertices) for axis in range(3)]
    upper=[max(point[axis] for point in vertices) for axis in range(3)]
    bounds.append({'asset':root_name,'unity_axis_min':lower,'unity_axis_max':upper,
                   'size_m':[upper[axis]-lower[axis] for axis in range(3)],
                   'center_m':[(upper[axis]+lower[axis])*.5 for axis in range(3)]})
    for obj in sorted(root.children_recursive,key=object_name):
        if obj.type!='MESH':continue
        mesh=obj.data;mesh.calc_loop_triangles()
        bm=bmesh.new();bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table();bm.edges.ensure_lookup_table()
        bad_edges=sum(1 for edge in bm.edges if not edge.is_manifold)
        bad_winding=sum(1 for edge in bm.edges if edge.is_manifold and not edge.is_contiguous)
        loose=sum(1 for vertex in bm.verts if not vertex.link_faces)
        degenerate=sum(1 for face in bm.faces if face.calc_area()<=1e-10)
        unseen=set(vertex.index for vertex in bm.verts)
        components=[];duplicates=0
        while unseen:
            start=next(iter(unseen));pending=[bm.verts[start]];indices=set();faces=set()
            while pending:
                at=pending.pop()
                if at.index in indices:continue
                indices.add(at.index);unseen.discard(at.index);faces.update(at.link_faces)
                pending.extend(edge.other_vert(at) for edge in at.link_edges if edge.other_vert(at).index not in indices)
            # Signed tetrahedron volumes evaluated per disconnected component;
            # an inverted detail cannot hide behind a larger positive body.
            volume=0.0
            for face in faces:
                first=face.verts[0].co
                for i in range(1,len(face.verts)-1):
                    volume+=first.dot(face.verts[i].co.cross(face.verts[i+1].co))/6
            coordinates=set()
            for index in indices:
                key=tuple(round(value,7) for value in bm.verts[index].co)
                if key in coordinates:duplicates+=1
                coordinates.add(key)
            components.append({'vertices':len(indices),'faces':len(faces),'positive_signed_volume':volume>1e-12})
        uv=mesh.uv_layers.active
        bad_uv=0;cross_tile=0
        for polygon in mesh.polygons:
            tiles=set()
            for index in polygon.loop_indices:
                u,v=uv.data[index].uv
                if not math.isfinite(u) or not math.isfinite(v) or not 0<=u<=1 or not 0<=v<=1:bad_uv+=1
                columns=2 if root_name in ['RB_Sandstone','RB_SageScrub'] else 4
                rows=2 if root_name in ['RB_Sandstone','RB_SageScrub','RB_Pedestrian'] else 4
                tiles.add((int(u*columns),int(v*rows)))
            if len(tiles)!=1:cross_tile+=1
        record={'mesh':obj.name,'triangles':len(mesh.loop_triangles),'components':len(components),
                'nonmanifold_edges':bad_edges,'inconsistent_winding_edges':bad_winding,
                'loose_vertices':loose,'degenerate_faces':degenerate,'duplicate_vertices_within_components':duplicates,
                'non_positive_volume_components':sum(1 for part in components if not part['positive_signed_volume']),
                'invalid_uv_coordinates':bad_uv,'faces_crossing_palette_tiles':cross_tile,
                'intentional_uv_reuse':'Repeated palette tiles between disconnected surfaces and LODs'}
        checked=['nonmanifold_edges','inconsistent_winding_edges','loose_vertices','degenerate_faces',
                 'duplicate_vertices_within_components','non_positive_volume_components','invalid_uv_coordinates','faces_crossing_palette_tiles']
        record['passed']=all(record[key]==0 for key in checked)
        if not record['passed']:failures.append(record['mesh'])
        records.append(record);bm.free()
print(json.dumps({'passed':len(failures)==0,'blender_version':bpy.app.version_string,
                  'audited_roots':audited_roots,'mesh_count':len(records),'failures':failures,'bounds':bounds,'meshes':records}))
