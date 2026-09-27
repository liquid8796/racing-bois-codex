"""Verify evidence provenance and exact instruction bytes, not self-award parity."""
import hashlib
import json
import sqlite3
from native_project import SOURCE, OUT, EXPECTED_SHA256, REPO
import pefile

pe=pefile.PE(str(SOURCE))
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED_SHA256
manifest=json.loads((REPO/'docs/reverse-engineering/assets/source_manifest.json').read_text())
expected_paths={r['path'] for r in manifest}
actual_paths={p.relative_to(SOURCE.parent).as_posix() for p in SOURCE.parent.rglob('*') if p.is_file()}
assert expected_paths==actual_paths,dict(added=sorted(actual_paths-expected_paths),removed=sorted(expected_paths-actual_paths))
for r in manifest:
    file=SOURCE.parent/r['path']
    assert file.stat().st_size==r['bytes']
    assert hashlib.sha256(file.read_bytes()).hexdigest()==r['sha256'],r['path']
with sqlite3.connect(OUT/'native-analysis.sqlite') as con:
    rows=con.execute('SELECT va,bytes FROM instructions').fetchall()
    assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    for va,encoded in rows:
        raw=bytes.fromhex(encoded)
        assert pe.get_data(va-pe.OPTIONAL_HEADER.ImageBase,len(raw))==raw,hex(va)
fixtures=json.loads((OUT/'parity-fixtures.json').read_text())
assert fixtures['source_sha256']==EXPECTED_SHA256
assert len(fixtures['cases'])==fixtures['case_count']==fixtures['passed']
assert len({r['test_id'] for r in fixtures['cases']})==len(fixtures['cases'])
assert all(r['status']=='PASS' and r['expected']==r['actual'] for r in fixtures['cases'])
ai=json.loads((OUT/'ai-decision-fixtures.json').read_text())
assert ai['source_sha256']==EXPECTED_SHA256
assert len(ai['cases'])==ai['case_count']==ai['passed']
assert all(r['expected']==r['actual'] for r in ai['cases'])
contacts=json.loads((OUT/'native-contact-validation.json').read_text())
assert contacts['status']=='PASS' and contacts['source_sha256']==EXPECTED_SHA256
bench=json.loads((OUT/'bike-component-bench.json').read_text())
assert bench['source_sha256']==EXPECTED_SHA256
assert len(bench['records'])==15
assert all(len(r['samples'])==30 and len(r['gears'])==7 and r['brake_ticks_to_zero'] for r in bench['records'])
matrix=[]
for address,count in fixtures['cases_by_routine'].items():
    subset=[r for r in fixtures['cases'] if r['source_va']==address]
    matrix.append({'source_va':address,'status':'COMPONENT_PASS','case_count':count,'fixture_ids':[r['test_id'] for r in subset],'tolerance':0,'units':'raw x86 integer/byte state','full_game_gate_closed':False,'hooks':sorted({h for r in subset for h in r['external_hooks']})})
native=[]
for name in ['keyboard-trace','brake','steering','combat','hit','steal','police']:
    path=OUT/('native-probe-'+name+'.json')
    if not path.exists():continue
    evidence=json.loads(path.read_text())
    samples=[r['payload'] for r in evidence['events'] if r.get('payload',{}).get('kind')=='native_state']
    assert samples and evidence['original_executable_unchanged'] and not evidence['copy_file_changes']
    native.append({'test_id':'NATIVE-'+name.upper(),'status':'NATIVE_OBSERVED','source_va':['0x434660','0x44b3b0'],'source_sha256':evidence['source_sha256'],'trace':path.name,'csv':'native-'+name+'.csv','sample_count':len(samples),'units':'original integer fields; ticks at nominal60Hz','tolerance':None,'tolerance_note':'No Unity comparison yet; raw reference observations only','full_game_gate_closed':False})
matrix.append({'source_va':'0x4092e0','status':'COMPONENT_PASS','case_count':ai['case_count'],'fixtures':'ai-decision-fixtures.json','tolerance':0,'units':'raw integer fields and bounded PRNG low byte','full_game_gate_closed':False})
(OUT/'ParityMatrix.json').write_text(json.dumps({'whole_game_parity':'OPEN','components':matrix,'native_scenarios':native,'native_contacts':{'status':contacts['status'],'evidence':'native-contact-validation.json','damage_cases':len(contacts['damage_cases']),'strict_equality_cases':len(contacts['strict_cooldown_equalities']),'transfers':len(contacts['weapon_transfers'])},'uncovered_required_domains':['complete live movement/steering/slope/jump/collision traces','full AI relationship/avoidance/traffic FSM and natural police spawn','all weapon combinations and animation hit timing under natural motion','all crash/bust/wreck/recovery transitions','complete menu media flow','finish ordering and campaign playthrough','mod versus vanilla binary differences']},indent=2)+'\n')
result={'status':'PASS','source_unchanged':True,'all_original_files_verified':len(manifest),'added_or_removed_source_files':0,'sqlite_integrity':'ok','instruction_bytes_verified':len(rows),'fixture_cases':fixtures['case_count'],'ai_fixture_cases':ai['case_count'],'total_instruction_fixture_cases':fixtures['case_count']+ai['case_count'],'native_weapon_damage_cases':len(contacts['damage_cases']),'native_weapon_transfers':len(contacts['weapon_transfers']),'bike_component_records':15,'full_game_parity':'OPEN'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
