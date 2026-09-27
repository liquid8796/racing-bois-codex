// Pure JavaScript contract tests with a media stub. This is not browser playback QA.
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

const sourcePath='Assets/RacingBois/Plugins/WebGL/RacingBoisMusic.jslib';
const script=fs.readFileSync(sourcePath,'utf8');
const messages=[], checks=[];
const listeners=new Map();
let created=0;
class MediaStub {
  constructor(){this.listeners=new Map();this.src='';this.currentTime=0;this.duration=300;this.readyState=1;this.playCalls=0;this.pauseCalls=0;this.loads=0;this.rejectNext=null;}
  addEventListener(name,fn){this.listeners.set(name,fn);}
  setAttribute(){}
  removeAttribute(name){if(name==='src')this.src='';}
  pause(){this.pauseCalls++;}
  load(){this.loads++;}
  play(){this.playCalls++;if(this.rejectNext){const error=this.rejectNext;this.rejectNext=null;return Promise.reject(error);}this.listeners.get('playing')?.();return Promise.resolve();}
}
const document={hidden:false,createElement(tag){assert.equal(tag,'audio');created++;return new MediaStub();},
  addEventListener(name,fn){if(!listeners.has(name))listeners.set(name,new Set());listeners.get(name).add(fn);},
  removeEventListener(name,fn){listeners.get(name)?.delete(fn);}};
const library={};
const context=vm.createContext({LibraryManager:{library},mergeInto:(target,values)=>Object.assign(target,values),
  UTF8ToString:value=>value,SendMessage:(receiver,method,payload)=>messages.push({receiver,method,...JSON.parse(payload)}),
  document,location:{origin:'https://localhost:7888',href:'https://localhost:7888/'},navigator:{userActivation:{isActive:false}},URL,Number,Math,JSON});
vm.runInContext(script,context,{filename:sourcePath});context.RBMusic=library.$RBMusic;
const call=(name,...args)=>library[name](...args);
const check=(name,fn)=>{fn();checks.push({name,passed:true});};
const url='https://localhost:7888/Content/music-'+('a'.repeat(64))+'.ogg';
call('RB_MusicInitialize','RacingBoisMusic');
check('one-owned-media-element',()=>{assert.equal(created,1);assert.equal([...listeners.values()].reduce((n,s)=>n+s.size,0),3);});
check('play-defers-without-user-activation',()=>{assert.equal(call('RB_MusicPlay','amber-apex',url,1,.18),1);assert.equal(context.RBMusic.audio.playCalls,0);assert.equal(messages.at(-1).state,'gesture-required');});
check('untrusted-event-does-not-unlock',()=>{context.RBMusic.gesture({isTrusted:false});assert.equal(context.RBMusic.audio.playCalls,0);});
check('trusted-gesture-unlocks-pending-song',()=>{context.RBMusic.gesture({isTrusted:true});assert.equal(context.RBMusic.audio.playCalls,1);assert.equal(messages.at(-1).state,'playing');});
check('different-origin-or-unsafe-url-rejected',()=>{
  for(const bad of [url.replace('localhost','example.org'),url+'?token=bad',url+'#fragment',url.replace('/Content/','/Other/'),
    url.replace('https://','https://user:password@'),url.replace('.ogg','.wav'),url.replace('a'.repeat(64),'short'),url.replace('/Content/','/Content/%2f')])
    assert.equal(call('RB_MusicPlay','bad-test',bad,0,.3),0,bad);
  assert.equal(context.RBMusic.id,'amber-apex');
});
check('identifier-contract-enforced',()=>{assert.equal(call('RB_MusicPlay','../../bad',url,1,.2),0);assert.equal(call('RB_MusicPlay','X'.repeat(65),url,1,.2),0);});
check('replacement-reuses-and-releases-single-element',()=>{const previous=context.RBMusic.audio;call('RB_MusicPlay','safe-passage',url.replace('a'.repeat(64),'b'.repeat(64)),1,.2);assert.equal(context.RBMusic.audio,previous);assert.equal(created,1);assert.ok(previous.pauseCalls>=2);});
check('mix-and-mute-bounded',()=>{call('RB_MusicMix',1,5);assert.equal(context.RBMusic.audio.muted,true);assert.equal(context.RBMusic.audio.volume,1);call('RB_MusicMix',0,NaN);assert.equal(context.RBMusic.audio.volume,0);});
check('pause-resume-is-explicit',()=>{call('RB_MusicPause',1);let count=context.RBMusic.audio.playCalls;context.RBMusic.gesture({isTrusted:true});assert.equal(context.RBMusic.audio.playCalls,count);call('RB_MusicPause',0);assert.equal(context.RBMusic.audio.playCalls,count+1);});
check('hidden-page-suspends-and-visible-page-resumes',()=>{document.hidden=true;context.RBMusic.visibility();const count=context.RBMusic.audio.playCalls;context.RBMusic.gesture({isTrusted:true});assert.equal(context.RBMusic.audio.playCalls,count);document.hidden=false;context.RBMusic.visibility();assert.equal(context.RBMusic.audio.playCalls,count+1);});
check('seek-clamps-to-declared-duration',()=>{call('RB_MusicSeek',900);assert.equal(context.RBMusic.audio.currentTime,299.99);call('RB_MusicSeek',NaN);assert.equal(context.RBMusic.audio.currentTime,0);});
context.RBMusic.audio.rejectNext={name:'NotAllowedError'};context.RBMusic.tryPlay();await new Promise(resolve=>setImmediate(resolve));
check('autoplay-rejection-stays-cosmetic',()=>{assert.equal(context.RBMusic.unlocked,false);assert.equal(messages.at(-1).state,'gesture-required');});
check('stop-releases-url-and-pending-state',()=>{call('RB_MusicStop');assert.equal(context.RBMusic.id,'');assert.equal(context.RBMusic.audio.src,'');assert.equal(context.RBMusic.requested,false);});
check('dispose-removes-document-handlers',()=>{call('RB_MusicDispose','RacingBoisMusic');assert.equal(context.RBMusic.audio,null);assert.equal([...listeners.values()].reduce((n,s)=>n+s.size,0),0);});
const report={passed:true,checks,checkCount:checks.length,source:sourcePath,sourceSha256:crypto.createHash('sha256').update(script).digest('hex'),
  liveBrowserPlaybackVerified:false,scope:'Node VM contract test with media/document stubs; no browser/audio/network acceptance is claimed.'};
fs.writeFileSync('docs/p08/media/music-bridge-unit-validation.json',JSON.stringify(report,null,2)+'\n');
process.stdout.write(JSON.stringify({passed:true,checkCount:checks.length,liveBrowserPlaybackVerified:false})+'\n');
