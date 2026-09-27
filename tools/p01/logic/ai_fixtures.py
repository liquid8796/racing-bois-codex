"""Exact native AI attack-eligibility routine; full boundary/probability domain.

Mode3's real PRNG accessor is used with its captured-value global as input.
There are no code hooks or Windows imports, and this is not a network test.
"""
import json
from emulate_fixtures import OriginalCPU, OBJECT, RIDER, STATS, TARGET, SEGMENT, TLS
from native_project import OUT, EXPECTED_SHA256

vm=OriginalCPU();results=[]
thresholds=[vm.read(0x465a10+i*4) for i in range(5)]
def evaluate(case):
    vm.reset_objects()
    level=case.get('level',0);dt=case.get('dt',1);random=case.get('random',0)
    reach=case.get('reach',5);gap=case.get('gap',0);side=case.get('side',0);av=case.get('attacker_velocity',0);tv=case.get('target_velocity',0)
    until_a=case.get('attacker_hit_until',0);until_t=case.get('target_hit_until',0)
    police=case.get('police',False);attack=case.get('attack',1);target_id=case.get('target_id',4);relation=case.get('relation',101);baseline=case.get('baseline',100)
    vm.write(RIDER+0x1d8,STATS);vm.write(TARGET+0x2fc,SEGMENT);vm.write(SEGMENT+0x1d8,TLS)
    vm.write(STATS+0x1d4,reach);vm.write(RIDER+0x1d4,attack);vm.byte(TLS+0x165,target_id)
    vm.write(RIDER+0x1d0,until_a);vm.write(SEGMENT+0x1d0,until_t)
    vm.write(OBJECT+0x18,dt);vm.write(OBJECT+0xec,av);vm.write(SEGMENT+0xec,tv)
    vm.write(OBJECT+0x1c,gap);vm.write(OBJECT+0x28,side)
    vm.write(0x4b7ecc,100);vm.byte(0x4b8a12,level);vm.write(0x4753b0,3);vm.write(0x49bce8,random)
    if police:
        vm.write(0x4642dc,OBJECT)
        vm.write(STATS+target_id*12+4,relation);vm.write(STATS+target_id*12+0x7c,baseline)
    expected=int(until_a<100 and until_t<100 and abs(((av-tv)>>4)+gap)<reach*16 and abs(side)<reach*8192 and (random&255)<thresholds[level]*dt and (not police or (attack==1 and target_id<10 and relation>baseline)))
    actual=vm.run(0x4092e0,OBJECT,TARGET)&255
    assert actual==expected,(case,expected,actual)
    results.append({'test_id':'AI-ATTACK-%04d'%len(results),'input':case,'clock':100,'expected':expected,'actual':actual,'instructions':vm.steps})

for level in range(5):
    for dt in [1,2,3]:
        for value in range(256):evaluate({'level':level,'dt':dt,'random':value})
for until_a in [0,99,100,101]:
    for until_t in [0,99,100,101]:evaluate({'attacker_hit_until':until_a,'target_hit_until':until_t})
for gap in [-81,-80,-79,0,79,80,81]:
    for side in [-40961,-40960,-40959,0,40959,40960,40961]:evaluate({'gap':gap,'side':side})
for av in [-161,-160,-159,-1,0,1,159,160,161]:
    for gap in [-80,-79,79,80]:evaluate({'attacker_velocity':av,'target_velocity':0,'gap':gap})
for attack in [0,1,2,3]:
    for target_id in [0,4,9,10,15]:
        for relation in [99,100,101]:evaluate({'police':True,'attack':attack,'target_id':target_id,'relation':relation})
result={'source_sha256':EXPECTED_SHA256,'source_va':'0x4092e0','kind':'original-instruction AI component execution','full_ai_parity':False,'windows_imports':0,'behavior_replacement_hooks':0,'instruction_observer':True,'random_mode':'Original mode3 accessor global0x49bce8 is fixture input; not a multiplayer test','aggression_thresholds_by_level':thresholds,'cases':results,'case_count':len(results),'passed':len(results)}
(OUT/'ai-decision-fixtures.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))
