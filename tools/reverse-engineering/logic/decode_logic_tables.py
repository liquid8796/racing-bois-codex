import json, pathlib, struct,sys,collections
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent/'vendor'));import pefile
ROOT=pathlib.Path(r'C:\Users\Liquid\Downloads\Unity\racing_bois_mod');OUT=pathlib.Path(r'D:\Project\Unity\racing-bois\docs\reverse-engineering\logic')
pe=pefile.PE(str(ROOT/'RacingBois.exe'));base=pe.OPTIONAL_HEADER.ImageBase
def read(va,n):return pe.get_data(va-base,n)
def u32(va):return struct.unpack('<I',read(va,4))[0]
def checksum(b):
 total=weighted=alternating=0
 for remaining,value in zip(range(len(b),0,-1),b):
  total+=value;weighted+=remaining*value;alternating+=value if remaining&1 else -value
 return (((alternating<<16)|(total&0xffff))^weighted)&0xffffffff
texts={x['id']:x['text'] for x in json.loads((OUT/'localization_strings.json').read_text(encoding='utf8')) if x['file']=='ENU.DLL'}
bikes=[]
for i in range(15):
 target=0x420ab1 if i==0 else u32(0x420b0c+(i-1)*4)
 assert read(target,1)==b'\xb8'
 sid=u32(target+1)
 bikes.append({'internal_index':i,'resource_SPEC_id':i+1,'string_id':sid,'name':texts[sid],'price':u32(0x468fc0+i*4),'trade_in':u32(0x468fc0+i*4)//2,'repair':u32(0x468fc0+i*4)//10,'name_mapping_va':hex(target),'price_va':hex(0x468fc0+i*4)})
profiles=[]
for i in range(9):
 if i==0:internal=0
 else:
  target=u32(0x415fec+(i-1)*4);assert read(target,1)==b'\xb0';internal=read(target+1,1)[0]
 profiles.append({'selection_index':i,'internal_character_index':internal,'starting_cash':struct.unpack('<H',read(0x469000+i*2,2))[0],'bike_indices_by_level':list(read(0x4641c8+internal*5,5))})
saves=[]
for f in sorted(list((ROOT/'SAVES').glob('*'))+[f for f in ROOT.iterdir() if f.is_file() and f.stat().st_size==160]):
 b=f.read_bytes();magic=struct.unpack_from('<I',b,4)[0];actual=struct.unpack_from('<I',b)[0];calc=checksum(b[4:]);valid=magic==0xcafedead and actual==calc
 saves.append({'file':str(f.relative_to(ROOT)),'valid':valid,'magic':hex(magic),'checksum_stored':hex(actual),'checksum_computed':hex(calc),'state':{'player_slot':b[8],'character_selection':b[9],'level_index':b[10],'qualification_mask':b[11],'bike_index':b[12],'bike':bikes[b[12]]['name'] if b[12]<15 else None,'course_selection':b[13],'finish_position_index':b[14],'unknown_0f':b[15],'cash':struct.unpack_from('<I',b,16)[0],'name':b[20:40].split(b'\0')[0].decode('cp1252',errors='replace')},'relationship_or_progress_records_unknown_semantics':[list(struct.unpack_from('<3i',b,40+i*12)) for i in range(10)]})
(OUT/'saves_decoded.json').write_text(json.dumps(saves,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'economy_tables.json').write_text(json.dumps({'bikes':bikes,'profile_defaults':profiles,'reward_base_by_position':[u32(0x46ab48+i*0x4c) for i in range(14)],'evidence':{'shop':'0x4215e0..0x42169a','reward':'0x42134c..0x42137a','fine':'0x421528..0x421537','repair':'0x4214f9..0x42150e','profiles':'0x41f630..0x41f69e','name_map':'0x420aa0..0x420b44','character_map':'0x415fc0..0x41600c'}},ensure_ascii=False,indent=2),encoding='utf8')
print('save validation',collections.Counter(x['valid'] for x in saves));print('\n'.join(f"{x['internal_index']:2} {x['name']:14} ${x['price']}" for x in bikes));print(json.dumps(profiles));print('rewards',[u32(0x46ab48+i*0x4c) for i in range(14)])
