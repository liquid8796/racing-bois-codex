"""Independent parser/cross-reference checks, malformed inputs, source hashes."""
from common import *
from decode_courses import decode_nod,decode_sgs
from decode_sprites import decode_cans
from decode_media import mids_to_smf
from collections import Counter
import copy
import io
import math


def rejected(function, payload):
    try:
        function(payload)
    except (AssertionError,ValueError,IndexError,struct.error):
        return True
    raise AssertionError(f'{function.__name__} accepted malformed input')


def main():
    checks=[]
    courses=[]
    for p in sorted((SOURCE/'DATA/COURSES').glob('*.CRS')):
        data=p.read_bytes();e={e['type'].strip():e for e in resources(data)['entries']}
        for kind,decoder in [('NOD',decode_nod),('SGS',decode_sgs)]:
            record=e[kind];payload=data[record['offset']:record['offset']+record['size']]
            parsed=decoder(payload)
            assert rejected(decoder,payload[:-1])
            bad=bytearray(payload);struct.pack_into('<I',bad,8,0xffffffff)
            assert rejected(decoder,bad)
            if kind=='NOD':
                bad=bytearray(payload);struct.pack_into('<I',bad,16,len(payload)+4)
                assert rejected(decoder,bad)
            checks.append({'id':f'COURSE-{p.stem}-{kind}','status':'PASS','valid_and_corrupt_inputs_checked':True})
    anim={a['identity']:a for a in json.loads((OUTPUT/'animation_catalog.json').read_text())}
    cans=json.loads((OUTPUT/'cans_decoded.json').read_text())
    links=[]
    for c in cans:
        name=c['identity']
        sibling=name.rsplit('/',1)[0]+'/0' if name.startswith('family') else name.replace('/CANS/','/ANIM/')
        a=anim[sibling]
        count=0
        for chunk in c['chunks']:
            if chunk['tag']!='CANS':continue
            for seq in chunk['sequences']:
                for frame in seq['frames']:
                    assert 1<=frame['frame_reference_1based']<=a['frame_count']
                    count+=1
        raw=bytes.fromhex(c['chunks'][0]['raw_hex'])
        assert rejected(decode_cans,raw[:-1])
        links.append({'cans':name,'rran':sibling,'frame_references_checked':count,'status':'PASS'})
    save_json(OUTPUT/'cans_rran_links.json',links)
    checks.append({'id':'CANS-RRAN-REFERENCES','status':'PASS','cans_records':len(links),
                   'frame_references':sum(x['frame_references_checked'] for x in links)})
    # An independent public MIDI parser re-opens every converted Standard MIDI
    # file, checking complete event payloads and timing against source events.
    sys.path.insert(0,str(OUTPUT/'.cache/python'))
    import mido
    midi=[]
    for p in sorted((OUTPUT/'media/midi').glob('*.MID')):
        source=SOURCE/'AUDIO/MUSIC'/p.name
        _,expected=mids_to_smf(source.read_bytes())
        independent=mido.MidiFile(p)
        assert independent.type==0 and independent.ticks_per_beat==expected['division']
        messages=[m for m in independent.tracks[0] if m.type!='end_of_track']
        assert len(messages)==len(expected['events'])
        ticks=0;seconds=0;tempo=500000
        for actual,event in zip(messages,expected['events']):
            assert actual.time==event['delta_ticks']
            ticks+=actual.time
            seconds+=actual.time*tempo/1_000_000/expected['division']
            if event['type']=='tempo':
                assert actual.type=='set_tempo' and actual.tempo==event['microseconds_per_quarter']
                tempo=actual.tempo
            else:
                assert bytes(actual.bytes()).hex()==event['message_hex']
        assert ticks==expected['total_ticks']
        assert abs(independent.length-seconds)<1e-6
        assert rejected(mids_to_smf,source.read_bytes()[:-1])
        midi.append({'path':p.name,'events':len(messages),'ticks':ticks,'duration_seconds':independent.length,'status':'MIDO_ROUNDTRIP_PASS'})
    save_json(OUTPUT/'media/midi_independent_validation.json',midi)
    checks.append({'id':'MIDI-INDEPENDENT-READER','status':'PASS','files':len(midi),'events':sum(x['events'] for x in midi)})
    image_rows=json.loads((OUTPUT/'mip_buffers.json').read_text())
    from PIL import Image
    for row in image_rows:
        with Image.open(OUTPUT/row['preview']) as image:
            image.load()
            assert image.size==(row['width'],row['height'])
            assert digest(image.tobytes())==row['levels'][0]['sha256_pixels']
    checks.append({'id':'MIP-IMAGE-ROUNDTRIP','status':'PASS','unique_buffers':len(image_rows)})
    native=json.loads((OUTPUT/'rpth_native_execution.json').read_text())
    assert len(native['paths'])==109 and all(p['all_samples_native_equal_reference'] for p in native['paths'])
    assert sum(p['directional_bias_every_sample']!=0 for p in native['paths'])==13
    assert native['node_boundary_fixture']['forward_A_to_B']['accumulator']==123
    assert native['node_boundary_fixture']['backward_B_to_A']['accumulator']==98
    checks.append({'id':'RPTH-NATIVE-BIDIRECTIONAL','status':'PASS','paths':109,
                   'native_value_assertions':native['native_value_assertions'],'seed_discrepancies_explained_as_independent_initialization':13})
    legacy=json.loads((OUTPUT/'legacy_rrfd_classification.json').read_text())
    assert sum(legacy['counts'].values())==1179
    assert legacy['cans_referenced_non_dat_missing_pixels']==0
    checks.append({'id':'LEGACY-RRFD-CLASSIFICATION','status':'PASS','counts':legacy['counts'],
                   'scope':'CANS complete sequence reachability and known direct PC family-getter calls; not global dynamic coverage'})
    durations=[s['runtime_duration_signed_byte'] for c in cans for k in c['chunks'] if k['tag']=='CANS' for s in k['sequences']]
    assert all(1<=d<=120 for d in durations)
    checks.append({'id':'CANS-NOMINAL-60HZ-DURATION','status':'PASS','sequences':len(durations),
                   'min_ticks':min(durations),'max_ticks':max(durations),
                   'execution_evidence':'docs/p01/logic/parity-fixtures.json animation cases at0x43ae90'})
    display=json.loads((OUTPUT/'display_units.json').read_text())
    display_fixtures=json.loads((OUTPUT/'display_unit_fixtures.json').read_text())
    assert display['fixture_count']==len(display_fixtures)==1086
    assert all(case['status']=='PASS' for case in display_fixtures)
    assert len(display['course_menu_lengths'])==5 and sum(len(c['levels']) for c in display['course_menu_lengths'])==25
    checks.append({'id':'DISPLAY-UNITS-NATIVE','status':'PASS','fixtures':1086,'course_level_values':25,
                   'scope':'Exact HUD and menu display arithmetic; physical meters and true branch-dependent race length are not asserted'})
    integrity=verify_source()
    checks.append({'id':'SOURCE-INTEGRITY','status':'PASS',**integrity})
    result={'status':'PASS_FOR_LISTED_EVIDENCE_CHECKS','checks':checks,
            'does_not_certify':'Full reverse completeness, all rendering semantics, or production quality',
            'open_gates':['Course physical units and full branch behavior','Full-program reachability beyond known PC getters and palette/render behavior',
                          'Animation attachment/anchors and hit windows','Media event branches and SoundFont playback','Cloud loader dimensions']}
    save_json(OUTPUT/'validation.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
