"""Additional validated internal counts; interpret structure separately from semantics."""
from audit_assets import *

def animation(d):
    assert d[:4]==b'NARR'
    offsets=struct.unpack_from('<4I',d,4)
    assert offsets[0]==20 and list(offsets)==sorted(offsets)
    fd,ah,ccb,pal=offsets
    assert d[fd:fd+4]==b'DFRR' and d[ah:ah+4]==b'MINA'
    size=u32(d,fd+4); assert size>=8 and (size-8)%28==0 and fd+size==ah
    n=(size-8)//28; assert u32(d,ah+16)==n
    frames=[]
    for i in range(n):
        cp,pp,mapoff,x,y,w,h=struct.unpack_from('<7I',d,fd+8+i*28)
        assert cp<len(d) and pp<len(d) and mapoff<len(d)
        tag=d[pp:pp+4]
        assert tag in (b'DPRR',b'TADP'),(pp,tag)
        plen=u32(d,pp+4);assert pp+plen<=len(d)
        frames.append({'index':i,'ccb_data_offset':cp,'pixel_chunk_offset':pp,'pixel_chunk_size':plen,'pixel_chunk_type':tag[::-1].decode(),'map_offset':mapoff,'x_raw':x,'y_raw':y,'width':w,'height':h,'pixel_chunk_sha256':sha(d[pp:pp+plen])})
    return frames

def mids(d,chunks):
    fmt=next(c for c in chunks if c['path']=='/fmt '); data=next(c for c in chunks if c['path']=='/data')
    division,bufsize,flags=struct.unpack_from('<3I',d,fmt['offset']+8)
    start=data['offset']+8; count=u32(d,start); pos=start+4; blocks=[]
    for i in range(count):
        tick,size=struct.unpack_from('<2I',d,pos);pos+=8
        assert pos+size<=start+data['size']
        stride=8 if flags&1 else 12
        assert size%stride==0
        blocks.append({'index':i,'start_ticks':tick,'bytes':size,'event_records':size//stride})
        pos+=size
    assert pos==start+data['size']
    return {'division':division,'max_buffer':bufsize,'flags':flags,'blocks':blocks,'event_records':sum(x['event_records'] for x in blocks)}

def main():
    root=pathlib.Path(r'C:\Users\Liquid\Downloads\Unity\racing_bois_mod'); out=pathlib.Path('docs/reverse-engineering/assets')
    animations=[]; failures=[]; families=json.loads((out/'families.json').read_text()); fd=(root/'DATA/FAMILIES.RSC').read_bytes(); fam_entries=resources(fd)['entries']
    for fam,e in zip(families,fam_entries):
        payload=fd[e['offset']:e['offset']+e['size']]
        raw=decompress(payload[16:],max_output=u32(payload,0))[0] if fam['compression'] else payload[16:]
        for node in fam['nodes']:
            if node['kind']!='RRAN':continue
            d=raw[node['offset']:node['offset']+node['size']]
            rec={'container':'DATA/FAMILIES.RSC','family_id':fam['id'],'node':node['path'],'offset_in_family':node['offset'],'size':node['size']}
            try: rec['frames']=animation(d);rec['validated']=True
            except Exception as ex:rec['validated']=False;rec['error']=str(ex);failures.append(rec)
            animations.append(rec)
    for p in (root/'DATA').rglob('*'):
        if p.suffix.upper() not in ('.RSC','.CAR') or p.name=='FAMILIES.RSC':continue
        d=p.read_bytes()
        for e in resources(d)['entries']:
            if e['type']!='ANIM':continue
            rec={'container':p.relative_to(root).as_posix(),'resource_id':e['id'],'offset':e['offset'],'size':e['size']}
            try:rec['frames']=animation(d[e['offset']:e['offset']+e['size']]);rec['validated']=True
            except Exception as ex:rec['validated']=False;rec['error']=str(ex);failures.append(rec)
            animations.append(rec)
    mid=[]; banks=[]
    for p in (root/'AUDIO/MUSIC').glob('*'):
        if p.suffix.upper() not in ('.MID','.SBK'):continue
        d=p.read_bytes(); ch=riff_chunks(d)
        if p.suffix.upper()=='.MID':
            try:mid.append({'path':p.relative_to(root).as_posix(),**mids(d,ch)})
            except Exception as e:failures.append({'path':str(p),'error':str(e)})
        else:
            cs={c['path']:c for c in ch};sn=cs['/LIST/sdta/snam'];sh=cs['/LIST/pdta/shdr'];ph=cs['/LIST/pdta/phdr'];ins=cs['/LIST/pdta/inst']
            names=d[sn['offset']+8:sn['offset']+8+sn['size']]
            assert sn['size']%20==0 and sh['size']%16==0 and sn['size']//20==sh['size']//16
            banks.append({'path':p.relative_to(root).as_posix(),'format_version':list(struct.unpack_from('<2H',d,cs['/LIST/INFO/ifil']['offset']+8)), 'sample_names':[names[i:i+20].split(b'\0')[0].decode('latin1') for i in range(0,len(names),20)],'sample_count':len(names)//20,'preset_headers_including_terminal':ph['size']//38,'instrument_headers_including_terminal':ins['size']//22,'sample_pcm_bytes':cs['/LIST/sdta/smpl']['size']})
    summary={'animations':len(animations),'animations_validated':sum(x['validated'] for x in animations),'rrfd_frame_records':sum(len(x.get('frames',[])) for x in animations),'unique_pixel_chunk_hashes':len({f['pixel_chunk_sha256'] for x in animations for f in x.get('frames',[])}),'mids_files_validated':len(mid),'mids_event_records':sum(m['event_records'] for m in mid),'soundfont_sample_records':sum(b['sample_count'] for b in banks),'soundfont_sample_names_unique':len({n for b in banks for n in b['sample_names']}),'failures':failures}
    dump(out/'animations.json',animations);dump(out/'midi_streams.json',mid);dump(out/'sound_banks.json',banks);dump(out/'internals_summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
