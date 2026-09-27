"""Execute original RPTH instructions and classify all remaining legacy RRFDs.

Unicorn execution is component evidence: no Windows/native game is launched,
no source file is changed, and no emulated external service hook is required.
"""
from common import *
from collections import Counter,defaultdict
import re

sys.path.insert(0,str(REPO/'tools/p01/logic'))
sys.path.insert(0,str(REPO/'tools/p01/logic/vendor'))
sys.path.insert(0,str(REPO/'tools/reverse-engineering/logic/vendor'))
from emulate_fixtures import OriginalCPU

WRAPPER=0x600000
PAYLOAD=0x601000
OUT_A=0x60f000
OUT_B=0x60f004
HARNESS=0x460000
TRACE=0x606000
COEFFICIENTS=0x608000

def native_trace(vm,count,forward):
    """Loop in emulated x86 instead of restarting Unicorn for every sample.

The harness occupies a non-called scratch part of the mapped PE image. Only
the harness is synthesized; the three tested function byte ranges are intact.
"""
    code=bytearray()
    def emit(data):code.extend(data)
    def immediate(op,value):emit(bytes([op])+struct.pack('<I',value&0xffffffff))
    def call(address):
        here=HARNESS+len(code)
        emit(b'\xe8'+struct.pack('<i',address-here-5))
    emit(b'\x53\x56\x57') # preserve ebx esi edi
    immediate(0xb9,WRAPPER);immediate(0xba,PAYLOAD)
    emit(b'\x6a'+bytes([1 if forward else 0]));call(0x451970)
    immediate(0xbe,TRACE);immediate(0xbb,COEFFICIENTS)
    immediate(0xa1,WRAPPER+4);emit(b'\x89\x06\x83\xc6\x04')
    immediate(0xbf,count)
    loop=len(code)
    if forward:
        immediate(0xb9,WRAPPER);immediate(0xba,OUT_A)
        emit(b'\x68'+struct.pack('<I',OUT_B));call(0x451a40)
        immediate(0xa1,OUT_A);emit(b'\x89\x03')
        immediate(0xa1,OUT_B);emit(b'\x89\x43\x04\x83\xc3\x08')
    immediate(0xb9,WRAPPER);immediate(0xba,256 if forward else -256);call(0x4519f0)
    immediate(0xa1,WRAPPER+4);emit(b'\x89\x06\x83\xc6\x04\x4f')
    branch=len(code);emit(b'\x0f\x85'+struct.pack('<i',loop-branch-6))
    emit(b'\x5f\x5e\x5b\xc3')
    vm.cpu.mem_write(HARNESS,bytes(code))
    vm.cpu.ctl_remove_cache(HARNESS,HARNESS+512)
    vm.run(HARNESS,limit=400000)
    values=list(struct.unpack('<'+'i'*(count+1),vm.cpu.mem_read(TRACE,4*(count+1))))
    pairs=list(struct.unpack('<'+'i'*(2*count),vm.cpu.mem_read(COEFFICIENTS,8*count))) if forward else []
    assert not vm.calls
    return values,pairs,vm.steps,digest(bytes(code))

