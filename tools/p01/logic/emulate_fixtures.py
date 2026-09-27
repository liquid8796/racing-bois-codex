"""Execute original PE instructions in an x86 emulator, with no native OS calls.

Only PE bytes from SOURCE are loaded. Import execution is forbidden. Named hooks
replace narrowly documented external services (TLS, event emission, damage sink).
Randomized differential cases compare independent field-level reference rules.
This is component execution evidence, never a full original-game runtime trace.
"""
import hashlib
import json
from pathlib import Path
import random
import struct
import sys
from native_project import SOURCE, OUT, EXPECTED_SHA256
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESP, UC_X86_REG_EIP

SENTINEL = 0x700000
OBJECT, RIDER, STATS, TARGET, SEGMENT, TLS = [0x600000+i*0x1000 for i in range(6)]
STACK = 0x710000

def trunc(value, divisor):
    return (abs(value)//abs(divisor)) * (-1 if (value<0)!=(divisor<0) else 1)

class OriginalCPU:
    def __init__(self):
        assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED_SHA256,'Unrecognized source binary'
        self.pe = pefile.PE(str(SOURCE))
        self.cpu = Uc(UC_ARCH_X86,UC_MODE_32)
        size=(self.pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095
        self.cpu.mem_map(0x400000,size)
        self.cpu.mem_write(0x400000,self.pe.get_memory_mapped_image())
        self.cpu.mem_map(0x600000,0x10000)
        self.cpu.mem_map(0x700000,0x20000)
        self.calls=[]
        self.steps=0
        self.limit=20000
        self.hooks={}
        self.cpu.hook_add(UC_HOOK_CODE,self.on_instruction)
    def write(self,address,value): self.cpu.mem_write(address,struct.pack('<I',value&0xffffffff))
    def byte(self,address,value): self.cpu.mem_write(address,bytes([value&255]))
    def read(self,address,signed=False): return int.from_bytes(self.cpu.mem_read(address,4),'little',signed=signed)
    def ret(self,pop=0,result=0):
        sp=self.cpu.reg_read(UC_X86_REG_ESP)
        target=self.read(sp)
        self.cpu.reg_write(UC_X86_REG_EAX,result&0xffffffff)
        self.cpu.reg_write(UC_X86_REG_ESP,sp+4+pop)
        self.cpu.reg_write(UC_X86_REG_EIP,target)
    def on_instruction(self,cpu,address,size,_):
        self.steps+=1
        if self.steps>self.limit:
            cpu.emu_stop();return
        if address==SENTINEL: cpu.emu_stop(); return
        if address in self.hooks:
            self.calls.append(hex(address)); self.hooks[address](self); return
        if not 0x401000 <= address < 0x461690:
            raise RuntimeError('Unexpected external execution at '+hex(address))
    def reset_objects(self):
        self.cpu.mem_write(0x600000,b'\0'*0x10000)
        self.write(OBJECT+0x2fc,RIDER)
        self.write(RIDER+0x1e0,STATS)
        self.write(OBJECT+0x2c,SEGMENT)
        self.write(0x4642d8,0)
        self.write(0x4642dc,0)
        self.hooks={}
    def run(self,address,ecx=OBJECT,edx=0,args=(),limit=20000):
        self.steps=0; self.calls=[];self.limit=limit
        self.write(STACK,SENTINEL)
        for i,value in enumerate(args): self.write(STACK+4+4*i,value)
        for register,value in [(UC_X86_REG_ECX,ecx),(UC_X86_REG_EDX,edx),(UC_X86_REG_ESP,STACK)]: self.cpu.reg_write(register,value)
        self.cpu.emu_start(address,SENTINEL+1)
        assert self.cpu.reg_read(UC_X86_REG_EIP)==SENTINEL, ('instruction budget exceeded',hex(address),self.steps)
        return self.cpu.reg_read(UC_X86_REG_EAX)

def main():
    vm=OriginalCPU(); rng=random.Random(1996); results=[]
    def check(test_id,address,inputs,expected,actual,hooks=None):
        assert actual==expected,(test_id,inputs,expected,actual)
        results.append(dict(test_id=test_id,source_va=hex(address),inputs=inputs,expected=expected,actual=actual,status='PASS',instruction_count=vm.steps,external_hooks=hooks or []))

    # Strict range boundaries and side equality, all weapon numeric IDs.
    for weapon in range(4):
        reach=[5,7,8,5][weapon]<<12
        for longitudinal in [0,63,64,-63,-64]:
            for lateral in [0,1,reach-1,reach,-reach+1,-reach]:
                for height in [0,0x2fff,0x3000,-0x3000]:
                    for side in [0,1]:
                        vm.reset_objects()
                        for off,val in [(0x1c,longitudinal),(0x28,lateral),(0x20,height)]:vm.write(TARGET+off,val)
                        out=vm.run(0x409c10,OBJECT,TARGET,(side,weapon))&255
                        expected=int(int(lateral>0)==side and abs(longitudinal)<64 and abs(lateral)<reach and abs(height)<0x3000)
                        check('RANGE-%04d'%len(results),0x409c10,dict(weapon=weapon,delta_longitudinal=longitudinal,delta_lateral=lateral,delta_height=height,side=side),expected,out)

    # Gear step can move only once, strict threshold comparisons, 7 slots.
    for gear in [-2,0,1,3,5,6,9]:
        upper=[1000+2000*i for i in range(7)]; lower=[max(0,v-750) for v in upper]
        for speed in [-1,0,lower[min(6,max(0,gear))]-1,lower[min(6,max(0,gear))],upper[min(6,max(0,gear))],upper[min(6,max(0,gear))]+1,30000]:
            vm.reset_objects(); vm.write(OBJECT+0x23c,gear);vm.write(OBJECT+0xec,speed)
            for i in range(7): vm.write(OBJECT+0x1d4+16*i,upper[i]);vm.write(OBJECT+0x1d8+16*i,lower[i])
            g=min(6,max(0,gear))
            expected=min(6,g+1) if speed>upper[g] else max(0,g-1) if speed<lower[g] else g
            vm.run(0x4391d0)
            check('GEAR-%04d'%len(results),0x4391d0,dict(gear=gear,speed=speed,upper=upper,lower=lower),expected,vm.read(OBJECT+0x23c))

    # Surface region classification contains strict road boundaries and flags.
    for flags in [0,8,16,32]:
        for material in range(4):
            for lateral in [-300,-201,-200,-199,-100,-99,0,99,100,101,148,149,199,200,201,300]:
                vm.reset_objects()
                for off,v in [(0xe0,-100),(0xe4,100),(0xe8,-200),(0xec,200)]:vm.write(SEGMENT+off,v)
                vm.byte(SEGMENT+0x37,flags);vm.byte(SEGMENT+0x3c,material)
                if -100<lateral<100: expected=0
                elif flags&32: expected=0
                elif flags&24: expected=1 if material==0 else 2
                elif material==3: expected=1
                elif lateral>100: expected=3 if lateral>=200 else 1 if material==0 else 0 if lateral<=148 else 2
                else: expected=3 if lateral<=-200 else 1 if material==0 else 0 if lateral>=-148 else 2
                out=vm.run(0x43a0c0,SEGMENT,lateral<<8)&255
                check('SURFACE-%04d'%len(results),0x43a0c0,dict(flags=flags,material=material,lateral_q8=lateral<<8),expected,out)

    # Forward velocity equation in the explicitly airborne/contact=0 branch.
    for i in range(250):
        vm.reset_objects()
        velocity=rng.randint(-12000,30000);drive=rng.randint(-100,150);drag_coeff=rng.randint(0,512);steer=rng.randint(-1000,1000);dt=rng.choice([1,2,3])
        for off,v in [(0xec,velocity),(0x114,drive),(0x150,drag_coeff),(0x118,steer),(0x18,dt),(0x160,0)]:vm.write(OBJECT+off,v)
        drag=(drag_coeff*((abs(velocity)>>2)>>8))>>8
        steer_loss=abs(steer)//16
        acceleration=drive-drag-steer_loss if velocity>=0 else drive+abs(drag+steer_loss)
        new=velocity+acceleration*dt
        if velocity>=0 and new<=0:new=100 if drive>0 else 0
        elif velocity<0 and new>0:new=0
        vm.run(0x4390c0)
        check('VELOCITY-%04d'%i,0x4390c0,dict(velocity=velocity,drive=drive,drag_coeff=drag_coeff,steer_term=steer,dt=dt,contact=0),dict(velocity=new,acceleration=acceleration,drag=drag),dict(velocity=vm.read(OBJECT+0xec,True),acceleration=vm.read(0x4c3cec,True),drag=vm.read(OBJECT+0x15c,True)))

    # Damage producer executes unchanged machine code; sink is recorded, not applied.
    for weapon in range(4):
        for strength in [1,15,60,127]:
            for endurance in [0,1,64,127,128,200,256]:
                vm.reset_objects()
                for off,v in [(0x30,strength),(0x34,256),(0x38,endurance)]:vm.write(STATS+off,v)
                vm.write(RIDER+0x1d4,weapon); captured={}
                def sink(m):
                    sp=m.cpu.reg_read(UC_X86_REG_ESP)
                    captured.update(damage=m.cpu.reg_read(UC_X86_REG_EDX),secondary=m.read(sp+4),kind=m.read(sp+8))
                    m.ret(8)
                vm.hooks[0x4052c0]=sink
                effective=max(((endurance<<8)//256*strength)>>8,strength//2)
                damage=(effective*[256,320,384,64][weapon])//256
                secondary=damage//4+1 if weapon==3 else 0
                vm.run(0x409ad0,OBJECT,TARGET)
                check('DAMAGE-%04d'%len(results),0x409ad0,dict(weapon=weapon,strength=strength,denominator=256,endurance=endurance),dict(damage=damage,secondary=secondary,kind=5 if secondary>=1 else 4),captured,['0x4052c0 capture arguments and return; recipient mutation intentionally outside this fixture'])

    # Independent recipient pool/clamp/authority tests; mode2 avoids event emitter.
    for ownership in [-1,2]:
        for damage in [0,1,15,30,60,1000]:
            vm.reset_objects();vm.write(OBJECT+0x324,ownership)
            for off,v in [(0x34,101),(0x38,80),(0x3c,1500)]:vm.write(STATS+off,v)
            vm.run(0x4050c0,OBJECT,damage)
            expected=dict(endurance=80 if ownership==-1 else max(80-4*damage,50),health=1500 if ownership==-1 else max(1500-64*damage,0))
            check('POOLS-%04d'%len(results),0x4050c0,dict(ownership=ownership,damage=damage,max_endurance=101,endurance=80,health=1500),expected,dict(endurance=vm.read(STATS+0x38),health=vm.read(STATS+0x3c)))
            vm.write(OBJECT+0x2f0,25);vm.run(0x4051e0,OBJECT,damage)
            check('BIKE-%04d'%len(results),0x4051e0,dict(ownership=ownership,damage=damage,condition=25),25 if ownership==-1 else max(25-damage,0),vm.read(OBJECT+0x2f0))

    # Input mailbox is a consume-once payload, not a held-key state by itself.
    for slot in range(8):
        for payload in [0,1,0x20,0x40,0x80,0xffffffff]:
            vm.reset_objects();vm.byte(OBJECT+0x328,slot);base=0x4c3810+24*slot
            vm.write(base+5,payload);vm.byte(base+9,1)
            first=vm.run(0x440410);second=vm.run(0x440410)
            check('INPUT-%04d'%len(results),0x440410,dict(slot=slot,payload=payload,available=1),[payload,0,0],[first,second,vm.cpu.mem_read(base+9,1)[0]])

    # Level-up mask accepts exactly 31, not arbitrary superset values.
    for level in range(5):
        for mask in [0,1,15,30,31,63,255]:
            vm.reset_objects();vm.byte(0x4b8a12,level);vm.byte(0x4b8a13,mask);vm.write(0x4753b0,0)
            out=vm.run(0x41f6d0,1)
            expected=[0x23 if level==4 else 0x20,level if level==4 else level+1,0] if mask==31 else [9,level,mask]
            check('CAMPAIGN-%04d'%len(results),0x41f6d0,dict(level=level,mask=mask,mode=0),expected,[out,vm.cpu.mem_read(0x4b8a12,1)[0],vm.cpu.mem_read(0x4b8a13,1)[0]])

    # Complete outcome threshold: offline top3, network flag top1.
    for network in [0,1]:
        for place_index in range(14):
            vm.reset_objects()
            vm.write(0x4753c4,0);vm.byte(0x4753b4,0)
            vm.byte(0x4c5b00,network);vm.byte(0x4c5af9,0);vm.byte(0x4c5d78,place_index)
            vm.run(0x416010,0x7f,180)
            check('QUALIFY-%d-%02d'%(network,place_index),0x416010,dict(network_flag=network,place_index=place_index,request=127,countdown=180),[2 if place_index<(1 if network else 3) else 3,180],[vm.read(0x4c5d7c),vm.read(0x4753c4)])
    vm.byte(0x4c5b00,0)
    # Qualification transition0x1e alone awards course bit; movie playback stub.
    for transition in [0x1c,0x1d,0x1e,0x1f]:
        for course in range(1,6):
            for mode in [1,2,3]:
                vm.reset_objects();vm.write(0x4753b0,mode);vm.byte(0x4b8a15,course);vm.byte(0x4b8a13,0);vm.byte(0x4b8a12,0)
                vm.hooks[0x4023e0]=lambda m:m.ret(4)
                vm.run(0x449150,transition)
                expected=1<<(course-1) if transition==0x1e and mode!=3 else 0
                check('COURSE-BIT-%02x-%d-%d'%(transition,course,mode),0x449150,dict(transition=transition,course=course,mode=mode),expected,vm.cpu.mem_read(0x4b8a13,1)[0],['0x4023e0 movie playback omitted'])

    # The recovery state machine is executed with animation setters stubbed.
    # Position/state decisions stay native; animation asset loading stays outside.
    for longitudinal in [-10,-9,0,9,10]:
        for lateral in [-1,0,6000,12000,12001]:
            for condition in [0,25]:
                vm.reset_objects();vm.write(RIDER+0x1d8,STATS)
                vm.byte(STATS+0x160,8);vm.write(OBJECT+0x324,2)
                vm.write(OBJECT+0x2f4,2);vm.write(OBJECT+0x2f0,condition)
                vm.write(OBJECT+0x1c,longitudinal);vm.write(OBJECT+0x28,lateral)
                vm.byte(RIDER+0x80,0x26);vm.write(0x4b7ed0,0)
                animation=[]
                def set_animation(m):
                    animation.append(m.cpu.reg_read(UC_X86_REG_EDX));m.ret()
                vm.hooks[0x40ac70]=set_animation;vm.hooks[0x40aca0]=lambda m:m.ret()
                vm.run(0x40a600)
                near=abs(longitudinal)<=9 and 0<=lateral<=12000
                expected=dict(state=3 if near and condition else 2,animation=[0x29 if condition else 0x25] if near else [],rider_velocity=0 if near else 1200)
                check('RECOVERY-%04d'%len(results),0x40a600,dict(longitudinal_delta=longitudinal,lateral_delta=lateral,condition=condition,state=2,animation=0x26,behavior_time=0),expected,dict(state=vm.read(OBJECT+0x2f4),animation=animation,rider_velocity=vm.read(RIDER+0xec)),['0x40ac70 animation setter captured','0x40aca0 secondary animation setter omitted'])

    # Save fixture corpus keeps original names, bytes and valid checksums.
    for file in sorted(SOURCE.parent.joinpath('SAVES').glob('*.RRS')):
        data=file.read_bytes();vm.reset_objects();vm.cpu.mem_write(OBJECT,data[4:])
        out=vm.run(0x42efc0,OBJECT,len(data)-4)
        check('SAVE-'+file.stem,0x42efc0,dict(file=file.name,sha256=hashlib.sha256(data).hexdigest(),length=len(data)-4),int.from_bytes(data[:4],'little'),out)

    # Runtime animation records have signed-byte tick durations and flags.
    # Proves equality advance and one-frame-per-call catch-up behavior.
    for duration in [1,2,3,5,10,25]:
        for delta in [-1,0,1,100]:
            vm.reset_objects();vm.write(OBJECT+8,RIDER);vm.write(RIDER,STATS);vm.write(RIDER+4,TARGET)
            vm.byte(OBJECT+0x10,0);vm.byte(OBJECT+0x11,0);vm.byte(OBJECT+0x12,255);vm.write(OBJECT+0x14,100+duration)
            vm.byte(STATS+0xc,duration);vm.byte(STATS+0xd,0);vm.byte(STATS+20+0xc,7)
            vm.write(0x4b7ecc,100+duration+delta);vm.run(0x43ae90)
            advanced=delta>=0
            expected=[1 if advanced else 0,100+duration+(7 if advanced else 0)]
            check('ANIMATION-%d-%d'%(duration,delta),0x43ae90,dict(frame0_duration=duration,frame1_duration=7,deadline=100+duration,clock=100+duration+delta,flags=0),expected,[vm.cpu.mem_read(OBJECT+0x11,1)[0],vm.read(OBJECT+0x14)])
    for flags,queued in [(0x11,255),(0x21,255),(1,1),(2,1)]:
        vm.reset_objects();vm.write(OBJECT+8,RIDER);vm.write(RIDER,STATS);vm.write(RIDER+4,TARGET)
        vm.byte(OBJECT+0x10,0);vm.byte(OBJECT+0x11,0);vm.byte(OBJECT+0x12,queued);vm.byte(OBJECT+0x18,2);vm.write(OBJECT+0x14,100)
        vm.byte(STATS+0xd,flags)
        for i in range(3):vm.byte(STATS+20*i+0xc,5+i)
        vm.byte(TARGET+0xc,9);vm.write(0x4b7ecc,100);vm.run(0x43ae90)
        loop=(flags&15)==1 and queued==255
        frame=flags>>4 if loop else 0
        expected=[0 if loop else 1,frame,3 if loop else 0,100+(5+frame if loop else 9)]
        check('ANIMATION-LOOP-%d-%d'%(flags,queued),0x43ae90,dict(flags=flags,queued=queued,loop_count=2,deadline=100,clock=100),expected,[vm.cpu.mem_read(OBJECT+0x10,1)[0],vm.cpu.mem_read(OBJECT+0x11,1)[0],vm.cpu.mem_read(OBJECT+0x18,1)[0],vm.read(OBJECT+0x14)])

    # CRT rand asks for a thread-local struct; hook only its address provider.
    for seed in [0,1,1996,0x7fffffff,0xffffffff]:
        vm.reset_objects();vm.write(TLS+0x14,seed);vm.hooks[0x4592b0]=lambda m:m.ret(result=TLS)
        state=seed
        for index in range(32):
            state=(214013*state+2531011)&0xffffffff
            out=vm.run(0x455eb0)
            check('RNG-%08x-%02d'%(seed,index),0x455eb0,dict(initial_seed=seed,sequence_index=index),dict(state=state,value=(state>>16)&32767),dict(state=vm.read(TLS+0x14),value=out),['0x4592b0 TLS address provider only'])
    grouped={}
    for r in results:grouped[r['source_va']]=grouped.get(r['source_va'],0)+1
    OUT.mkdir(parents=True,exist_ok=True)
    evidence={'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'engine':'Unicorn 2.1.4 x86-32','kind':'isolated original-instruction component execution','full_game_runtime':False,'host_imports_executed':0,'random_seed':1996,'case_count':len(results),'passed':len(results),'cases_by_routine':grouped,'cases':results}
    (OUT/'parity-fixtures.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({k:v for k,v in evidence.items() if k!='cases'},indent=2))

if __name__=='__main__':main()
