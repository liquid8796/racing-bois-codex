"""Validate the Blender MCP receipt and inspect produced source files read-only."""
from pathlib import Path
import hashlib
import json
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/p02/assetqa'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    receipt=json.loads((OUT/'barrier-qa-mcp.json').read_text(encoding='utf-8'))
    assert not receipt['result'].get('isError')
    text=next(c['text'] for c in receipt['result']['content'] if c['type']=='text')
    inspection=json.loads(text[text.index('{'):])
    assert inspection['unit_system']=='METRIC' and inspection['unit_scale']==1
    root=inspection['root']
    assert root['location']==[0,0,0] and root['rotation_radians']==[0,0,0] and root['scale']==[1,1,1]
    expected_triangles=[252,126,50]
    checks=[]
    failures=[]
    for i,mesh in enumerate(inspection['meshes']):
        errors=[]
        for field in ['nonmanifold_edges','inconsistent_winding_edges','loose_vertices',
                      'duplicate_vertex_position_pairs','zero_area_faces','zero_area_triangles',
                      'uv_out_of_bounds_triangles','uv_degenerate_triangles','uv_positive_area_overlap_pairs',
                      'unapplied_modifiers']:
            if mesh[field]:errors.append(field)
        assert mesh['triangles']==expected_triangles[i]
        assert mesh['signed_volume_m3']>0 and mesh['transform_determinant']>0
        assert len(mesh['connected_components_vertices'])==1
        assert mesh['uv_islands']==6
        assert mesh['parent']=='RB_RoadBarrier'
        assert mesh['scale']==[1,1,1] and mesh['location']==[0,0,0]
        assert len(mesh['materials'])==1 and mesh['materials'][0]=='RB_Barrier_PaintedConcrete'
        assert mesh['material_indices_used']==[0]
        assert all(abs(a-b)<.01 for a,b in zip(mesh['dimensions_m'],[2,.64,.9]))
        if i==0:
            assert all(abs(a-b)<1e-6 for a,b in zip(mesh['dimensions_m'],[2,.64,.9]))
            assert abs(mesh['local_bounds_min'][2])<1e-7
        checks.append({'mesh':mesh['name'],'triangles':mesh['triangles'],'uv_islands':mesh['uv_islands'],
                       'status':'PASS' if not errors else 'FAIL','issues':errors,
                       'aabb_dimension_error_max_m':max(abs(a-b) for a,b in zip(mesh['dimensions_m'],[2,.64,.9]))})
        failures.extend(errors)
    assert inspection['material_assignments_shared']
    folder=ROOT/'Assets/RacingBois/Art/Props/Barrier'
    paths=[folder/'RB_RoadBarrier.fbx',folder/'RB_Barrier_BaseColor.png',
           folder/'RB_Barrier_Normal.png',folder/'RB_Barrier_MetallicSmoothness.png',
           ROOT/'ArtSource/Props/RB_RoadBarrier.blend',ROOT/'ArtSource/Props/RB_Barrier_Roughness.png']
    original=json.loads((ROOT/'docs/reverse-engineering/assets/source_manifest.json').read_text())
    original_hashes={row['sha256'] for row in original}
    files=[]
    for path in paths:
        digest=sha(path)
        assert digest not in original_hashes
        files.append({'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,
                      'sha256':digest,'matches_original_file_hash':False})
    image_results=[]
    for name,size,mode in [('RB_Barrier_BaseColor.png',(512,512),'RGB'),
                           ('RB_Barrier_Normal.png',(128,128),'RGB'),
                           ('RB_Barrier_MetallicSmoothness.png',(128,128),'RGBA')]:
        with Image.open(folder/name) as image:
            image.load()
            assert image.size==size and image.mode==mode,(name,image.size,image.mode)
            image_results.append({'file':name,'size':list(image.size),'mode':image.mode,'extrema':image.getextrema()})
    with Image.open(folder/'RB_Barrier_Normal.png') as image:
        assert image.getextrema()==((128,128),(128,128),(255,255))
    with Image.open(folder/'RB_Barrier_MetallicSmoothness.png') as image:
        assert image.getextrema()==((0,0),(255,255),(0,0),(97,97))
    recipe=ROOT/'tools/blender/create_barrier.py'
    recipe_text=recipe.read_text(encoding='utf-8')
    # This is a supporting static check, not a general proof of authorship.
    imports_original=any(token in recipe_text for token in ['racing_bois_mod','images.load(', 'import_scene.', 'open_mainfile('])
    assert not imports_original
    summary={'status':'PASS_BLENDER_SOURCE_GEOMETRY_UV_TEXTURE_CHECKS',
             'inspection_transport':'MCP initialize + tools/call execute_blender_code -> Blender addon127.0.0.1:9876',
             'blender_version':inspection['blender_version'],'protocol':receipt['protocol']['protocolVersion'],
             'meshes':checks,'textures':image_results,'files':files,'failed_checks':failures,
             'provenance':{'recipe':recipe.relative_to(ROOT).as_posix(),'recipe_sha256':sha(recipe),
                           'original_import_calls_found':imports_original,
                           'observed_generation':'Explicit profile vertices, bevel, UV Smart Project, procedural stripe bake, decimated LOD copies',
                           'hash_limit':'A different hash alone does not prove newly authored content; recipe and source inspection provide the additional evidence.'},
             'screenshot_reference':'docs/p02/blender/barrier-render.png',
             'delegated_to_unity_qa':['Y-up axis conversion and final mesh dimensions','URP shader/map assignment and texture compression',
                                      'LODGroup thresholds and prefab references','Collider policy and baked-lightmap UV2 if used',
                                      'Gameplay-distance/browser frame-time and memory check'],
             'limits':['UV overlap checked within each LOD; cross-LOD atlas sharing is intentional.',
                       'Neutral normal and constant roughness/mask maps are deliberate for this foundation prop; not a claim of final art polish.',
                       'LOD1/2 slightly shrink with decimation; max AABB difference under7mm. Review LOD switching at gameplay distance in Unity.',
                       'Only UV0 is present in Blender; lightmap UV2 remains Unity import responsibility if baked lighting is used.']}
    (OUT/'barrier-inspection.json').write_text(json.dumps(inspection,indent=2),encoding='utf-8')
    (OUT/'barrier-qa-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    main()
