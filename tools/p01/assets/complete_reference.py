"""Catalog source variants and export documented code evidence.

Cloud dimensions are explicitly hypotheses. They are not a completed reverse
gate merely because the candidate images look plausible.
"""
from common import *
from PIL import Image

RANGES = [
    ('course_resource_bindings',0x441940,0x441a1d,'CRS resource loading and native post-processing'),
    ('nod_relocate',0x447b80,0x447bfd,'type0 links8/12; type1/2 links8/12/16; types3/4 terminal'),
    ('nod_segment_binding',0x447db0,0x447e2e,'bind type0 segment index to SGS stride52 record'),
    ('sgs_relocate',0x447e50,0x447ee9,'SGS count at8, records at16, stride52, pointer slots1..12'),
    ('course_bind',0x448030,0x44807c,'NOD and SGS global bindings 0x475334 and 0x475330'),
    ('path_reader',0x451970,0x451a80,'signed16 start/end; signed8 pairs; accumulate second byte per256 units'),
    ('object_bitfields',0x451a90,0x451b55,'RROB packed32 field extraction and spacing expression'),
    ('segment_consumer_bind',0x452cb0,0x452d68,'native consumers for every used SGS slot'),
    ('family_resource_lookup',0x415ad0,0x415afb,'resource lookup explicitly selects FAM FourCC'),
    ('course_family_preload',0x44b170,0x44b1d5,'RRSM state1 +8 FAM id and+5 slot'),
    ('course_family_stream',0x452310,0x452560,'stream event longitudinal activation and state transitions'),
    ('mountain_layout',0x45112d,0x4511d4,'two16-byte banks and sample stream pointer'),
    ('segment_traversal',0x452e10,0x452f50,'node lengths shifted8, type0 chain and branch1/2 handling'),
    ('cans_sequence_lookup',0x40b5a0,0x40b5e7,'version header and16+28*frame count sequence stride'),
    ('cans_frame_lookup',0x40b6f0,0x40b7a3,'one-based frame index at frame+2; RRFD stride28'),
    ('cans_rate_conversion',0x40b567,0x40b59c,'sequence timing field at+8 divided by20 into runtimebyte12'),
    ('rran_loader',0x44a200,0x44a349,'RRFD relocation,dimensions low16,native threeframe LOD aliases'),
    ('mip_relocation',0x40b7b0,0x40b800,'PC mip relative pointers and RRFD dimension masking'),
    ('family_leaf_dispatch',0x44aa80,0x44ab7c,'CLGP,FORM,CANS,RRAN runtime type handling'),
    ('dat_load_calls',0x443610,0x44369d,'326 rider/shadow and45 cop/shadow frame table loaders'),
    ('dat_loader',0x4436a0,0x4437a0,'DAT width/height bytes, pixel pointer and empty-slot handling'),
    ('root4_primary_variant_selection',0x44b706,0x44b78b,'root4 renderer explicitly selects secondary-index0 and frame2; native PC path'),
    ('family_two_level_selector',0x44acd0,0x44ad9e,'family root indexEDX and child selection from stack argument'),
    ('animation_60hz_updater',0x43ae90,0x43afd0,'signed descriptor duration byte plus60Hz clock; exact deadline/frame advance'),
]

