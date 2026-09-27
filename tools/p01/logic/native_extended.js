// Additive P01 contact-arena and live actor/behavior observations.
// Original gameplay routines retain their behavior; Frida instruments entries.
// The contact arena explicitly relocates the test
// pair immediately before hit processing; it is not natural collision gameplay.
const nativeActors=new Map(),nativeTraffic=new Map(),dispatchSeen=new Set();
let contactTarget=null,contactPhase=-1,arrangeCount=0,policeSpawned=false;
function tickNow(){return ptr(0x4b7ecc).readU32();}
function riderOf(bike){return bike.add(0x2fc).readPointer();}
function behaviorOf(bike){return riderOf(bike).add(0x1d8).readPointer();}
function statOf(bike){return riderOf(bike).add(0x1e0).readPointer();}
function actorInfo(bike){
  const rider=riderOf(bike),behavior=behaviorOf(bike),stats=statOf(bike),meta=nativeActors.get(bike.toString())||{};
  return {pointer:bike.toString(),template:meta.template||null,slot:bike.add(0x328).readS8(),characterId:behavior.add(0x165).readS8(),ownership:bike.add(0x324).readS32(),role:bike.equals(ptr(0x4642d8).readPointer())?'local_player':bike.equals(ptr(0x4642dc).readPointer())?'police_global':meta.template==='0x464310'?'police_template':bike.add(0x324).readS32()===0?'local_player_pending_global':'opponent',state:bike.add(0x2f4).readS32(),behavior:behavior.add(0x160).readS32(),intent:behavior.add(0x174).readS32(),target:behavior.add(0x168).readPointer().toString(),weapon:rider.add(0x1c8).readS32(),attack:rider.add(0x1d4).readS32(),animation:rider.add(0x80).readS8(),animationFrame:rider.add(0x81).readS8(),stealUntil:rider.add(0x1cc).readU32(),hitUntil:rider.add(0x1d0).readU32(),baseStrength:stats.add(0x30).readS32(),maxEndurance:stats.add(0x34).readS32(),endurance:stats.add(0x38).readS32(),health:stats.add(0x3c).readS32(),bikeCondition:bike.add(0x2f0).readS32(),velocity:bike.add(0xec).readS32(),longitudinal:bike.add(0x1c).readS32(),lateral:bike.add(0x28).readS32(),height:bike.add(0x20).readS32()};
}
Interceptor.attach(ptr(0x405990),{onEnter(){this.template=this.context.ecx.toString();this.character=this.context.esp.add(16).readS32();this.slot=this.context.esp.add(20).readS32();},onLeave(value){
  if(value.isNull())return;nativeActors.set(value.toString(),{template:this.template,characterArgument:this.character,slotArgument:this.slot});
  log('native_actor_created',{tick:tickNow(),...actorInfo(value)});
}});
Interceptor.attach(ptr(0x4387a0),{onEnter(){this.template=this.context.edx.toString();},onLeave(value){
  if(!value.isNull()&&this.template==='0x46dde0'){nativeTraffic.set(value.toString(),{object:value,last:null});log('native_traffic_created',{tick:tickNow(),pointer:value.toString(),template:this.template,objectType:value.add(0xc4).readU32(),updateCallback:value.add(0xe0).readPointer().toString()});}
}});
// Observe only live objects currently executing their original update callback.
// Constructor addresses can be recycled when pre-race world resources unload.
Interceptor.attach(ptr(0x440dd0),{onEnter(){
  const object=this.context.ecx,key=object.toString(),state=object.add(0x1ec).readS32(),type=object.add(0x1e4).readS32();
  const previous=nativeTraffic.get(key);
  if(!previous||previous.last!==state){nativeTraffic.set(key,{object,last:state});log('native_traffic_live_update',{tick:tickNow(),source_va:'0x440dd0',pointer:key,objectType:object.add(0xc4).readU32(),trafficType:type,state,velocity:object.add(0xec).readS32(),longitudinal:object.add(0x1c).readS32()});}
}});
Interceptor.attach(ptr(0x408df0),{onEnter(){this.bike=this.context.ecx;this.before=actorInfo(this.bike);this.to=this.context.edx.toInt32();},onLeave(){if(this.before.behavior!==this.to)log('native_behavior_transition',{tick:tickNow(),before:this.before,after:actorInfo(this.bike)});}});
Interceptor.attach(ptr(0x407c8e),function(){
  const bike=this.context.ecx,info=actorInfo(bike),id=this.context.eax.toInt32(),key=info.role+':'+info.slot+':'+id;
  if(!dispatchSeen.has(key)){dispatchSeen.add(key);log('native_behavior_dispatch',{tick:tickNow(),...info,dispatchId:id,callback:ptr(0x465980+id*4).readPointer().toString()});}
});
const chooseAttack=new NativeFunction(ptr(0x4095d0),'void',['pointer','pointer','int'],'fastcall');
const spawnCop=new NativeFunction(ptr(0x406b80),'void',['pointer','int'],'fastcall');
function arrangeContact(player,target){
  const tr=riderOf(target),pr=riderOf(player);
  // Choose existing first forward rider; move player just behind it, preserving
  // the nearby forward scan's typed-rider selection during this isolated call.
  const longitudinal=tr.add(0x1c).readS32()-16,lateral=tr.add(0x28).readS32()-8192,height=tr.add(0x20).readS32();
  for(const p of [player,pr]){p.add(0x1c).writeS32(longitudinal);p.add(0x28).writeS32(lateral);p.add(0x20).writeS32(height);p.add(0x2c).writePointer(tr.add(0x2c).readPointer());}
  arrangeCount++;
}
Interceptor.attach(ptr(0x4096f0),{onEnter(){
  this.attacker=this.context.ecx;this.observe=false;
  const player=ptr(0x4642d8).readPointer(),tick=tickNow();
  if(!this.attacker.equals(player)||!contactTarget||tick<120||tick>=600)return;
  arrangeContact(player,contactTarget);
  if(scenario==='steal'&&riderOf(player).add(0x1c8).readS32()===0){
    const targetRider=riderOf(contactTarget);
    targetRider.add(0x1c8).writeS32(2);targetRider.add(0x1d4).writeS32(2);targetRider.add(0x1cc).writeU32(0);
    behaviorOf(contactTarget).add(0x168).writePointer(player);chooseAttack(contactTarget,player,0);
  }
  this.observe=true;this.before={attacker:actorInfo(player),target:actorInfo(contactTarget)};
},onLeave(){if(this.observe)log('native_contact_result',{tick:tickNow(),scenario,phase:contactPhase,arranged:true,before:this.before,after:{attacker:actorInfo(this.attacker),target:actorInfo(contactTarget)}});}});
Interceptor.attach(ptr(0x409c10),{onEnter(){this.attacker=this.context.ecx;this.target=this.context.edx;this.tick=tickNow();},onLeave(result){
  if(this.attacker.equals(ptr(0x4642d8).readPointer())&&contactTarget&&this.tick>=120&&this.tick<600)log('native_range_result',{tick:this.tick,accepted:result.toUInt32()&255,attacker:this.attacker.toString(),target:this.target.toString()});
}});
Interceptor.attach(ptr(0x409ad0),{onEnter(){this.a=this.context.ecx;this.t=this.context.edx;this.capture=this.a.equals(ptr(0x4642d8).readPointer());if(this.capture)this.before={attacker:actorInfo(this.a),target:actorInfo(this.t)};},onLeave(){if(this.capture)log('native_weapon_damage_result',{tick:tickNow(),before:this.before,after:{attacker:actorInfo(this.a),target:actorInfo(this.t)}});}});
Interceptor.attach(ptr(0x4052c0),{onEnter(){
  const target=this.context.ecx;if(nativeActors.has(target.toString()))log('native_damage_sink',{tick:tickNow(),caller:this.returnAddress.toString(),target:target.toString(),damage:this.context.edx.toInt32(),secondary:this.context.esp.add(4).readS32(),type:this.context.esp.add(8).readS32()});
}});
let outcomeLogged=new Set();
Interceptor.attach(ptr(0x416010),{onEnter(){this.request=this.context.ecx.toInt32();this.countdown=this.context.edx.toInt32();},onLeave(){
  const key=this.request+':'+ptr(0x4c5d7c).readS32();if(outcomeLogged.has(key))return;outcomeLogged.add(key);
  const player=ptr(0x4642d8).readPointer(),cop=ptr(0x4642dc).readPointer();log('native_outcome_request',{tick:tickNow(),request:this.request,countdown:this.countdown,result:ptr(0x4c5d7c).readS32(),player:player.isNull()?null:actorInfo(player),cop:cop.isNull()?null:actorInfo(cop)});
}});
Interceptor.attach(ptr(0x416120),{onLeave(value){log('native_result_transition',{tick:tickNow(),transition:value.toInt32(),positionIndex:ptr(0x4b8a16).readU8(),cash:ptr(0x4b8a18).readU32()});}});
Interceptor.attach(ptr(0x44b3b0),{onLeave(){
  const tick=tickNow(),player=ptr(0x4642d8).readPointer();if(player.isNull())return;
  if((scenario==='hit'||scenario==='steal')&&tick>=118&&tick<600){
    if(!contactTarget){
      let node=riderOf(player).readPointer();
      for(let n=0;n<200&&!node.isNull()&&!node.readPointer().isNull();n++,node=node.readPointer()){
        if(node.add(0xc4).readU32()===8){const bike=node.add(0x1c4).readPointer();if(!bike.equals(player)&&nativeActors.has(bike.toString())){contactTarget=bike;break;}}
      }
      if(contactTarget)log('native_contact_setup',{tick,scenario,attacker:actorInfo(player),target:actorInfo(contactTarget),intervention:'Player positions are clamped beside this existing forward rider immediately before each original hit-processing call; not natural-play positioning.'});
    }
    const phase=scenario==='hit'?Math.max(0,Math.floor((tick-120)/120)):0;
    if(contactTarget&&phase!==contactPhase){
      contactPhase=phase;const rider=riderOf(player);rider.add(0x1c8).writeS32(phase===3?0:phase);rider.add(0x1d4).writeS32(phase===3?3:phase);
      // Reset test recipient pools once per weapon case, not once per hit.
      const stats=statOf(contactTarget);stats.add(0x38).writeS32(stats.add(0x34).readS32());stats.add(0x3c).writeS32(20000);contactTarget.add(0x2f0).writeS32(20000);riderOf(contactTarget).add(0x1d0).writeU32(0);
      log('native_weapon_case_setup',{tick,phase,player:actorInfo(player),target:actorInfo(contactTarget)});
    }
  }
  if(scenario==='police'&&!policeSpawned&&tick>=180){policeSpawned=true;log('probe_invoke_police_spawn',{tick,source_va:'0x406b80',segment:player.add(0x2c).readPointer().toString(),argument2:0,reason:'Controlled initial spawn via original routine; natural spawn trigger not claimed.'});spawnCop(player.add(0x2c).readPointer(),0);const cop=ptr(0x4642dc).readPointer();if(!cop.isNull()){nativeActors.set(cop.toString(),{template:'0x464310',evidence:'0x406c4d constructor argument inside original spawn'});log('native_police_identity',{tick,...actorInfo(cop)});}}
}});
