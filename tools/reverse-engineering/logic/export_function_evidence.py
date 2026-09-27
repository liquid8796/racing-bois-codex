import json,pathlib,sys,hashlib,collections
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent/'vendor'))
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
ROOT=pathlib.Path(r'C:\Users\Liquid\Downloads\Unity\racing_bois_mod');OUT=pathlib.Path(r'D:\Project\Unity\racing-bois\docs\reverse-engineering\logic')
p=pefile.PE(str(ROOT/'RacingBois.exe'));base=p.OPTIONAL_HEADER.ImageBase
ranges=[
('apply_rider_damage',0x4050c0,0x4051d8,'combat'),('apply_bike_damage',0x4051e0,0x4052b2,'combat'),('apply_damage_and_fall',0x4052c0,0x40544a,'combat'),
('load_15_bike_specs',0x405e30,0x405e7e,'bikes'),('apply_bike_spec',0x405ea0,0x406073,'physics'),('rider_update_candidate',0x4060b0,0x406266,'physics'),
('ai_or_remote_rider_update_candidate',0x407d40,0x407f1b,'ai'),('ai_attack_choice_candidate',0x409460,0x409509,'ai'),('attack_state_test',0x409510,0x40955d,'combat'),('choose_attack_animation',0x4095d0,0x4096eb,'combat'),('attack_hit_and_weapon_transfer',0x4096f0,0x409acc,'combat'),('compute_weapon_damage',0x409ad0,0x409bbe,'combat'),('attack_range_test',0x409c10,0x409c92,'combat'),
('character_selection_map',0x415fc0,0x415feb,'campaign'),('profile_defaults',0x41f630,0x41f6a5,'campaign'),('campaign_level_progression',0x41f6d0,0x41f740,'campaign'),('bike_name_map',0x420aa0,0x420b0b,'bikes'),('race_reward',0x421290,0x4213b9,'economy'),('fine_and_repair',0x4214e0,0x4215d9,'economy'),('bike_purchase',0x4215e0,0x4216b2,'economy'),
('save_checksum',0x42efc0,0x42effc,'save'),('save_write',0x42f000,0x42f104,'save'),('save_read',0x42f110,0x42f268,'save'),('template_mip_loader',0x432f90,0x433084,'assets'),('pack_24byte_net_state',0x43c7e0,0x43c958,'network'),('mode_dependent_random',0x441750,0x441765,'ai'),('network_datagram_send',0x441b30,0x441c90,'network'),('network_sockaddr_ipv4',0x441c90,0x441ccb,'network'),('network_sockaddr_ipx',0x441cd0,0x441cfd,'network'),('network_stream_send',0x4428a0,0x4428fa,'network'),('biker_dat_setup',0x443610,0x443693,'assets'),('biker_dat_loader',0x4436a0,0x44379f,'assets'),('qualification_mask_and_movie',0x449150,0x4491ff,'campaign'),('crt_random',0x455eb0,0x455edf,'ai'),('horizon_raw_bob_loader',0x44c440,0x44c5c8,'assets'),('meter_raw_bob_loader',0x44c5d0,0x44c5ed,'assets'),('generic_raw_bob_loader',0x44c5f0,0x44c701,'assets'),('dash_raw_bob_loader',0x44c710,0x44c72e,'assets'),('horizon_surface_setup',0x448a90,0x448b10,'assets')]
cs=Cs(CS_ARCH_X86,CS_MODE_32);cs.skipdata=True
index=[];d=OUT/'functions';d.mkdir(exist_ok=True)
for name,start,end,category in ranges:
 raw=p.get_data(start-base,end-start);fileoffset=p.get_offset_from_rva(start-base)
 rows=[f'{i.address:08x}\t{i.bytes.hex()}\t{i.mnemonic}\t{i.op_str}' for i in cs.disasm(raw,start)]
 (d/(name+'.tsv')).write_text('\n'.join(rows),encoding='utf8')
 index.append({'analyst_label':name,'category':category,'va_start':hex(start),'va_end_exclusive':hex(end),'file_offset_start':hex(fileoffset),'length':len(raw),'sha256_code_slice':hashlib.sha256(raw).hexdigest(),'instruction_rows':len(rows),'original_symbol':False,'slice_not_guaranteed_entire_function':name.endswith('candidate') or name in ['network_datagram_send','rider_update_candidate','bike_purchase']})
(OUT/'function_index.json').write_text(json.dumps(index,indent=2),encoding='utf8')
print('Evidence slices:',len(index),'; categories:',dict(collections.Counter(x['category'] for x in index)))
