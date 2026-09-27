"""Original-code flat-surface component bench, explicitly not whole-game telemetry.

The exact SPEC initialization, throttle/brake ramp, speed and gear instructions
are used. Full update ordering, collision, rendering, input polling, traction,
network and road/height are outside this controlled bench. Only internal units
are reported, with nominal 60Hz; rider parameter75 is an explicit test input.
"""
import hashlib
import json
from native_project import REPO, OUT, SOURCE
from emulate_fixtures import OriginalCPU, OBJECT, SEGMENT

def main():
    specs=json.loads((REPO/'docs/reverse-engineering/assets/bikespec_raw.json').read_text())
    source=SOURCE.parent/'DATA/BIKESPEC.RSC'
    raw=source.read_bytes()
    records=[]
    for spec in specs:
        vm=OriginalCPU()
        vm.reset_objects()
        record=raw[spec['offset']:spec['offset']+spec['size']]
        assert len(record)==356
        spec_address=0x606000
        vm.cpu.mem_write(spec_address,record)
        index=spec['id']-1
        vm.write(0x47ea40+4*index,spec_address)
        vm.run(0x405ea0,OBJECT,75,(index,))
        gears=[{'slot':i,'torque_q8':vm.read(OBJECT+0x1d0+16*i,True),'up_threshold':vm.read(OBJECT+0x1d4+16*i,True),'down_threshold':vm.read(OBJECT+0x1d8+16*i,True)} for i in range(7)]
        # Constructor0x4387a0 copies these exact template fields at0x463ba8.
        for dst,src in [(0x148,0x1c),(0x14c,0x20),(0x150,0x24),(0x154,0x28),(0x160,0x2c)]:
            vm.write(OBJECT+dst,vm.read(0x463ba8+src))
        vm.write(OBJECT+0x18,1);vm.write(OBJECT+0x2c,SEGMENT)
        vm.write(OBJECT+0x23c,0);vm.write(OBJECT+0x240,0)
        vm.byte(OBJECT+0x244,0);vm.byte(OBJECT+0xc0,0)
        vm.write(SEGMENT+0xe0,-100);vm.write(SEGMENT+0xe4,100)
        vm.write(OBJECT+0x28,0)
        samples=[]
        for tick in range(1,1801):
            vm.run(0x40acd0,OBJECT,1)
            vm.run(0x4390c0)
            vm.run(0x4391d0)
            if tick%60==0:
                samples.append({'tick':tick,'nominal_seconds':tick/60,'velocity_internal':vm.read(OBJECT+0xec,True),'gear_slot':vm.read(OBJECT+0x23c),'drive_term':vm.read(OBJECT+0x114,True)})
        speed_before_brake=vm.read(OBJECT+0xec,True)
        stop_tick=None
        for brake_tick in range(1,1801):
            vm.run(0x40acd0,OBJECT,2)
            vm.run(0x4390c0)
            vm.run(0x4391d0)
            if vm.read(OBJECT+0xec,True)==0:stop_tick=brake_tick;break
        records.append({'spec_id':spec['id'],'spec_sha256':hashlib.sha256(record).hexdigest(),'gears':gears,'samples':samples,'brake_start_velocity_internal':speed_before_brake,'brake_ticks_to_zero':stop_tick})
        print('SPEC',spec['id'],'component bench complete',flush=True)
    result={'kind':'isolated original-code component bench','full_game_runtime':False,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'spec_source_sha256':hashlib.sha256(raw).hexdigest(),'nominal_hz':60,'initialization_rider_parameter':75,'sequence':['throttle_or_brake(0x40acd0)','forward_velocity(0x4390c0)','gear_step(0x4391d0)'],'not_measured':['real key-to-speed latency','meters/miles units','actual full-update ordering','slope','traction coupling','nitro','collision','top-speed under all conditions'],'records':records}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'bike-component-bench.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'bikes':len(records),'brake_reached_zero':sum(r['brake_ticks_to_zero'] is not None for r in records),'note':'Controlled component bench only; not whole-game acceleration parity.'},indent=2))

if __name__=='__main__':main()
