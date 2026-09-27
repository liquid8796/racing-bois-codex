"""Validate captured real-process mutations against recovered integer formulas."""
import collections
import json
from native_project import OUT, EXPECTED_SHA256

def events(name):
    p=json.loads((OUT/('native-probe-'+name+'.json')).read_text())
    assert p['source_sha256']==EXPECTED_SHA256 and p['original_executable_unchanged'] and not p['copy_file_changes']
    assert not [m for m in p['events'] if m.get('type')=='error']
    e=[m.get('payload',{}) for m in p['events']]
    assert not [m for m in e if m.get('kind')=='native_exception']
    return e

hit=events('hit');steal=events('steal');police=events('police')
damage=[]
for v in hit:
    if v.get('kind')!='native_weapon_damage_result':continue
    a=v['before']['attacker'];b=v['before']['target'];after=v['after']['target']
    effective=max((((a['endurance']<<8)//a['maxEndurance'])*a['baseStrength'])>>8,a['baseStrength']//2)
    amount=effective*[256,320,384,64][a['attack']]//256
    secondary=amount//4+1 if a['attack']==3 else 0
    expected={'endurance':max(b['endurance']-4*amount,b['maxEndurance']//2),'health':max(b['health']-64*amount,0),'bikeCondition':max(b['bikeCondition']-secondary,0)}
    actual={k:after[k] for k in expected}
    assert expected==actual,(v['tick'],expected,actual)
    damage.append({'tick':v['tick'],'weapon_id':a['attack'],'native_damage':amount,'secondary':secondary,'expected':expected,'actual':actual,'status':'PASS'})
assert {r['weapon_id'] for r in damage}=={0,1,2,3}
range_hits={v['tick'] for v in hit if v.get('kind')=='native_range_result' and v['accepted']==1}
equality=[]
for v in hit:
    if v.get('kind')!='native_contact_result':continue
    b=v['before']['target'];after=v['after']['target']
    if v['tick']==b['hitUntil'] and v['tick'] in range_hits:
        assert b['health']==after['health']
        equality.append({'tick':v['tick'],'deadline':b['hitUntil'],'target_animation':b['animation'],'range_accepted':True,'health_before':b['health'],'health_after':after['health']})
assert equality,'Missing native strict-equality cooldown observation'
transfers=[]
for v in steal:
    if v.get('kind')!='native_contact_result':continue
    before,after=v['before'],v['after']
    if before['attacker']['weapon']!=after['attacker']['weapon']:
        assert before['attacker']['weapon']==0 and before['target']['weapon']==2
        assert after['attacker']['weapon']==2 and after['target']['weapon']==0
        assert after['attacker']['stealUntil']==v['tick']+300
        transfers.append({'tick':v['tick'],'before':[0,2],'after':[2,0],'steal_until':after['attacker']['stealUntil'],'delta_ticks':300,'status':'PASS'})
assert transfers
roles=collections.defaultdict(set);transitions=[];traffic=[]
for v in police:
    if v.get('kind')=='native_behavior_dispatch':roles[v['role']].add(v['dispatchId'])
    if v.get('kind')=='native_behavior_transition':transitions.append({'tick':v['tick'],'role':v['after']['role'],'character_id':v['after']['characterId'],'slot':v['after']['slot'],'from':v['before']['behavior'],'to':v['after']['behavior']})
    if v.get('kind')=='native_traffic_live_update':
        assert v['objectType']==32 and 0<=v['trafficType']<=10 and v['state'] in [1,3]
        traffic.append(v)
cop=next(v for v in police if v.get('kind')=='native_police_identity')
bust=next(v for v in police if v.get('kind')=='native_outcome_request' and v['request']==4)
assert traffic,'No live traffic callback observations'
result={'status':'PASS','source_sha256':EXPECTED_SHA256,'scope':'controlled native contact mutations, strict cooldown equality, weapon transfer and observed roles','damage_cases':damage,'strict_cooldown_equalities':equality,'weapon_transfers':transfers,'police_identity':cop,'first_bust':bust,'observed_behavior_ids_by_role':{k:sorted(v) for k,v in roles.items()},'behavior_transitions':transitions,'traffic_states_observed':sorted({v['state'] for v in traffic}),'traffic_instance_count':len({v['pointer'] for v in traffic}),'traffic_live_observations':traffic,'rejected_traffic_evidence':'Periodic snapshots in earlier police probes retained recycled constructor pointers; use only native_traffic_live_update records from0x440dd0.','result_transitions':[v for v in police if v.get('kind')=='native_result_transition'],'limitations':['contact fixtures reposition player beside an existing target before hit processing','recipient pools reset to explicit test values once per weapon case','steal fixture initializes target attack using original animation-selection routine','police initial spawn invokes original routine; natural spawn eligibility not verified','unobserved AI handlers and full relationship model remain open','native contact cases are not physics or browser performance tests']}
(OUT/'native-contact-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':'PASS','native_damage_cases':len(damage),'cooldown_equalities':len(equality),'weapon_transfers':len(transfers),'roles':result['observed_behavior_ids_by_role'],'traffic_states':result['traffic_states_observed'],'result_transitions':result['result_transitions']},indent=2))
