"""Independently verify an actual preview's bytes and real observation chronology.

No native run is performed and no visual/comfort/performance acceptance is inferred.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import math
import struct
import zlib
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def require(value,message):
    if not value:raise ValueError(message)
def finite(value):
    if isinstance(value,float):return math.isfinite(value)
    if isinstance(value,dict):return all(finite(v) for v in value.values())
    if isinstance(value,list):return all(finite(v) for v in value)
    return True
def contained(root,name):
    require(isinstance(name,str) and name and not Path(name).is_absolute() and '..' not in Path(name).parts,'Unsafe receipt path')
    path=(root/name).resolve();require(path.is_relative_to(root.resolve()),'Receipt escaped output')
    return path
def png_varied(data):
    require(data[:8]==b'\x89PNG\r\n\x1a\n','PNG signature mismatch')
    pos=8;compressed=[];width=height=0;ended=False
    while pos<len(data):
        require(pos+12<=len(data),'Truncated PNG chunk');length=struct.unpack_from('>I',data,pos)[0];kind=data[pos+4:pos+8]
        require(length<=16*1024*1024 and pos+length+12<=len(data),'Invalid PNG chunk length')
        payload=data[pos+8:pos+8+length];crc=struct.unpack_from('>I',data,pos+8+length)[0]
        require(zlib.crc32(kind+payload)&0xffffffff==crc,'PNG CRC mismatch')
        if kind==b'IHDR':
            width,height,depth,color,compression,filter_method,interlace=struct.unpack('>IIBBBBB',payload)
            require((width,height)==(1280,720) and depth==8 and color in {2,6} and compression==filter_method==interlace==0,'Unexpected PNG encoding')
            channels=4 if color==6 else 3
        elif kind==b'IDAT':compressed.append(payload)
        elif kind==b'IEND':ended=True;require(pos+12==len(data),'Trailing PNG data');break
        pos+=length+12
    require(ended and width>0 and compressed,'PNG data incomplete');stride=width*channels
    stream=zlib.decompressobj();raw=stream.decompress(b''.join(compressed),(stride+1)*height+1)
    require(len(raw)==(stride+1)*height and stream.eof and not stream.unused_data,'PNG pixel data mismatch')
    previous=bytearray(stride);first=None;varied=False
    def paeth(a,b,c):
        p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
        return a if pa<=pb and pa<=pc else b if pb<=pc else c
    for y in range(height):
        start=y*(stride+1);f=raw[start];require(f<=4,'Unknown PNG filter');row=bytearray(raw[start+1:start+1+stride])
        for x in range(stride):
            left=row[x-channels] if x>=channels else 0;above=previous[x];upper_left=previous[x-channels] if x>=channels else 0
            if f==1:row[x]=(row[x]+left)&255
            elif f==2:row[x]=(row[x]+above)&255
            elif f==3:row[x]=(row[x]+((left+above)//2))&255
            elif f==4:row[x]=(row[x]+paeth(left,above,upper_left))&255
        if first is None:first=row[:3]
        if any(sum(abs(row[x+k]-first[k]) for k in range(3))>20 for x in range(0,stride,channels*31)):varied=True
        previous=row
    return varied
def require_x64(path):
    data=path.read_bytes();require(len(data)>=64 and data[:2]==b'MZ','Native PE missing')
    pointer=struct.unpack_from('<I',data,60)[0]
    require(pointer>=64 and pointer+26<=len(data) and data[pointer:pointer+4]==b'PE\x00\x00','Invalid PE header')
    require(struct.unpack_from('<H',data,pointer+4)[0]==0x8664 and struct.unpack_from('<H',data,pointer+24)[0]==0x20b,'Native player must be x64 PE32+')
def audit(build_root,output):
    build=json.loads((build_root/'PosePreview.build.json').read_text());binding_path=build_root/'PosePreview.binding.json';binding=json.loads(binding_path.read_text())
    require(build.get('passed') is True and build.get('sourceBindingPassed') is True and build.get('editorStateRestored') is True and build.get('result')=='Succeeded' and build.get('target')=='StandaloneWindows64' and build.get('backend')=='Mono2x','Real successful/restored Unity build required')
    require_x64(build_root/'RacingBoisPosePreview.exe');require_x64(build_root/'UnityPlayer.dll')
    require(build['sourceFingerprint']==binding['sourceFingerprint'],'Build/binding identity mismatch')
    for row in build['playerFiles']:
        path=contained(build_root,row['path']);require(path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],'Player changed since build')
    run=json.loads((output/'run.json').read_text());require(run.get('completed') is True and run.get('status')=='CAPTURED' and run.get('errors')==0,'Native capture incomplete or errored')
    require(run.get('nativeVisualAccepted') is False and run.get('monoDetected') is True and run.get('platform')=='WindowsPlayer','Native scope mismatch')
    require(run['sourceFingerprint']==binding['sourceFingerprint'] and run['bindingSha256']==sha(binding_path) and run['fixtureSha256']==binding['fixtureSha256'] and run['selectionSha256']==binding['selectionSha256'],'Run identity mismatch')
    fixture_path=output/'reconstruction.json';require(sha(fixture_path)==run['fixtureSha256'],'Fixture copy changed')
    fixture=json.loads(fixture_path.read_text());variants=['unfiltered','envelope40']+(['comparison20'] if run['include20'] else [])
    expected={(e['id'],v,s) for e in fixture['episodes'] for v in variants for s in ['before','correction','mid','settled']}
    captures=run['captures'];require(len(captures)==len(expected),'Capture count missing/duplicate')
    actual=set();timing_deviations=[]
    for capture in captures:
        identity=(capture['episode'],capture['variant'],capture['stage']);require(identity not in actual,'Duplicate capture identity');actual.add(identity)
        path=contained(output,capture['file']);data=path.read_bytes()
        require(len(data)==capture['bytes'] and sha(path)==capture['sha256'],'PNG changed')
        require(png_varied(data),'Independently decoded camera frame is uniform')
        require(capture['variedPixels'] is True and finite(capture),'Capture not finite or uniform')
        require(capture['readbackCompletedWallSeconds']>=capture['requestWallSeconds'],'Readback preceded request')
        limits={'before':(-1.01,-.99),'correction':(-.001,.001),'mid':(.15,.25),'settled':(.8,.95)}
        lo,hi=limits[capture['stage']]
        if not lo<=capture['afterSeconds']<=hi:timing_deviations.append({'capture':identity,'afterSeconds':capture['afterSeconds']})
    require(actual==expected,'Capture matrix incomplete')
    sample_path=contained(output,run['samplesFile']);require(sha(sample_path)==run['samplesSha256'],'Raw observations changed')
    samples=[json.loads(line) for line in sample_path.read_text().splitlines() if line]
    require(len(samples)==run['samples'] and 0<len(samples)<=10000,'Sample count invalid')
    previous=-1;frames=set();groups=collections.Counter();missed=0
    for index,row in enumerate(samples):
        require(row['sequence']==index+1 and finite(row),'Sample identity/nonfinite data')
        require(row['wallSeconds']>previous,'Chronology not strictly increasing');previous=row['wallSeconds']
        require(row['unityFrame'] not in frames,'Backfilled/repeated frame observations');frames.add(row['unityFrame'])
        require(row['missedSampleSlots']>=0,'Negative missed-slot count');missed+=row['missedSampleSlots']
        groups[(row['episodeIndex'],row['variant'])]+=1
    require(missed==run['missedSampleSlots'],'Missed-slot summary differs')
    require(set(groups)=={(e['originalIndex'],v) for e in fixture['episodes'] for v in variants},'Observation segments missing')
    require(0<run['wallSeconds']<=102,'Native runtime exceeded bounded window')
    return {'verified':True,'scope':'Build/run/capture bytes and real observation chronology only. Images must be inspected; no native visual/comfort/frame-performance acceptance.',
            'samples':len(samples),'captures':len(captures),'missedSampleSlots':missed,'maximumSampleGapSeconds':run['maximumSampleGapSeconds'],
            'warnings':run['warnings'],'runSha256':sha(output/'run.json'),'sourceFingerprint':run['sourceFingerprint'],
            'visualAccepted':False,'captureTimingComparable':not timing_deviations,'captureTimingDeviations':timing_deviations,
            'segments':[{'episodeIndex':i,'variant':v,'samples':n} for (i,v),n in groups.items()]}
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--receipt',type=Path,required=True);args=parser.parse_args()
    require(not args.receipt.exists(),'Choose a fresh verification receipt');result=audit(args.build_root,args.output)
    args.receipt.parent.mkdir(parents=True,exist_ok=True);args.receipt.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='segments'},indent=2))
if __name__=='__main__':main()
