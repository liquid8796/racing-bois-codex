"""Full research atlas: FAM/CLGP/RRAN/CANS/FORM, external CAR/RSC, DAT.

Pixel storage and native LOD alias rules are decoded; display uses the source
RGBX palette with index zero shown transparent as a clearly marked preview.
All outputs remain outside Unity Assets; no production asset is created here.
"""
from common import *
from collections import Counter, defaultdict
import html
import re
from PIL import Image, ImageDraw
from inspect_mips import parse_mip_body


def decode_cans(data):
    chunks = []
    offset = 0
    while offset < len(data):
        assert offset + 8 <= len(data)
        size = u32(data, offset+4)
        assert size >= 8 and offset+size <= len(data)
        raw = data[offset:offset+size]
        tag = raw[:4][::-1].decode('ascii')
        record = {'tag': tag, 'offset': offset, 'bytes': size, 'raw_hex': raw.hex()}
        if tag == 'CANS':
            version, count = struct.unpack_from('<2I', raw, 8)
            assert version in (1, 2, 3, 4)
            position = 48 if version == 1 else 16
            sequences = []
            for i in range(count):
                sid, n, rate, flags = struct.unpack_from('<4I', raw, position)
                assert position+16+n*28 <= size
                frames = []
                for j in range(n):
                    base = position + 16 + j * 28
                    words = list(struct.unpack_from('<7i', raw, base))
                    frames.append({'index': j, 'offset': base,
                                   'frame_reference_1based': struct.unpack_from('<h', raw, base+2)[0],
                                   'raw_i32': words})
                sequences.append({'index': i, 'id': sid, 'offset': position,
                                  'frame_count': n, 'rate_raw': rate,
                                  'runtime_rate_div20': int(signed(rate)/20),
                                  'runtime_duration_signed_byte': ((int(signed(rate)/20)+128)%256)-128,
                                  'nominal_duration_seconds_60hz': (((int(signed(rate)/20)+128)%256)-128)/60,
                                  'timing_evidence': '0x40b567 stores rate/20 byte;0x43aecb reads signedbyte and0x43aecf adds60Hz clock; P01 logic exact-byte fixtures',
                                  'flags_raw': flags, 'frames': frames})
                position += 16+n*28
            assert position == size
            record.update(version=version, sequence_count=count, sequences=sequences)
        elif tag == 'SRCN':
            n = u32(raw,8)
            assert size == 12+32*n
            record['source_names'] = [raw[12+32*i:44+32*i].split(b'\0')[0].decode('latin1') for i in range(n)]
        elif tag == 'ATTD':
            assert (size-8) % 32 == 0
            record['attribute_labels'] = [raw[i:i+32].split(b'\0')[0].decode('latin1') for i in range(8,size,32)]
        elif tag == 'ACTN':
            n = u32(raw, 8)
            stride = (size-12)//n if n else 16
            assert stride in (12,16) and size == 12+stride*n
            record['record_stride'] = stride
            record['actions'] = [{'index': i, 'raw_hex': raw[12+stride*i:12+stride*(i+1)].hex(),
                                  'id_fourcc': raw[12+stride*i:16+stride*i][::-1].decode('latin1')}
                                 for i in range(n)]
        elif tag == 'ATTR':
            n, position, attributes = u32(raw,8), 12, []
            for _ in range(n):
                count = u32(raw, position)
                assert position + 4 + count*4 <= size
                attributes.append(list(struct.unpack_from('<'+'I'*count, raw, position+4)))
                position += 4+count*4
            assert position == size
            record['attributes_per_sequence'] = attributes
        elif tag == 'HOLE':
            n = u32(raw,8)
            assert size == 12+4*n
            record['values_raw'] = list(struct.unpack_from('<'+'I'*n,raw,12))
        chunks.append(record)
        offset += size
    assert offset == len(data)
    return chunks