def rpth_execution():
    vm=OriginalCPU()
    results=[]
    checks=0
    for path in sorted((OUTPUT/'courses').glob('*.json')):
        course=json.loads(path.read_text())
        segments=course['SGS']['segments']
        nodes=course['NOD']['nodes']
        for chunk in course['SGS']['chunks']:
            if chunk['tag']!='RPTH':continue
            raw=bytes.fromhex(chunk['raw_hex'])
            samples=chunk['samples_raw_s8_pairs']
            count=chunk['count_field']
            start,end=struct.unpack_from('<hh',raw,12)
            vm.cpu.mem_write(PAYLOAD,raw)
            forward,coefficients,forward_steps,forward_harness=native_trace(vm,count,True)
            assert forward[0]==start and vm.read(WRAPPER+8)==count*256
            assert coefficients==[value for pair in samples for value in pair]
            assert all(forward[i+1]==forward[i]+samples[i][1] for i in range(count))
            reverse_walk,_,reverse_steps,reverse_harness=native_trace(vm,count,False)
            reverse=list(reversed(reverse_walk))
            assert reverse[-1]==end and vm.read(WRAPPER+8)==0
            assert all(reverse[i]==reverse[i+1]-samples[i][1] for i in range(count))
            checks+=4+4*count
            bias=end-forward[-1]
            assert all(reverse[i]-forward[i]==bias for i in range(count+1))
            checks+=count+1
            associated=[s['index'] for s in segments if s['raw_u32'][1]==chunk['offset']]
            used=[{'index':n['index'],'type':n['type'],'segment':n['segment_index'],'length':n['node_length_raw']}
                  for n in nodes if n['type']==0 and n['segment_index'] in associated]
            assert all(n['length']==count for n in used)
            results.append({'course':path.stem,'chunk_offset':chunk['offset'],'sample_count':count,
                            'source_payload_sha256':digest(raw),'nodes':used,
                            'forward_seed':start,'reverse_seed':end,'forward_component_end':forward[-1],
                            'reverse_component_start':reverse[0],'directional_bias_every_sample':bias,
                            'all_samples_native_equal_reference':True,
                            'executed_instruction_count':forward_steps+reverse_steps,
                            'scratch_harness_sha256':[forward_harness,reverse_harness],
                            'forward_trace_sha256':digest(struct.pack('<'+'i'*len(forward),*forward)),
                            'reverse_trace_sha256':digest(struct.pack('<'+'i'*len(reverse),*reverse)),
                            'external_hooks':[],
                            'scope':'RPTH component integrates all samples; caller node-transition ordering has separate tests'})
    # Controlled in-memory counterfactual proves seed fields are independent.
    raw=bytearray(bytes.fromhex(next(c for c in json.loads((OUTPUT/'courses/MEDLY.json').read_text())['SGS']['chunks'] if c['tag']=='RPTH')['raw_hex']))
    original_end=struct.unpack_from('<h',raw,14)[0]
    struct.pack_into('<h',raw,14,original_end+777)
    vm.cpu.mem_write(PAYLOAD,bytes(raw))
    vm.run(0x451970,WRAPPER,PAYLOAD,(1,));forward_seed=vm.read(WRAPPER+4,True)
    vm.run(0x451970,WRAPPER,PAYLOAD,(0,));reverse_seed=vm.read(WRAPPER+4,True)
    assert forward_seed==0 and reverse_seed==original_end+777
    skipped=[]
    for position,delta in [(0,0),(0,127),(127,1),(128,127),(255,1),(0,256),(0,512),(0,768),(1024,-512)]:
        vm.write(WRAPPER,PAYLOAD);vm.write(WRAPPER+4,0);vm.write(WRAPPER+8,position)
        vm.run(0x4519f0,WRAPPER,delta)
        new=position+delta
        expected=0
        if position>>8!=new>>8:
            sample_index=position>>8 if delta>0 else new>>8
            value=struct.unpack_from('<b',raw,17+2*sample_index)[0]
            expected=value if delta>0 else -value
        actual=vm.read(WRAPPER+4,True)
        assert actual==expected
        skipped.append({'old_position_q8':position,'delta_q8':delta,'new_position_q8':new,
                        'native_accumulator_delta':actual,'status':'PASS'})
    # Caller-level fixture: two native node/segment records, with other optional
    # segment resources null. Both native routines execute without hooks.
    sgs_a,sgs_b,node_a,node_b,terminal,path_b=0x602000,0x602080,0x603000,0x603080,0x603100,0x601200
    vm.cpu.mem_write(WRAPPER,b'\0'*0x500)
    vm.cpu.mem_write(sgs_a,b'\0'*0x200)
    vm.cpu.mem_write(node_a,b'\0'*0x200)
    vm.cpu.mem_write(PAYLOAD,b'HTPR'+struct.pack('<IIhh',36,10,0,99)+bytes([0,1])*10)
    vm.cpu.mem_write(path_b,b'HTPR'+struct.pack('<IIhh',36,10,123,133)+bytes([0,1])*10)
    for address,sgs,next_node,previous in [(node_a,sgs_a,node_b,terminal),(node_b,sgs_b,terminal,node_a)]:
        for offset,value in [(0,0),(8,next_node),(12,previous),(16,sgs),(20,10)]:
            vm.write(address+offset,value)
    vm.write(terminal,3)
    vm.write(sgs_a+4,PAYLOAD);vm.write(sgs_b+4,path_b)
    vm.run(0x452cb0,WRAPPER,node_a,(1,))
    vm.write(WRAPPER+8,9*256);vm.write(WRAPPER+0x34,9*256);vm.write(WRAPPER+0x30,9)
    forward_result=vm.run(0x452e10,WRAPPER,256)
    forward_boundary={'result':forward_result,'node':vm.read(WRAPPER+4),
                      'position_q8':vm.read(WRAPPER+8),'accumulator':vm.read(WRAPPER+0x30,True)}
    assert forward_boundary=={'result':1,'node':node_b,'position_q8':0,'accumulator':123}
    vm.run(0x452cb0,WRAPPER,node_b,(1,))
    vm.write(WRAPPER+8,128);vm.write(WRAPPER+0x34,128)
    backward_result=vm.run(0x452e10,WRAPPER,-256)
    backward_boundary={'result':backward_result,'node':vm.read(WRAPPER+4),
                       'position_q8':vm.read(WRAPPER+8),'accumulator':vm.read(WRAPPER+0x30,True)}
    assert backward_boundary=={'result':1,'node':node_a,'position_q8':2432,'accumulator':98}
    assert not vm.calls
    output={'status':'NATIVE_COMPONENT_SEMANTICS_CLOSED','source_exe_sha256':digest((SOURCE/'RacingBois.exe').read_bytes()),
            'source_functions':['0x451970','0x4519f0','0x451a40'],
            'paths':results,'native_value_assertions':checks+2+len(skipped),
            'seed_counterfactual':{'course':'MEDLY','only_reverse_seed_delta':777,
                                   'forward_initialization_unchanged':True,'reverse_initialization_shifted_by':777,
                                   'source_file_modified':False},
            'large_step_checks':skipped,
            'node_boundary_fixture':{'source_functions':['0x452cb0','0x452e10'],
                                     'synthetic_inputs':'Two real-layout type0 nodes; source-independent10samples; A seeds0/99, B seeds123/133; coefficient pairs(0,1). Optional other resources null.',
                                     'forward_A_to_B':forward_boundary,'backward_B_to_A':backward_boundary,
                                     'external_hooks':[],
                                     'conclusion':'Caller changes node before RPTH update; initialization replaces accumulator with next forward or previous reverse seed. It does not validate/correct endpoint sums.'},
            'interpretation':'Forward/reverse seeds are independent native initialization fields; equality with integrated samples is not a loader invariant. 13 source paths have a constant direction-dependent accumulator offset.',
            'not_proven':'Why source authors chose inconsistent seeds, vanilla parity, or perceptual effect of all 13 cases in a full game run.'}
    save_json(OUTPUT/'rpth_native_execution.json',output)
    return output

