"""Read-only inventory and validated legacy container parsing for Racing Bois.
Outputs research evidence only; never loads or executes source EXE/DLL files.
Usage: python tools/reverse-engineering/assets/audit_assets.py [--source PATH] [--output PATH]
Requires Pillow; ffprobe on PATH gives audiovisual stream metadata.
"""
from __future__ import annotations
import argparse, collections, concurrent.futures, csv, hashlib, io, json, pathlib
import struct, subprocess, sys, zlib
from PIL import Image, ImageDraw
from dcl import decompress

def u32(d, o): return struct.unpack_from('<I', d, o)[0]
def sha(d): return hashlib.sha256(d).hexdigest()
def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
def csvdump(path, rows):
    if not rows: return
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w=csv.DictWriter(f, list(dict.fromkeys(k for row in rows for k in row)))
        w.writeheader(); w.writerows(rows)
def kind(d):
    if d[:3] == b'\xff\xd8\xff': return 'JPEG'
    if d[:2] == b'BM': return 'BMP'
    if d[:4] == b'RIFF': return 'RIFF/' + d[8:12].decode('ascii', 'replace')
    if d[:4] == b'CRSR': return 'CRSR'
    if d[:4] == b'\x00\x01\x00\x00': return 'TrueType'
    if d[:2] == b'MZ': return 'PE/MZ'
    if len(d)>=8 and d[4:8] == b'\xad\xde\xfe\xca': return 'RRS-save'
    return 'unidentified/headerless'

def resources(data):
    assert data[:4] == b'CRSR'
    off = u32(data,16); capacity = u32(data,20)
    assert data[off:off+4] == b'LBTR'
    count = u32(data,off+8)
    assert off+16+count*32 <= len(data)
    out=[]
    for i in range(count):
        t, rid, start, size, *rest = struct.unpack_from('<4s7I',data,off+16+i*32)
        assert start >= off+16+count*32 and start+size <= len(data)
        out.append({'index':i,'type':t[::-1].decode('ascii'),'id':rid,
                    'offset':start,'size':size,'unknown4':rest,'sha256':sha(data[start:start+size])})
    spans=sorted((e['offset'],e['offset']+e['size']) for e in out)
    assert all(a[1] <= b[0] for a,b in zip(spans,spans[1:]))
    return {'version':u32(data,8),'table_offset':off,'table_capacity_bytes':capacity,
            'entry_count':count,'table_end':off+16+count*32,'entries':out}

def family_tree(d, start=0, end=None, trail='root', depth=0):
    """Validate nested relative-offset arrays and typed leaf records.
    Leafs are records, not assumed unique models or rendered frames.
    """
    if end is None: end=len(d)
    if depth>8 or start+8>end: raise ValueError('Bad FAM node bounds')
    count=u32(d,start)
    if count > 4096: return [{'path':trail,'offset':start,'size':end-start,'kind':d[start:start+4][::-1].decode('ascii','replace')}]
    header=4+count*4
    if count==0:
        assert end-start==8 and u32(d,start+4)==8
        return [{'path':trail,'offset':start,'size':8,'kind':'EMPTY'}]
    assert start+header<=end
    offsets=[u32(d,start+4+i*4) for i in range(count)]
    assert offsets[0]==header and offsets==sorted(set(offsets)) and offsets[-1]<end-start
    out=[]
    for i,(a,b) in enumerate(zip(offsets, offsets[1:]+[end-start])):
        out.extend(family_tree(d,start+a,start+b,trail+'/'+str(i),depth+1))
    return out

def dat_frames(d):
    pos=0; out=[]
    while pos<len(d):
        assert pos+2<=len(d)
        w,h=d[pos:pos+2]; n=w*h
        assert (w==0)==(h==0) and pos+2+n<=len(d)
        out.append({'index':len(out),'offset':pos,'width':w,'height':h,'pixel_bytes':n,
                    'sha256':sha(d[pos+2:pos+2+n]) if n else ''})
        pos+=2+n
    assert pos==len(d)
    return out

def riff_chunks(d,start=12,end=None,parent=''):
    if end is None: end=min(len(d),u32(d,4)+8)
    pos=start; out=[]
    while pos+8<=end:
        tag=d[pos:pos+4].decode('ascii','replace'); n=u32(d,pos+4)
        assert pos+8+n<=end, (tag,pos,n,end)
        path=parent+'/'+tag
        out.append({'path':path,'offset':pos,'size':n})
        if tag=='LIST' and n>=4:
            out.extend(riff_chunks(d,pos+12,pos+8+n,path+'/'+d[pos+8:pos+12].decode('ascii','replace')))
        pos+=8+n+(n&1)
    assert pos in (end,end+1), (pos,end)
    return out

