"""Recover display-unit contracts from native instructions and source tables.

These are HUD/display conversions, not a claim that the engine uses meters.
Native math executes under Unicorn; menu fixture stops before localization I/O.
"""
from common import *
from collections import Counter

sys.path[:0]=[str(REPO/'tools/p01/logic'),str(REPO/'tools/p01/logic/vendor'),str(REPO/'tools/reverse-engineering/logic/vendor')]
from emulate_fixtures import OriginalCPU,OBJECT,SENTINEL
from unicorn.x86_const import UC_X86_REG_EBX,UC_X86_REG_EIP,UC_X86_REG_EAX

def i32(value):return signed(value&0xffffffff)
def trunc(value,divisor):return (abs(value)//abs(divisor))*(-1 if (value<0)!=(divisor<0) else 1)

def digital_speed(raw,metric=False):
    raw=i32(raw)
    if metric:
        value=trunc((i32(raw&0xffffff87)>>3)+(i32(raw&0xfffffe1f)>>5)+(i32(raw&0xfffff0ff)>>8),10)
    else:
        value=(raw>>12)+(raw>>7)+(raw>>9)
    return max(0,value)

def analog_phase(raw):
    value=i32(i32(i32(raw&0xffffff80)<<4)+i32(i32(raw&0xfffffe00)*4)+(i32(raw&0xfffff001)>>1))
    value=trunc(value,200)-1024
    return value+4096 if value<0 else value

def distance_tenths(raw_position,metric=False):
    # Store AL matches the original uint8 output, including wrap at invalid or
    # out-of-range positions. Native speed clamps; this counter does not.
    value=trunc((i32(raw_position)>>5)-400,165) if metric else trunc((i32(raw_position)>>8)-50,33)
    return value&255

def main():
    vm=OriginalCPU()
    vm.write(0x4642d8,OBJECT)
    cases=[]
    values=sorted(set([-32768,-4096,-1024,-1,0,1,7,8,31,32,63,64,127,128,255,256,511,512,
                       999,1000,3999,4000,4095,4096,4097,7999,8000,9999,10000,10001,12000,16000,20000,22000,32767]
                      +[boundary+d for boundary in range(0,22001,512) for d in (-1,0,1)]))
    for metric in (False,True):
        vm.byte(0x497248,ord('0' if metric else '1'))
        for mode in (0,1,2):
            vm.byte(0x467a98,mode)
            for raw in values:
                vm.write(OBJECT+0xec,raw);vm.write(OBJECT+0x108,raw)
                vm.run(0x4468e0)
                expected=analog_phase(raw) if mode==0 else digital_speed(raw,metric)
                actual=vm.read(0x49e10c,True)
                assert actual==expected,(raw,metric,mode,expected,actual)
                assert not vm.calls
                cases.append({'test':'HUD_SPEED','raw_velocity':raw,'metric':metric,'hud_mode':mode,
                              'expected':expected,'actual':actual,'status':'PASS','source_va':'0x4468e0'})
    positions=sorted(set([-100000,-1,0,1,49*256,50*256-1,50*256,50*256+1]
                         +[(50+33*t)*256+d for t in (0,1,2,10,53,185,255,256) for d in (-1,0,1)]
                         +[int((400+165*t)*32)+d for t in (0,1,2,10,53,185,255,256) for d in (-1,0,1)]))
    for metric in (False,True):
        vm.byte(0x497248,ord('0' if metric else '1'))
        for position in positions:
            vm.write(OBJECT+0x44,position)
            vm.run(0x446a40)
            actual=vm.cpu.mem_read(0x49e115,1)[0]
            expected=distance_tenths(position,metric)
            assert actual==expected,(position,metric,actual,expected)
            assert not vm.calls
            cases.append({'test':'HUD_DISTANCE','raw_position_snapshot':position,'metric':metric,
                          'expected_tenths_byte':expected,'actual_tenths_byte':actual,'status':'PASS','source_va':'0x446a40'})
    pe=vm.pe
    rows=struct.unpack('<25I',pe.get_data(0x68f58,100))
    file_pointers=struct.unpack('<5I',pe.get_data(0x6df58,20))
    localization=json.loads((REPO/'docs/reverse-engineering/logic/localization_strings.json').read_text(encoding='utf-8'))
    english={r['id']:r['text'] for r in localization if r['file']=='ENU.DLL'}
    metric_factor=struct.unpack('<d',pe.get_data(0x62008,8))[0]
    assert metric_factor==1.609
    courses=[]
    for index in range(5):
        entry_va=0x4691a0+index*56
        menu_entry=struct.unpack('<14I',pe.get_data(entry_va-0x400000,56))
        assert menu_entry[1]==index+1 and menu_entry[2]==index+16 and menu_entry[11]==0x4213c0
        name=pe.get_string_at_rva(file_pointers[index]-0x400000).decode('ascii').upper()
        course={'selection_id_1based':index+1,'loader_index_0based':index,'menu_entry_va':hex(entry_va),
                'title_string_id':index+16,'display_name':english[index+16],
                'course_source':f'DATA/COURSES/{name}.CRS','length_table_va':hex(0x468f58+index*20),
                'levels':[]}
        for level in range(5):
            for metric in (False,True):
                vm.byte(0x497248,ord('0' if metric else '1'))
                vm.byte(0x4b8a12,level)
                vm.write(OBJECT+8,index+16)
                vm.write(OBJECT+0x24,0x4000)
                capture={}
                def stop_before_localization(machine):
                    capture['tenths']=machine.cpu.reg_read(UC_X86_REG_EBX)
                    capture['unit_string_id']=machine.cpu.reg_read(UC_X86_REG_EAX)&65535
                    machine.cpu.reg_write(UC_X86_REG_EIP,SENTINEL)
                vm.hooks={0x420869:stop_before_localization}
                vm.run(0x420810)
                expected=int(rows[index*5+level]*metric_factor) if metric else rows[index*5+level]
                assert capture=={'tenths':expected,'unit_string_id':28 if metric else 27},(index,level,metric,capture,expected)
                cases.append({'test':'COURSE_MENU_LENGTH','course_index':index,'level_index':level,'metric':metric,
                              'expected_tenths':expected,**capture,'status':'PASS',
                              'source_va':'0x420810','observation_stop_before_localization':'0x420869'})
            course['levels'].append({'level_display':level+1,'imperial_tenths':rows[index*5+level],
                                     'miles_display':f'{rows[index*5+level]//10}.{rows[index*5+level]%10}',
                                     'metric_tenths':int(rows[index*5+level]*metric_factor),
                                     'kilometers_display':f'{int(rows[index*5+level]*metric_factor)//10}.{int(rows[index*5+level]*metric_factor)%10}'})
        courses.append(course)
    vm.hooks={}
    samples=[{'raw_velocity':v,'mph':digital_speed(v),'kph':digital_speed(v,True)} for v in [0,1000,4000,8000,10000,12000,16000,20000]]
    summary={'status':'NATIVE_DISPLAY_MATH_AND_TABLE_MAPPING_PASS','source_exe_sha256':digest((SOURCE/'RacingBois.exe').read_bytes()),
             'fixture_count':len(cases),'fixture_groups':dict(Counter(c['test'] for c in cases)),
             'source_functions':{'speed':'0x4468e0','distance':'0x446a40','metric_setting':'0x42f490',
                                 'course_display':'0x420810','course_selection':'0x4160c0','filename_loader':'0x441940'},
             'digital_speed_examples':samples,'course_menu_metric_factor':metric_factor,'course_menu_lengths':courses,
             'display_calibration':{'raw_longitudinal_q8_per_sample':256,'start_offset_samples':50,
                                    'imperial_samples_per_displayed_tenth_mile':33,
                                    'imperial_raw_position_per_displayed_mile':84480,
                                    'metric_raw_position_per_displayed_tenth_km':5280,
                                    'proof_scope':'HUD quantization only; physical Unity meters, exact route distance and integrated speed consistency are not claimed'},
             'behavioral_notes':['Speed negatives clamp to0 in digital modes.',
                                 'HUD distance stores low8bits without clamp; out-of-range/negative inputs can wrap.',
                                 'HUD display arithmetic approximates metric/imperial ratio1.6, while course menu uses1.609 and truncates tenths.',
                                 'Menu lengths are declared display metadata, not measurements of every fork or level finish predicate.'],
             'platform_reference':'https://learn.microsoft.com/en-us/windows/win32/intl/locale-imeasure'}
    save_json(OUTPUT/'display_units.json',summary)
    save_json(OUTPUT/'display_unit_fixtures.json',cases)
    # Separate evidence collection avoids overwriting existing asset evidence.
    lines=(REPO/'docs/reverse-engineering/logic/RacingBois.disassembly.tsv').read_text().splitlines()
    ranges=[('speed',0x4468e0,0x4469c8),('distance',0x446a40,0x446a7b),
            ('course_menu_length',0x420810,0x4208c9),('course_selection',0x4160c0,0x416112),
            ('course_ui_callback',0x4213c0,0x421480),('locale_measurement',0x42f340,0x42f49b),
            ('position_snapshot',0x4384e1,0x438535),('hud_distance_format',0x446d90,0x446dd0),
            ('hud_speed_format',0x44706f,0x447112),('dashboard_unit_image',0x416310,0x416358)]
    directory=OUTPUT/'display_evidence';directory.mkdir(exist_ok=True)
    for name,start,end in ranges:
        (directory/(name+'.tsv')).write_text('\n'.join(line for line in lines if start<=int(line.split('\t')[0],16)<end)+'\n',encoding='utf-8')
    print(json.dumps({'fixture_count':len(cases),'groups':summary['fixture_groups'],
                      'speed_examples':samples,'courses':courses},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