class Atlas:
    def __init__(self):
        raw = (SOURCE/'DATA/PALETTE.RAW').read_bytes()
        self.palette = [c for i in range(256) for c in raw[i*4:i*4+3]]
        self.rows = []
        self.mips = {}
        self.groups = defaultdict(list)
        self.animations = []
        self.cans = []
        self.forms = []
        self.failures = []
        (OUTPUT/'pixels').mkdir(parents=True,exist_ok=True)
        (OUTPUT/'sheets').mkdir(parents=True,exist_ok=True)

    def indexed(self, pixels, width, height):
        image = Image.frombytes('P', (width,height), pixels)
        image.putpalette(self.palette)
        image.info['transparency'] = 0
        return image

    def mip(self, chunk, identity, group):
        assert chunk[:4] in (b'TADP', b'DPRR')
        assert u32(chunk,4) == len(chunk)
        assert u32(chunk,8) == 12345678
        key = digest(chunk)
        if key not in self.mips:
            body = chunk[36:]
            record = parse_mip_body(body)
            for level in record['levels']:
                n = level['width']*level['height']
                start = level['offset_in_body']
                pixels = body[start:start+n]
                assert len(pixels) == n
                # Decode every level, including the smallest level. Saving every
                # image would inflate the catalog with mip duplicates.
                decoded = self.indexed(pixels,level['width'],level['height'])
                assert decoded.size == (level['width'],level['height'])
                level['sha256_pixels'] = digest(pixels)
                if level['level'] == 0:
                    filename = key + '.png'
                    decoded.save(OUTPUT/'pixels'/filename)
                    record['preview'] = 'pixels/' + filename
            record['chunk_sha256'] = key
            record['tag'] = chunk[:4][::-1].decode()
            record['mip_header_hex'] = chunk[8:36].hex()
            record['flags_raw'] = u32(chunk,20)
            self.mips[key] = record
        record = self.mips[key]
        self.groups[group].append((identity,record['preview']))
        self.rows.append({'identity':identity,'group':group,'chunk_sha256':key,
                          'preview':record['preview'],'kind':'indexed_mip_base'})
        return key

    def animation(self, data, identity, group):
        assert data[:4] == b'NARR'
        fd, anim, ccb, plut = struct.unpack_from('<4I',data,4)
        assert fd == 20 and data[fd:fd+4] == b'DFRR'
        n = (u32(data,fd+4)-8)//28
        assert fd+u32(data,fd+4) == anim and u32(data,anim+16) == n
        frames = []
        for i in range(n):
            raw = list(struct.unpack_from('<7I',data,fd+8+i*28))
            cp, pp, palette, auxiliary, runtime_raw, w,h = raw
            assert cp < len(data) and pp+12 <= len(data)
            assert not palette or palette < len(data)
            assert 0 <= auxiliary <= 0xffffffff
            size = u32(data,pp+4)
            assert pp+size <= len(data)
            chunk = data[pp:pp+size]
            rec = {'index':i,'ccb_offset':cp,'pixel_offset':pp,'pixel_bytes':size,
                   'palette_or_attributes_offset':palette,'auxiliary_pointer_offset':auxiliary,
                   'runtime_raw_slot16':runtime_raw,'width_low16':w&65535,'height_low16':h&65535,
                   'raw_u32':raw,'pixel_marker':u32(chunk,8)}
            if u32(chunk,8) == 12345678:
                rec['mip_key'] = self.mip(chunk,identity+f'/frame{i}',group)
                rec['status'] = 'PIXELS_DECODED'
            elif size == 12:
                rec['status'] = 'LEGACY_12_BYTE_LOD_RECORD'
            else:
                rec['status'] = 'UNSUPPORTED_PIXEL_ENCODING'
                self.failures.append({'identity':identity,'frame':i,'bytes':size})
            frames.append(rec)
        # Loader 0x44a29b..0x44a341 shares the full mip pixel buffer with the
        # two smaller RRFD records in each view triple. Do not invent pixels
        # from the twelve-byte legacy records.
        if frames and frames[0].get('mip_key'):
            primary = self.mips[frames[0]['mip_key']]
            if primary['flags_raw'] & 1 and n in (3,12):
                for i in range(0,n,3):
                    assert frames[i].get('mip_key')
                    for j in (1,2):
                        frames[i+j]['runtime_alias_frame'] = i
                        frames[i+j]['mip_key'] = frames[i]['mip_key']
                        frames[i+j]['status'] = 'NATIVE_LOD_ALIAS_RESOLVED'
        elif n == 3 and frames[2].get('mip_key'):
            for i in (0,1):
                frames[i]['runtime_alias_frame'] = 2
                frames[i]['mip_key'] = frames[2]['mip_key']
                frames[i]['status'] = 'NATIVE_LOD_ALIAS_RESOLVED'
        self.animations.append({'identity':identity,'group':group,'frames':frames,
                                'anim_chunk_raw_hex':data[anim:ccb].hex(),
                                'frame_count':n,'status':'STRUCTURE_AND_PIXEL_STORAGE_DECODED'})

    def family(self, entry, data, nodes):
        group = f'family_{entry["id"]:03d}'
        if len(nodes)==1 and nodes[0]['kind']=='EMPTY':
            return
        for node in nodes:
            chunk = data[node['offset']:node['offset']+node['size']]
            identity = group+'/'+node['path']
            kind = node['kind']
            if kind == 'CLGP':
                header, pointer = u32(chunk,4), u32(chunk,28)
                positions = [u32(chunk,p) for p in range(pointer,header,4)] if pointer<header else [pointer]
                for i,p in enumerate(positions):
                    size = u32(chunk,p+4)
                    assert p+size <= len(chunk)
                    self.mip(chunk[p:p+size],identity+f'/texture{i}',group)
            elif kind == 'RRAN':
                self.animation(chunk,identity,group)
            elif kind == 'CANS':
                self.cans.append({'identity':identity,'group':group,'chunks':decode_cans(chunk)})
            elif kind == 'FORM':
                assert len(chunk)==12 and u32(chunk,4)==12
                self.forms.append({'identity':identity,'raw_hex':chunk.hex(),
                                   'payload_u32_le':u32(chunk,8),'payload_u32_be':int.from_bytes(chunk[8:12],'big'),
                                   'meaning':'opaque FORM metadata; integer interpretation is not proven'})

    def other_containers(self):
        for path in sorted((SOURCE/'DATA').rglob('*')):
            if path.suffix.upper() not in ('.RSC','.CAR') or path.name=='FAMILIES.RSC':
                continue
            data=path.read_bytes()
            group='external_'+path.stem
            for e in resources(data)['entries']:
                identity=path.relative_to(SOURCE).as_posix()+f'/{e["type"].strip()}/{e["id"]}'
                chunk=data[e['offset']:e['offset']+e['size']]
                if e['type']=='ANIM':
                    self.animation(chunk,identity,group)
                elif e['type']=='CANS':
                    self.cans.append({'identity':identity,'group':group,'chunks':decode_cans(chunk)})
                elif e['type']=='CEL ':
                    # Walk the complete CCB/PLUT/PDAT stream without assuming
                    # each resource is a single image record.
                    p=0
                    while p<len(chunk):
                        assert p+8<=len(chunk)
                        size=u32(chunk,p+4)
                        assert size>=8 and p+size<=len(chunk)
                        if chunk[p:p+4] in (b'TADP',b'DPRR'):
                            if size>=12 and u32(chunk,p+8)==12345678:
                                self.mip(chunk[p:p+size],identity+f'/pixel@{p}',group)
                            else:
                                self.rows.append({'identity':identity,'group':group,'kind':'legacy_cel',
                                                  'pixel_offset':p,'pixel_bytes':size,'status':'NON_PC_MIP_RECORD'})
                        p+=size

    def dat(self):
        for path in sorted((SOURCE/'DATA/BIKERS').glob('*.DAT')):
            data=path.read_bytes()
            for frame in dat_frames(data):
                if not frame['pixel_bytes']:
                    continue
                w,h=frame['width'],frame['height']
                start=frame['offset']+2
                pixels=data[start:start+w*h]
                name='dat_'+frame['sha256']+f'_{w}x{h}.png'
                self.indexed(pixels,w,h).save(OUTPUT/'pixels'/name)
                group='biker_'+path.stem
                identity=f'{path.stem}/{frame["index"]}'
                preview='pixels/'+name
                self.groups[group].append((identity,preview))
                self.rows.append({'identity':identity,'group':group,'preview':preview,'kind':'dat_frame',**frame})

    def save(self):
        catalogs=[]
        for group,items in sorted(self.groups.items()):
            # All records are represented, even when source bytes are shared.
            pages=[]
            for page,start in enumerate(range(0,len(items),64)):
                batch=items[start:start+64]
                columns=8; cellw=150; cellh=145
                sheet=Image.new('RGB',(columns*cellw,((len(batch)+columns-1)//columns)*cellh),(29,32,40))
                draw=ImageDraw.Draw(sheet)
                for i,(label,path) in enumerate(batch):
                    image=Image.open(OUTPUT/path).convert('RGBA')
                    image.thumbnail((cellw-10,110),Image.Resampling.NEAREST)
                    x=(i%columns)*cellw; y=(i//columns)*cellh
                    sheet.paste(image,(x+(cellw-image.width)//2,y+5),image)
                    draw.text((x+4,y+116),label.split('/')[-2]+'/'+label.split('/')[-1],fill=(235,235,235))
                target=f'sheets/{group}_{page:02d}.jpg'
                sheet.save(OUTPUT/target,quality=88)
                pages.append(target)
            names=sorted({name for c in self.cans if c['group']==group for chunk in c['chunks'] for name in chunk.get('source_names',[])})
            catalogs.append({'group':group,'records':len(items),'pages':pages,'source_animation_names':names})
        summary={'family_groups':sum(c['group'].startswith('family_') for c in catalogs),
                 'atlas_groups':len(catalogs),'indexed_mip_records':sum(r['kind']=='indexed_mip_base' for r in self.rows),
                 'unique_mip_buffers':len(self.mips),'decoded_unique_mip_levels':sum(len(r['levels']) for r in self.mips.values()),
                 'rran_records':len(self.animations),'rrfd_records':sum(a['frame_count'] for a in self.animations),
                 'rrfd_status_counts':dict(Counter(f['status'] for a in self.animations for f in a['frames'])),
                 'cans_records':len(self.cans),'cans_sequences':sum(c['sequence_count'] for a in self.cans for c in a['chunks'] if c['tag']=='CANS'),
                 'source_animation_names':sorted({n for a in self.cans for c in a['chunks'] for n in c.get('source_names',[])}),
                 'form_records':len(self.forms),'dat_nonempty_frames':sum(r['kind']=='dat_frame' for r in self.rows),
                 'contact_pages':sum(len(c['pages']) for c in catalogs),'failures':self.failures}
        save_json(OUTPUT/'sprite_summary.json',summary)
        save_json(OUTPUT/'pixel_catalog.json',self.rows)
        save_json(OUTPUT/'mip_buffers.json',list(self.mips.values()))
        save_json(OUTPUT/'animation_catalog.json',self.animations)
        save_json(OUTPUT/'cans_decoded.json',self.cans)
        save_json(OUTPUT/'forms_decoded.json',self.forms)
        save_json(OUTPUT/'atlas_groups.json',catalogs)
        body=['<!doctype html><meta charset="utf-8"><title>Racing Bois - reference atlas</title>',
              '<style>body{background:#151820;color:#e9e9ea;font:16px system-ui;max-width:1250px;margin:40px auto}img{max-width:100%}a{color:#8bdbd0}section{border-top:1px solid #4a5261;padding:24px 0}input{padding:14px;width:80%}small{color:#bdc3cb}</style>',
              '<h1>Racing Bois · Research reference atlas</h1><p>Original assets are references only. Every production asset must be authored anew.</p>',
              '<p>All decoded pixel buffers use source RGBX palette; index 0 is transparent in these previews. Runtime recoloring, draw ordering, clipping and lighting are not certified by this atlas.</p>',
              '<input id="search" placeholder="Filter by family / source animation name" oninput="document.querySelectorAll(\'section\').forEach(x=>x.hidden=!x.dataset.key.includes(this.value.toLowerCase()))">']
        for c in catalogs:
            label=c['group']+' '+', '.join(c['source_animation_names'])
            body.append(f'<section data-key="{html.escape(label.lower())}"><h2>{html.escape(label)}</h2><small>{c["records"]} decoded record views; duplicates are not separate concepts.</small>')
            body.extend(f'<p><a href="{p}"><img loading="lazy" src="{p}" alt="{html.escape(label)}"></a></p>' for p in c['pages'])
            body.append('</section>')
        (OUTPUT/'atlas.html').write_text('\n'.join(body),encoding='utf-8')
        print(json.dumps(summary,indent=2))


def main():
    atlas=Atlas()
    for entry,data,nodes in families():
        atlas.family(entry,data,nodes)
    atlas.other_containers()
    atlas.dat()
    atlas.save()

if __name__=='__main__':
    main()


