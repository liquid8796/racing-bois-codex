"""Convert RIFF/MIDS to standard MIDI and fully decode original WAVE media.

Event semantics: Microsoft MIDIEVENT / MIDI Event Types documentation.
Source MIDI banks, media and thumbnails remain reference-only research data.
"""
from common import *
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import subprocess
import wave
from PIL import Image,ImageDraw

def vlq(value):
    assert 0 <= value < 1 << 28
    result=bytearray([value&127]);value>>=7
    while value:
        result.insert(0,(value&127)|128);value>>=7
    return bytes(result)

def mids_to_smf(data):
    assert data[:4]==b'RIFF' and data[8:12]==b'MIDS'
    chunks={x['path']:x for x in riff_chunks(data)}
    division,maxbuf,flags=struct.unpack_from('<3I',data,chunks['/fmt ']['offset']+8)
    assert 0 < division <= 0x7fff and flags in (0,1)
    start=chunks['/data']['offset']+8; end=start+chunks['/data']['size']
    count=u32(data,start);position=start+4
    events=[];blocks=[];total_ticks=0;track=bytearray();types=Counter()
    for i in range(count):
        block_ticks,size=struct.unpack_from('<2I',data,position);position+=8
        assert position+size<=end
        block_end=position+size
        blocks.append({'index':i,'header_ticks_raw':block_ticks,'bytes':size,'cumulative_ticks_before':total_ticks})
        while position<block_end:
            delta=u32(data,position)
            if flags&1:
                event=u32(data,position+4);position+=8
            else:
                stream=u32(data,position+4);event=u32(data,position+8);position+=12
                assert stream == 0 or (stream == 0xffffffff and event >> 24 == 1)
            event_type=event>>24;params=event&0xffffff
            assert not event_type&0x80, 'Long event requires a separately validated encoder'
            types[event_type]+=1;total_ticks+=delta
            if event_type==1:
                assert params>0
                encoded=b'\xff\x51\x03'+params.to_bytes(3,'big')
                normalized={'type':'tempo','microseconds_per_quarter':params}
            elif event_type==0:
                status=params&255
                assert 0x80<=status<0xf0
                length=2 if status>>4 in (0xc,0xd) else 3
                encoded=params.to_bytes(3,'little')[:length]
                assert all(x<128 for x in encoded[1:])
                normalized={'type':'channel','message_hex':encoded.hex()}
            else:
                raise ValueError(f'Unsupported MIDI event {event_type:#x}')
            track.extend(vlq(delta));track.extend(encoded)
            events.append({'delta_ticks':delta,'absolute_ticks':total_ticks,**normalized})
        assert position==block_end
    assert position==end
    track.extend(b'\x00\xff\x2f\x00')
    smf=b'MThd'+struct.pack('>IHHH',6,0,1,division)+b'MTrk'+struct.pack('>I',len(track))+track
    return smf,{'division':division,'stream_flags':flags,'max_buffer':maxbuf,'blocks':blocks,
                'event_count':len(events),'total_ticks':total_ticks,'event_types':dict(types),'events':events}

def audio_decode(path):
    result=subprocess.run(['ffmpeg','-hide_banner','-nostdin','-v','error','-i',str(path),'-map','0:a','-f','null','-'],capture_output=True,text=True,timeout=120)
    assert result.returncode==0 and not result.stderr, (path,result.stderr)
    with wave.open(str(path),'rb') as reader:
        n=reader.getnframes();raw=reader.readframes(n)
        assert len(raw)==n*reader.getnchannels()*reader.getsampwidth()
        return {'path':path.relative_to(SOURCE).as_posix(),'status':'FULL_PCM_DECODE_PASS',
                'frames':n,'channels':reader.getnchannels(),'sample_rate':reader.getframerate(),
                'bytes_per_sample':reader.getsampwidth(),'pcm_sha256':digest(raw),
                'duration_seconds':n/reader.getframerate()}

