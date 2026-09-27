import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'../..');
const results=[];
function check(name,run){try{run();results.push({name,passed:true});}catch(error){results.push({name,passed:false,error:error.message});}}
function store(){const values=new Map();return{getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};}
const heap=new Map(),messages=[],listeners=[];let next=1;
const context={LibraryManager:{library:{}},mergeInto:(target,value)=>Object.assign(target,value),
  localStorage:store(),sessionStorage:store(),_malloc:()=>{const p=next++;heap.set(p,'');return p;},_free:p=>heap.delete(p),
  lengthBytesUTF8:s=>Buffer.byteLength(s,'utf8'),UTF8ToString:s=>typeof s==='number'?heap.get(s):s,
  stringToUTF8:(value,p)=>heap.set(p,value),document:{hidden:false,addEventListener:(name,fn)=>listeners.push({name,fn})},
  SendMessage:(...args)=>messages.push(args)};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root,'Assets/RacingBois/Plugins/WebGL/RacingBoisStorage.jslib'),'utf8'),context);
const storage=context.LibraryManager.library;context.RBStorage=storage.$RBStorage;
function read(key,persistent){const p=storage.RB_StorageRead(key,persistent);if(!p)return null;const value=heap.get(p);storage.RB_StorageFree(p);return value;}
check('persistent_profile_and_tab_receipt_are_separate',()=>{
  assert.equal(storage.RB_StorageWrite('same','profile-fixture',1),1);assert.equal(storage.RB_StorageWrite('same','lease-fixture',0),1);
  assert.equal(read('same',1),'profile-fixture');assert.equal(read('same',0),'lease-fixture');storage.RB_StorageRemove('same',0);assert.equal(read('same',0),'');assert.equal(read('same',1),'profile-fixture');
});
check('unicode_roundtrip_and_allocations_released',()=>{storage.RB_StorageWrite('name','Tay đua Nguyễn',1);assert.equal(read('name',1),'Tay đua Nguyễn');assert.equal(heap.size,0);});
check('oversized_storage_record_is_not_deserialized',()=>{context.sessionStorage.setItem('large','x'.repeat(8193));assert.equal(read('large',0),'');});
check('denied_storage_reports_failure_instead_of_empty_success',()=>{
  const original=context.localStorage;context.localStorage={getItem(){throw Error('denied');},setItem(){throw Error('quota');}};
  assert.equal(storage.RB_StorageRead('fixture',1),0);assert.equal(storage.RB_StorageWrite('fixture','value',1),0);context.localStorage=original;
});
check('visibility_callback_uses_latest_receiver_once',()=>{
  storage.RB_RegisterLifecycle('old');storage.RB_RegisterLifecycle('current');assert.equal(listeners.length,1);
  context.document.hidden=true;listeners[0].fn();assert.deepEqual(messages.pop(),['current','OnPageVisibility','hidden']);
  context.document.hidden=false;listeners[0].fn();assert.deepEqual(messages.pop(),['current','OnPageVisibility','visible']);
});
class FakeSocket {constructor(){this.readyState=1;this.bufferedAmount=0;} close(code,reason){this.closed={code,reason};}send(text){this.sent=text;}}
context.WebSocket=FakeSocket;context.HEAPU8={buffer:{byteLength:128*1024*1024}};
vm.runInContext(fs.readFileSync(path.join(root,'Assets/RacingBois/Plugins/WebGL/RacingBoisSocket.jslib'),'utf8'),context);
const socket=context.LibraryManager.library;context.RBState=socket.$RBState;
check('server_session_replaced_close_reason_is_preserved',()=>{
  socket.RB_Connect('receiver','ws://fixture/multiplayer');context.RBState.socket.onclose({code:1008,reason:'session_replaced'});
  assert.deepEqual(messages.pop(),['receiver','OnSocketClosed','session_replaced']);
});
check('oversize_frame_stops_before_unity_message_bridge',()=>{
  socket.RB_Connect('receiver','ws://fixture/multiplayer');const current=context.RBState.socket;current.onmessage({data:'x'.repeat(32769)});
  assert.equal(current.closed.code,1009);assert.deepEqual(messages.pop(),['receiver','OnSocketClosed','Message too large']);assert.equal(context.RBState.socket,null);
});
check('stale_socket_callbacks_cannot_close_replacement',()=>{
  socket.RB_Connect('receiver','ws://fixture/multiplayer');const old=context.RBState.socket;
  socket.RB_Connect('receiver','ws://fixture/multiplayer');const current=context.RBState.socket;const before=messages.length;
  old.onclose({code:1008,reason:'session_replaced'});old.onmessage({data:'stale'});assert.equal(context.RBState.socket,current);assert.equal(messages.length,before);
});
const report={generatedUtc:new Date().toISOString(),passed:results.every(x=>x.passed),tests:results.length,results};
fs.mkdirSync(path.join(root,'docs/p05'),{recursive:true});fs.writeFileSync(path.join(root,'docs/p05/web-bridge-validation.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));if(!report.passed)process.exitCode=1;
