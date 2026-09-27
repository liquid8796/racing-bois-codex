'use strict';
const copyPath = __COPY_PATH_JSON__;
const raceProbe = __RACE_PROBE__;
const scenario = __SCENARIO_JSON__;
const fake = ptr('0x0bad0010');
const keep = [];
const counts = {};
const states=[];
let paletteBytes=null;
const surfaceHooks=new Set(),lockedSurfaces=new Map(),capturedFrames=new Set();
Process.setExceptionHandler(details=>{log('native_exception',{type:details.type,address:details.address.toString(),memory:details.memory?{operation:details.memory.operation,address:details.memory.address.toString()}:null,backtrace:Thread.backtrace(details.context,Backtracer.ACCURATE).map(DebugSymbol.fromAddress).map(String)});return false;});
let stoppedAtGraphics = false;
function log(kind, details = {}) { send({kind, ...details}); }
function moduleExport(dll, name) { return Process.getModuleByName(dll).getExportByName(name); }
function hook(dll, name, ret, signature, body) {
  const at = moduleExport(dll, name);
  const original = new NativeFunction(at, ret, signature, 'stdcall');
  const callback = new NativeCallback(function (...args) { return body(original, args, this); }, ret, signature, 'stdcall');
  keep.push(callback); Interceptor.replace(at, callback);
}
function string(p) { return p.isNull() ? '' : p.readAnsiString(); }
function ownsKey(p) { return p.equals(fake); }
function gameSubkey(p) { return string(p).toLowerCase().includes('vexalith interactive'); }
function allowedPath(name) {
  const full = name.replace(/\//g, '\\').toLowerCase();
  return !full.includes('..') && (full.startsWith(copyPath.toLowerCase()+'\\') || (!full.includes(':') && !full.startsWith('\\')));
}
hook('advapi32.dll','RegOpenKeyExA','long',['pointer','pointer','uint','uint','pointer'],(original,a)=>{
  if(ownsKey(a[0])||gameSubkey(a[1])) { a[4].writePointer(fake);log('virtual_registry_open',{name:string(a[1])});return 0; }
  return original(a[0],a[1],a[2],0x20019,a[4]);
});
hook('advapi32.dll','RegCreateKeyExA','long',['pointer','pointer','uint','pointer','uint','uint','pointer','pointer','pointer'],(_o,a)=>{
  if(ownsKey(a[0])||gameSubkey(a[1])){a[7].writePointer(fake);if(!a[8].isNull())a[8].writeU32(2);log('virtual_registry_create');return 0;}
  log('blocked_registry_create',{name:string(a[1])});return 5;
});
hook('advapi32.dll','RegQueryValueExA','long',['pointer','pointer','pointer','pointer','pointer','pointer'],(o,a)=>{
  if(!ownsKey(a[0]))return o(...a);
  const name=string(a[1]);
  if(name.toLowerCase()==='path'){
    const value=Memory.allocAnsiString(copyPath+'\\');const size=copyPath.length+2;
    if(!a[3].isNull())a[3].writeU32(1);
    if(!a[4].isNull()){if(a[5].readU32()<size){a[5].writeU32(size);return 234;}Memory.copy(a[4],value,size);}
    a[5].writeU32(size);log('virtual_registry_path');return 0;
  }
  log('virtual_registry_default',{name});return 2;
});
hook('advapi32.dll','RegSetValueExA','long',['pointer','pointer','uint','uint','pointer','uint'],(_o,a)=>{log('blocked_registry_write',{name:string(a[1]),virtual:ownsKey(a[0]),bytes:a[5]});return ownsKey(a[0])?0:5;});
hook('advapi32.dll','RegDeleteKeyA','long',['pointer','pointer'],(_o,a)=>{log('blocked_registry_delete',{name:string(a[1])});return ownsKey(a[0])?0:5;});
hook('advapi32.dll','RegCloseKey','long',['pointer'],(o,a)=>ownsKey(a[0])?0:o(...a));
hook('advapi32.dll','RegFlushKey','long',['pointer'],()=>0);
const addPrivateFont=new NativeFunction(moduleExport('gdi32.dll','AddFontResourceExA'),'int',['pointer','uint','pointer'],'stdcall');
const removePrivateFont=new NativeFunction(moduleExport('gdi32.dll','RemoveFontResourceExA'),'int',['pointer','uint','pointer'],'stdcall');
hook('gdi32.dll','AddFontResourceA','int',['pointer'],(_o,a)=>{const result=addPrivateFont(a[0],0x10,ptr(0));log('private_font_add',{path:string(a[0]),loaded:result,flags:0x10});return result;});
hook('gdi32.dll','RemoveFontResourceA','int',['pointer'],(_o,a)=>removePrivateFont(a[0],0x10,ptr(0)));
for(const name of ['RegEnumValueA','RegEnumKeyExA'])hook('advapi32.dll',name,'long',Array(8).fill('pointer'),(o,a)=>ownsKey(a[0])?259:o(...a));
hook('kernel32.dll','CreateFileA','pointer',['pointer','uint','uint','pointer','uint','uint','pointer'],(o,a,context)=>{
  const name=string(a[0]);const writing=(a[1]&0x50000000)!==0||a[4]!==3;
  if(writing&&!allowedPath(name)){log('blocked_file_mutation',{name});context.lastError=5;return ptr(-1);}
  const result=o(...a);if(result.equals(ptr(-1)))log('file_open_failed',{name,writing});return result;
});
hook('kernel32.dll','SetCurrentDirectoryA','int',['pointer'],(o,a)=>{
  const path=string(a[0]);
  if(path.replace(/\//g,'\\').toLowerCase()==='\\racingbo'){log('virtual_cd_cwd',{original:path});return o(Memory.allocAnsiString(copyPath));}
  if(!allowedPath(path+'\\')){log('blocked_cwd',{path});return 0;}return o(...a);
});
hook('kernel32.dll','GetDriveTypeA','uint',['pointer'],(o,a)=>{
  const path=string(a[0]);
  if(path[0]?.toLowerCase()===copyPath[0].toLowerCase()){log('virtual_cd_drive',{drive:path});return 5;}
  return o(...a);
});
hook('kernel32.dll','CreateProcessA','int',Array(10).fill('pointer'),()=>{log('blocked_child_process');return 0;});
Interceptor.attach(moduleExport('kernel32.dll','ExitProcess'),{onEnter(args){log('native_exit',{code:args[0].toUInt32(),backtrace:Thread.backtrace(this.context,Backtracer.ACCURATE).map(DebugSymbol.fromAddress).map(String)});}});
for(const [name,argc] of [['connect',3],['bind',3],['send',4],['sendto',6]])hook('wsock32.dll',name,'int',Array(argc).fill('pointer'),()=>{log('blocked_network',{api:name});return -1;});
// No fullscreen/display mutation or modal dialog on the working desktop.
hook('user32.dll','ShowWindow','int',['pointer','int'],(o,a)=>o(a[0],0));
hook('user32.dll','MessageBoxA','int',['pointer','pointer','pointer','uint'],(_o,a)=>{log('message_box',{text:string(a[1]),caption:string(a[2])});return 1;});
hook('user32.dll','SystemParametersInfoA','int',['uint','uint','pointer','uint'],(_o,a)=>{log('blocked_system_setting',{action:a[0]});return 0;});
Interceptor.attach(moduleExport('user32.dll','CreateWindowExA'),{onEnter(args){args[0]=ptr(args[0].toUInt32()&~8);args[3]=ptr(args[3].toUInt32()&~0x10000000);}});
hook('user32.dll','SetWindowsHookExA','pointer',['int','pointer','pointer','uint'],(_o,a)=>{log('blocked_windows_hook',{id:a[0]});return ptr(0);});
const dd=moduleExport('ddraw.dll','DirectDrawCreate');
const isLocalWrapper=Process.getModuleByName('ddraw.dll').path.toLowerCase().startsWith(copyPath.toLowerCase());
log('ddraw_module',{path:Process.getModuleByName('ddraw.dll').path,localWrapper:isLocalWrapper});
Interceptor.attach(dd,{
  onEnter(args){this.out=args[1];},
  onLeave(result){
    log('directdraw_create',{result:result.toString()});
    if(result.toInt32()!==0)return;
    if(isLocalWrapper){
      log('local_windowed_ddraw_active');
      const table=this.out.readPointer().readPointer();
      Interceptor.attach(table.add(5*4).readPointer(),{onEnter(args){if(!args[2].isNull())paletteBytes=Array.from(new Uint8Array(args[2].readByteArray(1024)));this.out=args[3];},onLeave(value){
        if(value.toInt32()!==0)return;const entry=this.out.readPointer().readPointer().add(6*4).readPointer();
        if(surfaceHooks.has(entry.toString()))return;surfaceHooks.add(entry.toString());
        Interceptor.attach(entry,{onEnter(args){const start=args[2].toUInt32(),count=args[3].toUInt32();if(paletteBytes&&start+count<=256){const bytes=new Uint8Array(args[4].readByteArray(count*4));for(let i=0;i<bytes.length;i++)paletteBytes[start*4+i]=bytes[i];}}});
      }});
      Interceptor.attach(table.add(6*4).readPointer(),{onEnter(args){this.desc=args[1];this.out=args[2];this.width=this.desc.add(12).readU32();this.height=this.desc.add(8).readU32();},onLeave(value){
        log('surface_create',{width:this.width,height:this.height,result:value.toString(),surface:this.out.readPointer().toString()});
        if(value.toInt32()!==0)return;const surfaceTable=this.out.readPointer().readPointer();
        const lock=surfaceTable.add(25*4).readPointer(),unlock=surfaceTable.add(32*4).readPointer();
        if(surfaceHooks.has(lock.toString()))return;surfaceHooks.add(lock.toString());
        Interceptor.attach(lock,{onEnter(args){this.self=args[0].toString();this.desc=args[2];},onLeave(result){if(result.toInt32()===0){const d=this.desc;lockedSurfaces.set(this.self,{width:d.add(12).readU32(),height:d.add(8).readU32(),pitch:d.add(16).readS32(),bpp:d.add(84).readU32(),pixels:d.add(36).readPointer()});}}});
        Interceptor.attach(unlock,{onEnter(args){
          if(!raceProbe)return;const frame=lockedSurfaces.get(args[0].toString()),tick=ptr(0x4b7ecc).readU32(),group=Math.floor(tick/300);
          if(!frame||frame.width!==640||frame.height!==480||frame.pitch<=0||group<1||group>4||capturedFrames.has(group)||frame.pixels.isNull())return;
          capturedFrames.add(group);send({kind:'native_frame',tick,width:frame.width,height:frame.height,pitch:frame.pitch,bpp:frame.bpp,palette:paletteBytes,source:'task-owned native DirectDraw surface buffer before Unlock'},frame.pixels.readByteArray(frame.pitch*frame.height));
        }});
      }});
      return;
    }
    const object=this.out.readPointer(),vtable=object.readPointer();
    const coop=vtable.add(20*4).readPointer();
    const original=new NativeFunction(coop,'long',['pointer','pointer','uint'],'stdcall');
    const normal=new NativeCallback((self,hwnd,flags)=>{log('directdraw_normal_coop',{requested_flags:flags});return original(self,hwnd,8);},'long',['pointer','pointer','uint'],'stdcall');
    keep.push(normal);Interceptor.replace(coop,normal);
    const mode=new NativeCallback((_self,width,height,bpp)=>{stoppedAtGraphics=true;log('blocked_display_mode',{width,height,bpp});return -2005530516;},'long',['pointer','uint','uint','uint'],'stdcall');
    keep.push(mode);Interceptor.replace(vtable.add(21*4).readPointer(),mode);
  }
});
for(const [address,label] of [[0x448200,'application_initialize'],[0x448490,'startup_probe'],[0x448b90,'registry_load'],[0x448f90,'content_initialize'],[0x4163d0,'race_scheduler'],[0x44b2e0,'simulation_batch'],[0x44b3b0,'simulation_tick']]) {
  Interceptor.attach(ptr(address),{onEnter(){counts[label]=(counts[label]||0)+1;if(counts[label]<3)log('native_entry',{address:'0x'+address.toString(16),label});},onLeave(result){if(counts[label]<3)log('native_leave',{label,result:result.toString()});}});
}
rpc.exports={snapshot(){return {counts,clock:ptr(0x4b7ecc).readU32(),stoppedAtGraphics,threads:Process.enumerateThreads().map(t=>({id:t.id,state:t.state,pc:t.context.pc.toString(),backtrace:Thread.backtrace(t.context,Backtracer.ACCURATE).map(DebugSymbol.fromAddress).map(String)}))};}};
if(raceProbe){
  Interceptor.attach(ptr(0x41df60),{onEnter(){if(this.context.ecx.isNull())log('null_surface',{caller:this.returnAddress.toString(),surfaces:Array.from({length:12},(_,i)=>ptr(0x4753f8+i*4).readPointer().toString())});}});
  const skipMovie=new NativeCallback((name,flags,extra)=>{log('probe_skip_prerace_movie',{name:string(name)});return 1;},'int',['pointer','int','int'],'fastcall');
  keep.push(skipMovie);Interceptor.replace(ptr(0x4023e0),skipMovie);
  const quit=new NativeFunction(moduleExport('user32.dll','PostQuitMessage'),'void',['int'],'stdcall');
  const killTimer=new NativeFunction(moduleExport('user32.dll','KillTimer'),'int',['pointer','uint'],'stdcall');
  let started=false;
  Interceptor.attach(ptr(0x421df0),{onLeave(){
    if(started)return;started=true;
    ptr(0x4753b0).writeU32(2);ptr(0x4b8a11).writeU8(1);ptr(0x4b8a12).writeU8(0);ptr(0x4b8a13).writeU8(0);ptr(0x4b8a14).writeU8(4);ptr(0x4753c8).writeU8(0);ptr(0x476c98).writeU8(0);
    const hwnd=ptr(0x4753dc).readPointer(),cancelled=[];
    for(let id=1;id<=16;id++){if(killTimer(hwnd,id))cancelled.push(id);}
    log('probe_cancel_premenu_timers',{cancelled});
    log('probe_initial_condition',{mode:2,characterSelection:1,level:0,bikeIndex:4,course:1,demoAutopilot:false,joystick:false,menuBypassed:true});
    quit(1);
  }});
  Interceptor.attach(ptr(0x455ea0),{onEnter(args){args[0]=ptr(1996);}});
  let previousInput=-1;
  function inputForTick(tick){
    if(scenario==='brake')return tick<120?0:tick<300?1:tick<600?2:tick<720?0:tick<900?1:2;
    if(scenario==='steering')return tick<120?0:tick<240?1:tick<270?5:tick<330?0x201:tick<360?5:2;
    if(scenario==='combat')return tick<120?0:tick<180?0x20:tick<240?0:tick<300?0x40:tick<360?0:tick<420?0xa0:0;
    if(scenario==='hit'){if(tick<120||tick>=600)return 0;const phase=Math.floor((tick-120)/120);return (tick-120)%120<90?(phase===3?0x40:0x20):0;}
    if(scenario==='steal')return tick>=120&&tick<600?0x20:0;
    if(scenario==='police')return tick<720?1:2;
    return tick<120?0:tick<720?1:2;
  }
  Interceptor.attach(ptr(0x44f800),{onLeave(value){const tick=ptr(0x4b7ecc).readU32(),bits=inputForTick(tick);value.replace(bits);if(bits!==previousInput){previousInput=bits;log('native_input_transition',{tick,bits,scenario});}}});
  Interceptor.attach(ptr(0x403d60),{onEnter(){if(this.context.ecx.equals(ptr(0x4642d8).readPointer()))log('native_fall_call',{tick:ptr(0x4b7ecc).readU32(),type:this.context.esp.add(8).readU32()});}});
  Interceptor.attach(ptr(0x4052c0),{onEnter(){if(this.context.ecx.equals(ptr(0x4642d8).readPointer()))log('native_damage_call',{tick:ptr(0x4b7ecc).readU32(),damage:this.context.edx.toInt32(),secondary:this.context.esp.add(4).readS32(),type:this.context.esp.add(8).readS32()});}});
  let previousAnimation=-1,previousRiderState=-1;
  Interceptor.attach(ptr(0x44b3b0),{onLeave(){
    const tick=ptr(0x4b7ecc).readU32();
    const bike=ptr(0x4642d8).readPointer();if(bike.isNull())return;
    const rider=bike.add(0x2fc).readPointer(),animation=rider.add(0x80).readU8(),riderState=bike.add(0x2f4).readS32();
    if(animation!==previousAnimation||riderState!==previousRiderState){log('native_animation_state',{tick,animation,riderState});previousAnimation=animation;previousRiderState=riderState;}
    if(tick%6!==0||states.length>600)return;
    const state={tick,wallMs:Date.now(),input:ptr(0x4b7ed0).readU32(),longitudinal:bike.add(0x1c).readS32(),lateral:bike.add(0x28).readS32(),height:bike.add(0x20).readS32(),velocity:bike.add(0xec).readS32(),gear:bike.add(0x23c).readS32(),riderState,demoAutopilot:ptr(0x4753c8).readU8(),updateTicks:bike.add(0x18).readU32(),drive:bike.add(0x114).readS32(),steering:bike.add(0x288).readS32(),animation,health:rider.add(0x1e0).readPointer().add(0x3c).readS32()};
    states.push(state);log('native_state',state);
  }});
}
log('guards_ready',{source_base:Process.mainModule.base.toString(),copyPath,displayModeChanges:false,registryMode:'virtual game key; writes blocked',network:false});