def legacy_classification():
    animations=json.loads((OUTPUT/'animation_catalog.json').read_text())
    by_id={a['identity']:a for a in animations}
    cans=json.loads((OUTPUT/'cans_decoded.json').read_text())
    canned={}
    for c in cans:
        name=c['identity']
        sibling=name.rsplit('/',1)[0]+'/0' if name.startswith('family') else name.replace('/CANS/','/ANIM/')
        canned[sibling]=c
    rows=[]
    for animation in animations:
        name=animation['identity']
        refs=defaultdict(list)
        control=canned.get(name)
        if control:
            actions=next((c['actions'] for c in control['chunks'] if c['tag']=='ACTN'),[])
            for chunk in control['chunks']:
                if chunk['tag']!='CANS':continue
                for sequence in chunk['sequences']:
                    for frame in sequence['frames']:
                        refs[frame['frame_reference_1based']-1].append(sequence['id'])
        for frame in animation['frames']:
            if frame['status']!='LEGACY_12_BYTE_LOD_RECORD':continue
            record={'animation':name,'frame':frame['index'],'descriptor_width':frame['width_low16'],
                    'descriptor_height':frame['height_low16'],'pixel_marker_raw':frame['pixel_marker'],
                    'cans_sequences_referring_to_frame':sorted(set(refs[frame['index']]))}
            if name.startswith('DATA/GLOBAL.RSC'):
                rid=int(name.rsplit('/',1)[1])
                mapping={1:'LOBOB.DAT',2:'LOCOP.DAT',3:'LOSHADOW.DAT',4:'LOSHADOC.DAT'}
                dat=dat_frames((SOURCE/'DATA/BIKERS'/mapping[rid]).read_bytes())[frame['index']]
                record.update(classification='GLOBAL_DAT_STORAGE',dat_file=mapping[rid],dat_frame=frame['index'],
                              dat_nonempty=bool(dat['pixel_bytes']),
                              caveat='Separate native DAT bank storage; not an asserted in-place RRFD pixel alias')
            elif control:
                assert not refs[frame['index']], (name,frame['index'])
                record.update(classification='UNREFERENCED_BY_COMPLETE_CANS_SEQUENCE_TABLE',
                              source_cans=control['identity'],
                              proof='Every CANS sequence frame reference was enumerated; no sequence references this slot.',
                              caveat='Static CANS reachability does not prove absence of every possible direct manual frame selection.')
            else:
                assert re.search(r'/root/[47]/\d+/1$',name),name
                primary=name.rsplit('/',1)[0]+'/0'
                assert primary in by_id
                assert all(f['status']!='LEGACY_12_BYTE_LOD_RECORD' for f in by_id[primary]['frames'])
                record.update(classification='SECONDARY_ROOT4_VARIANT_UNSELECTED_BY_KNOWN_PC_CALLS' if '/root/4/' in name else 'ROOT7_SECONDARY_VARIANT_NO_STATIC_SELECTION_FOUND',
                              complete_primary_variant=primary,
                              proof='0x44b71d pushes0;0x44b724 setsEDX4;0x44b729 calls selector0x44acd0.' if '/root/4/' in name else 'No identified direct family-getter call selects root7; source primary sibling has complete pixel data.',
                              caveat='No dynamic all-course coverage or proof against computed/indirect calls; original authoring purpose not known.')
            rows.append(record)
    assert len(rows)==1179
    counts=dict(Counter(r['classification'] for r in rows))
    assert counts=={'GLOBAL_DAT_STORAGE':742,'UNREFERENCED_BY_COMPLETE_CANS_SEQUENCE_TABLE':176,
                    'SECONDARY_ROOT4_VARIANT_UNSELECTED_BY_KNOWN_PC_CALLS':255,
                    'ROOT7_SECONDARY_VARIANT_NO_STATIC_SELECTION_FOUND':6}
    lines=(REPO/'docs/reverse-engineering/logic/RacingBois.disassembly.tsv').read_text().splitlines()
    callsites=[]
    targets=['0x44ac00','0x44acd0','0x44ada0']
    for i,line in enumerate(lines):
        fields=line.split('\t')
        if len(fields)>=4 and fields[2]=='call' and fields[3] in targets:
            callsites.append({'callsite_va':'0x'+fields[0],'target':fields[3],
                              'preceding_instruction_window':lines[max(0,i-12):i+1]})
    exe=(SOURCE/'RacingBois.exe').read_bytes()
    absrefs={target:exe.count(int(target,16).to_bytes(4,'little')) for target in targets}
    output={'status':'ALL_LEGACY_RECORDS_CLASSIFIED_WITH_SCOPED_EVIDENCE','counts':counts,
            'cans_referenced_non_dat_missing_pixels':sum(bool(r['cans_sequences_referring_to_frame']) for r in rows if r['classification']!='GLOBAL_DAT_STORAGE'),
            'rows':rows,'identified_direct_family_getter_calls':callsites,'absolute_function_pointer_byte_occurrences':absrefs,
            'not_proven':'Global full-program non-reachability of legacy unused slots; keep originals cataloged and do not delete source.'}
    save_json(OUTPUT/'legacy_rrfd_classification.json',output)
    return output

def main():
    native=rpth_execution()
    legacy=legacy_classification()
    print(json.dumps({'native_rpth_paths':len(native['paths']),
                      'native_value_assertions':native['native_value_assertions'],
                      'directional_seed_differences':sum(p['directional_bias_every_sample']!=0 for p in native['paths']),
                      'remaining_legacy_classification':legacy['counts'],
                      'cans_referenced_non_dat_missing_pixels':legacy['cans_referenced_non_dat_missing_pixels']},indent=2))

if __name__=='__main__':
    main()