def main():
    evidence_slices(RANGES)
    raw=(SOURCE/'DATA/PALETTE.RAW').read_bytes()
    palette=[c for i in range(256) for c in raw[i*4:i*4+3]]
    clouds=[]
    for name,width in [('BIGCLOUD.BOB',512),('LILCLOUD.BOB',256)]:
        path=next((SOURCE/'IMAGES').rglob(name));data=path.read_bytes()
        image=Image.frombytes('P',(width,len(data)//width),data);image.putpalette(palette)
        target=OUTPUT/(name+'_candidate.png');image.save(target)
        clouds.append({'source':path.relative_to(SOURCE).as_posix(),'bytes':len(data),
                       'candidate_width':width,'candidate_height':len(data)//width,
                       'candidate':target.relative_to(OUTPUT).as_posix(),
                       'status':'INFERRED_DIMENSIONS_NOT_LOADER_VERIFIED',
                       'reason':'power-of-two dimensions and 2x Hi/Lo scale; no literal loader reference found'})
    save_json(OUTPUT/'cloud_candidates.json',clouds)
    anims=json.loads((OUTPUT/'animation_catalog.json').read_text())
    mappings=[]
    for rid,name in [(1,'LOBOB.DAT'),(2,'LOCOP.DAT'),(3,'LOSHADOW.DAT'),(4,'LOSHADOC.DAT')]:
        animation=next(a for a in anims if a['identity']==f'DATA/GLOBAL.RSC/ANIM/{rid}')
        frames=dat_frames((SOURCE/'DATA/BIKERS'/name).read_bytes())
        assert len(frames)==len(animation['frames'])
        mismatch=[]
        for frame,descriptor in zip(frames,animation['frames']):
            if frame['pixel_bytes'] and (frame['width'],frame['height'])!=(descriptor['width_low16'],descriptor['height_low16']):
                mismatch.append({'index':frame['index'],'dat':[frame['width'],frame['height']],
                                 'rrfd':[descriptor['width_low16'],descriptor['height_low16']]})
        mappings.append({'rran':animation['identity'],'dat':name,'slots':len(frames),
                         'nonempty':sum(bool(f['pixel_bytes']) for f in frames),
                         'nonempty_dimension_mismatches':mismatch,
                         'mapping_status':'SLOT_AND_ROLE_CORRESPONDENCE; independent DAT renderer, no byte-copy alias asserted'})
    save_json(OUTPUT/'dat_rrfd_reconciliation.json',mappings)
    import csv
    from collections import defaultdict
    use=defaultdict(set);events=[]
    endpoint_mismatches=[]
    fams=json.loads((REPO/'docs/reverse-engineering/assets/families.json').read_text())
    famids={f['id'] for f in fams}
    for path in sorted((OUTPUT/'courses').glob('*.json')):
        parsed=json.loads(path.read_text())
        for chunk in parsed['SGS']['chunks']:
            for event in chunk.get('stream_events',[]):
                fid=event['family_id_when_state1']
                if fid is not None:
                    assert fid in famids
                    use[fid].add(path.stem)
                    events.append({'course':path.stem,'chunk_offset':chunk['offset'],**event})
            if chunk['tag']=='RPTH' and not chunk['endpoint_sum_matches_header']:
                endpoint_mismatches.append({'course':path.stem,'chunk_offset':chunk['offset'],
                                           'sample_count':chunk['count_field'],
                                           'start':chunk['endpoint_accumulator_start_raw'],
                                           'header_end':chunk['endpoint_accumulator_end_raw'],
                                           'accumulated_end':chunk['reconstructed_accumulator_raw'][-1]})
    groups={c['group']:c for c in json.loads((OUTPUT/'atlas_groups.json').read_text())}
    ledger=[]
    for fam in fams:
        if len(fam['nodes'])==1 and fam['nodes'][0]['kind']=='EMPTY':continue
        group=groups[f'family_{fam["id"]:03d}']
        ledger.append({'reference_id':f'FAM-{fam["id"]:03d}',
                       'course_references':';'.join(sorted(use[fam['id']])),
                       'source_animation_names':';'.join(group['source_animation_names']),
                       'research_atlas_pages':';'.join(group['pages']),
                       'new_production_source':'','new_production_asset_ids':'',
                       'status':'REFERENCE_READY_NEW_AUTHORING_REQUIRED',
                       'unit_note':'Compound family containing texture and animation variants; not an independent model count'})
    save_json(OUTPUT/'course_family_references.json',events)
    save_json(OUTPUT/'path_endpoint_differences.json',endpoint_mismatches)
    save_json(OUTPUT/'content_reference_ledger.json',ledger)
    with (OUTPUT/'content_reference_ledger.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(ledger[0]));writer.writeheader();writer.writerows(ledger)
    print(json.dumps({'evidence_slices':len(RANGES),'cloud_candidates':len(clouds),
                      'family_stream_events':len(events),'families_referenced':len(use),
                      'content_ledger_rows':len(ledger),'path_endpoint_mismatches':len(endpoint_mismatches)},indent=2))

if __name__=='__main__':
    main()