def video_sheet(metadata):
    path=SOURCE/metadata['path']
    duration=float(metadata['format']['duration'])
    timestamps=[min(.5,duration/6),duration/2,max(0,duration-1)]
    frames=[]
    for index,seconds in enumerate(timestamps):
        dest=OUTPUT/'media'/'video_frames'/(path.stem+f'_{index}.jpg')
        dest.parent.mkdir(parents=True,exist_ok=True)
        result=subprocess.run(['ffmpeg','-hide_banner','-nostdin','-v','error','-ss',str(seconds),'-i',str(path),'-frames:v','1','-q:v','3','-y',str(dest)],capture_output=True,text=True,timeout=60)
        assert result.returncode==0 and dest.exists(), (path,result.stderr)
        frames.append(dest)
    sheet=Image.new('RGB',(960,230),(22,24,30));draw=ImageDraw.Draw(sheet)
    for index,frame in enumerate(frames):
        image=Image.open(frame).convert('RGB');image.thumbnail((320,200))
        sheet.paste(image,(index*320,0));draw.text((index*320+5,205),f'{path.name} {timestamps[index]:.2f}s',fill='white')
    dest=OUTPUT/'media'/(path.stem+'_filmstrip.jpg');sheet.save(dest,quality=88)
    return {'path':metadata['path'],'duration_seconds':duration,'sample_seconds':timestamps,
            'filmstrip':dest.relative_to(OUTPUT).as_posix(),'sampled_only':True}

def reference_catalog(paths):
    strings=json.loads((REPO/'docs/reverse-engineering/logic/RacingBois.exe.strings.json').read_text())
    disasm=(REPO/'docs/reverse-engineering/logic/RacingBois.disassembly.tsv').read_text().splitlines()
    sys.path.insert(0,str(REPO/'tools/reverse-engineering/logic/vendor'))
    import pefile
    pe=pefile.PE(str(SOURCE/'RacingBois.exe'))
    exe=(SOURCE/'RacingBois.exe').read_bytes()
    output=[]
    for path in paths:
        matching=[s for s in strings if s['text'].lower() in (path.stem.lower(),path.name.lower())]
        refs=[]
        for string in matching:
            va=int(string['va'],16)
            direct=[line for line in disasm if f'0x{va:x}' in line.split('\t')[-1]]
            pointers=[];needle=va.to_bytes(4,'little');start=0
            while True:
                found=exe.find(needle,start)
                if found<0:break
                pointers.append(hex(pe.get_rva_from_offset(found)+pe.OPTIONAL_HEADER.ImageBase));start=found+1
            refs.append({'text':string['text'],'string_va':string['va'],'direct_code_references':direct,
                         'raw_pointer_locations':pointers})
        output.append({'path':path.relative_to(SOURCE).as_posix(),'literal_references':refs,
                       'trigger_status':'LITERAL_REFERENCE_ONLY_EVENT_BRANCH_UNPROVEN' if refs else 'NO_EXACT_LITERAL_REFERENCE_FOUND',
                       'remake_policy':'NEWLY_AUTHORED_REPLACEMENT_REQUIRED'})
    return output

def main():
    (OUTPUT/'media/midi').mkdir(parents=True,exist_ok=True)
    midi=[]
    for path in sorted((SOURCE/'AUDIO/MUSIC').glob('*.MID')):
        smf,parsed=mids_to_smf(path.read_bytes())
        dest=OUTPUT/'media/midi'/path.name
        dest.write_bytes(smf)
        save_json(dest.with_suffix('.json'),parsed)
        midi.append({'source':path.relative_to(SOURCE).as_posix(),'smf':dest.relative_to(OUTPUT).as_posix(),
                     'event_count':parsed['event_count'],'ticks':parsed['total_ticks'],'division':parsed['division']})
    audio=[p for p in (SOURCE/'AUDIO').rglob('*') if p.suffix.upper() in ('.WAV','.RRA')]
    with ThreadPoolExecutor(max_workers=4) as pool:
        audio_results=list(pool.map(audio_decode,audio))
    metadata=json.loads((REPO/'docs/reverse-engineering/assets/media_metadata.json').read_text())
    video=[m for m in metadata if m['path'].upper().endswith('.AVI')]
    with ThreadPoolExecutor(max_workers=4) as pool:
        video_results=list(pool.map(video_sheet,video))
    paths=audio+[SOURCE/m['path'] for m in video]
    references=reference_catalog(paths)
    save_json(OUTPUT/'media/midi_conversion.json',midi)
    save_json(OUTPUT/'media/audio_decode.json',audio_results)
    save_json(OUTPUT/'media/video_catalog.json',video_results)
    save_json(OUTPUT/'media/trigger_references.json',references)
    summary={'mids_converted':len(midi),'midi_events':sum(m['event_count'] for m in midi),
             'wave_fully_decoded':len(audio_results),'wave_frames_decoded':sum(m['frames'] for m in audio_results),
             'video_filmstrips':len(video_results),'exact_literal_reference_media':sum(bool(m['literal_references']) for m in references),
             'full_event_trigger_semantics':'OPEN','soundfont_synth_playback':'OPEN'}
    save_json(OUTPUT/'media_summary.json',summary)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    main()