def font_metadata(d):
    count=struct.unpack_from('>H',d,4)[0]; tables={}
    for i in range(count):
        tag,check,off,size=struct.unpack_from('>4sIII',d,12+16*i)
        assert off+size<=len(d)
        tables[tag.decode()]={'offset':off,'size':size}
    names=[]
    if 'name' in tables:
        base=tables['name']['offset']; fmt,n,store=struct.unpack_from('>HHH',d,base)
        for i in range(n):
            plat,enc,lang,nid,length,off=struct.unpack_from('>6H',d,base+6+12*i)
            raw=d[base+store+off:base+store+off+length]
            text=raw.decode('utf-16-be' if plat in (0,3) else 'latin1',errors='replace')
            if nid in (1,2,4,6): names.append({'name_id':nid,'platform':plat,'text':text})
    glyphs=struct.unpack_from('>H',d,tables['maxp']['offset']+4)[0] if 'maxp' in tables else None
    return {'table_count':count,'glyph_count':glyphs,'names':names,'tables':tables}

def probe(path):
    try:
        p=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],capture_output=True,text=True,timeout=45)
        r=json.loads(p.stdout or '{}'); r['returncode']=p.returncode
        if p.stderr: r['error']=p.stderr.strip()
        return r
    except Exception as e: return {'error':str(e)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',default=r'C:\Users\Liquid\Downloads\Unity\racing_bois_mod'); ap.add_argument('--output',default='docs/reverse-engineering/assets'); a=ap.parse_args()
    root=pathlib.Path(a.source).resolve(); out=pathlib.Path(a.output).resolve()
    assert out!=root and root not in out.parents, 'Output must not modify source tree'
    out.mkdir(parents=True,exist_ok=True); (out/'samples').mkdir(exist_ok=True)
    files=sorted(p for p in root.rglob('*') if p.is_file()); inventory=[]; archives=[]; entries=[]; families=[]; frame_rows=[]; images=[]; riffs=[]; fonts=[]; bikes=[]; failures=[]; sample_images=[]
    pal=(root/'DATA/PALETTE.RAW').read_bytes(); palette=[c for i in range(256) for c in pal[i*4:i*4+3]]
    media=[]
    for p in files:
        d=p.read_bytes(); rel=p.relative_to(root).as_posix(); fmt=kind(d)
        inventory.append({'path':rel,'bytes':len(d),'extension':p.suffix.upper() or '(none)','magic_type':fmt,'magic_hex':d[:16].hex(),'sha256':sha(d),'category':rel.split('/')[0] if '/' in rel else 'ROOT'})
        try:
            if fmt=='CRSR':
                parsed=resources(d); archives.append({'path':rel,**{k:v for k,v in parsed.items() if k!='entries'}})
                for e in parsed['entries']:
                    entries.append({'path':rel,**e}); payload=d[e['offset']:e['offset']+e['size']]
                    if e['type']=='SPEC': bikes.append({'path':rel,'id':e['id'],'offset':e['offset'],'size':e['size'],'i32':list(struct.unpack('<'+'i'*(len(payload)//4),payload))})
                    if e['type']=='FAM ':
                        raw_size,stored,crc,flag=struct.unpack_from('<4I',payload)
                        assert stored+16==len(payload)
                        if flag==1:
                            raw,consumed=decompress(payload[16:],max_output=raw_size)
                            assert consumed==stored and len(raw)==raw_size and zlib.crc32(raw)==crc
                        elif flag==0:
                            raw=payload[16:]; consumed=len(raw)
                            assert len(raw)==raw_size
                        else: raise ValueError('Unknown FAM compression flag')
                        rec={'id':e['id'],'source_offset':e['offset'],'stored_bytes':stored,'raw_bytes':len(raw),'compression':flag,'crc32_expected':f'{crc:08x}','crc32_actual':f'{zlib.crc32(raw):08x}','sha256_raw':sha(raw)}
                        try: rec['nodes']=family_tree(raw); rec['tree_validated']=True
                        except Exception as ex: rec['tree_validated']=False; rec['tree_error']=str(ex)
                        families.append(rec)
                        if e['id'] in (1,7,25): (out/'samples'/f'family_{e["id"]:03}.bin').write_bytes(raw)
            if p.suffix.upper()=='.DAT' and 'BIKERS' in p.parts:
                frames=dat_frames(d)
                frame_rows.extend({'path':rel,**f} for f in frames)
                for f in [x for x in frames if x['pixel_bytes']][:8]:
                    start=f['offset']+2; im=Image.frombytes('P',(f['width'],f['height']),d[start:start+f['pixel_bytes']]); im.putpalette(palette)
                    name=f'{p.stem}_{f["index"]:03}.png'; im.save(out/'samples'/name); sample_images.append((name,im.convert('RGB')))
            if fmt in ('JPEG','BMP'):
                with Image.open(io.BytesIO(d)) as im:
                    im.load(); images.append({'path':rel,'format':im.format,'width':im.width,'height':im.height,'mode':im.mode,'fully_decoded':True})
            if fmt=='TrueType': fonts.append({'path':rel,**font_metadata(d)})
            if fmt.startswith('RIFF/'):
                c=riff_chunks(d); riffs.append({'path':rel,'form':fmt[5:],'declared_bytes':u32(d,4)+8,'file_bytes':len(d),'chunks':c})
                if fmt in ('RIFF/WAVE','RIFF/AVI '): media.append(p)
        except Exception as e: failures.append({'path':rel,'error':type(e).__name__+': '+str(e)})
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        metadata=list(pool.map(probe,media))
    media_results=[{'path':p.relative_to(root).as_posix(),**m} for p,m in zip(media,metadata)]
    grouping={}
    for f in inventory: grouping.setdefault(f['sha256'],[]).append(f['path'])
    duplicates=[{'sha256':h,'paths':paths,'copies':len(paths)} for h,paths in grouping.items() if len(paths)>1]
    def totals(key):
        groups={}
        for f in inventory:
            g=groups.setdefault(f[key],{'files':0,'bytes':0}); g['files']+=1;g['bytes']+=f['bytes']
        return groups
    vids=[m for m in media_results if m['path'].upper().endswith('.AVI')]
    wavs=[m for m in media_results if m not in vids]
    summary={'source':str(root),'file_count':len(files),'total_bytes':sum(f['bytes'] for f in inventory),'unique_hashes':len(grouping),'duplicate_groups':len(duplicates),'by_category':totals('category'),'by_extension':totals('extension'),'by_magic':totals('magic_type'),'crsr_archives':len(archives),'crsr_entries':len(entries),'crsr_entries_by_type':dict(collections.Counter(e['type'] for e in entries)),'family_entries':len(families),'family_compressed_entries':sum(f['compression']==1 for f in families),'family_tree_validated':sum(f['tree_validated'] for f in families),'family_leaf_types':dict(collections.Counter(n['kind'] for f in families for n in f.get('nodes',[]))),'dat_frame_slots':len(frame_rows),'dat_nonempty_frames':sum(f['pixel_bytes']>0 for f in frame_rows),'dat_unique_pixel_hashes':len({f['sha256'] for f in frame_rows if f['sha256']}),'image_count_fully_decoded':len(images),'font_count':len(fonts),'video_files':len(vids),'video_reported_frames':sum(int(s.get('nb_frames',0)) for m in vids for s in m.get('streams',[]) if s.get('codec_type')=='video'),'video_duration_seconds':sum(float(m.get('format',{}).get('duration',0)) for m in vids),'wave_files':len(wavs),'wave_duration_seconds':sum(float(m.get('format',{}).get('duration',0)) for m in wavs),'failures':failures}
    dump(out/'summary.json',summary); dump(out/'source_manifest.json',inventory); csvdump(out/'source_manifest.csv',inventory); dump(out/'duplicates.json',duplicates); dump(out/'resource_archives.json',archives); csvdump(out/'resource_entries.csv',entries); dump(out/'resource_entries.json',entries); dump(out/'families.json',families); csvdump(out/'biker_frames.csv',frame_rows); dump(out/'images.json',images);dump(out/'fonts.json',fonts);dump(out/'riff_chunks.json',riffs);dump(out/'media_metadata.json',media_results);dump(out/'bikespec_raw.json',bikes)
    cellw,cellh=190,175; sheet=Image.new('RGB',(cellw*8,cellh*((len(sample_images)+7)//8)),(32,32,32));draw=ImageDraw.Draw(sheet)
    for i,(name,im) in enumerate(sample_images):
        x=(i%8)*cellw;y=(i//8)*cellh;im.thumbnail((cellw-10,cellh-25));sheet.paste(im,(x+5,y+20));draw.text((x+5,y+3),name,fill='white')
    sheet.save(out/'samples/biker_contact_sheet.png')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
