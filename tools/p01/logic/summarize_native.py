"""Summarize measured trace ranges without inventing physical units or parity."""
import csv
import json
import statistics
from native_project import OUT

summaries=[]
for name in ['keyboard-trace','brake','steering','combat','hit','steal','police']:
    path=OUT/('native-probe-'+name+'.json')
    if not path.exists():continue
    probe=json.loads(path.read_text())
    events=[m.get('payload',{}) for m in probe['events']]
    states=[e for e in events if e.get('kind')=='native_state']
    if not states:continue
    rates=[(b['tick']-a['tick'])*1000/(b['wallMs']-a['wallMs']) for a,b in zip(states,states[1:]) if b['tick']>a['tick'] and b['wallMs']>a['wallMs']]
    inputs=[e for e in events if e.get('kind')=='native_input_transition']
    brakes=[]
    for start in [i for i in inputs if i['bits']==2]:
        initial=min(states,key=lambda s:abs(s['tick']-start['tick']))
        stop=next((s for s in states if s['tick']>start['tick'] and s['input']==2 and s['riderState']==0 and s['velocity']==0),None)
        brakes.append({'input_tick':start['tick'],'nearest_velocity':initial['velocity'],'first_sampled_stop_tick':stop['tick'] if stop else None,'elapsed_ticks_upper_bound':stop['tick']-start['tick'] if stop else None,'sample_interval_ticks':6,'is_uncontaminated_brake_stop':bool(stop and all(s['riderState']==0 for s in states if start['tick']<=s['tick']<=stop['tick']))})
    with (OUT/('native-'+name+'.csv')).open('w',newline='') as f:
        keys=list(dict.fromkeys(k for row in states for k in row))
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(states)
    summary={'name':name,'trace':path.name,'sample_count':len(states),'tick_range':[states[0]['tick'],states[-1]['tick']],'median_observed_hz':statistics.median(rates),'observed_hz_range':[min(rates),max(rates)],'velocity_range_internal':[min(s['velocity'] for s in states),max(s['velocity'] for s in states)],'lateral_range_internal':[min(s['lateral'] for s in states),max(s['lateral'] for s in states)],'rider_states':sorted({s['riderState'] for s in states}),'input_transitions':inputs,'braking':brakes,'animation_transitions':[e for e in events if e.get('kind')=='native_animation_state'],'falls':[e for e in events if e.get('kind')=='native_fall_call'],'damage_calls':[e for e in events if e.get('kind')=='native_damage_call'],'native_exceptions':[e for e in events if e.get('kind')=='native_exception'],'source_executable_unchanged':probe['original_executable_unchanged'],'copy_file_changes':probe['copy_file_changes'],'limits':['local compatibility wrapper and instrumentation active','pre-race menu/media bypassed','no full native campaign','sampled state is not a complete per-instruction replay','physical unit mapping not established','not browser performance evidence']}
    summaries.append(summary)
(OUT/'native-trace-summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
print(json.dumps([{k:v for k,v in s.items() if k in ['name','sample_count','tick_range','median_observed_hz','rider_states','braking']} for s in summaries],indent=2))
