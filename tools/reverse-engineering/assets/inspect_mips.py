"""Check PC mip structures in CLGP PDAT and TEMPLATE.MIP; semantic use is pending."""
from audit_assets import *

def parse_mip_body(body):
    zero,w,h,n,fill=struct.unpack_from('<5I',body)
    assert zero==0 and 0<w<=8192 and 0<h<=8192 and 1<=n<=14
    assert 20+n*12<=len(body)
    levels=[]
    for i in range(n):
        mask,stride,off=struct.unpack_from('<IiI',body,20+i*12)
        lw,lh=max(1,w>>i),max(1,h>>i)
        assert mask==lw-1 and stride==-2*lw, ('mip shape',i,w,h,n,mask,stride)
        assert 20+n*12<=off and off+lw*lh<=len(body), ('mip bounds',i,off,lw,lh,len(body))
        levels.append({'level':i,'width':lw,'height':lh,'offset_in_body':off,'mask':mask,'negative_double_stride':stride,'candidate_pixel_bytes':lw*lh})
    return {'width':w,'height':h,'fill_raw':fill,'levels':levels}

def main():
    root=pathlib.Path(r'C:\Users\Liquid\Downloads\Unity\racing_bois_mod');out=pathlib.Path('docs/reverse-engineering/assets')
    fams=json.loads((out/'families.json').read_text());d=(root/'DATA/FAMILIES.RSC').read_bytes();entries=resources(d)['entries'];records=[];failures=[]
    for fam,e in zip(fams,entries):
        raw=d[e['offset']+16:e['offset']+e['size']]
        if fam['compression']:raw=decompress(raw,max_output=fam['raw_bytes'])[0]
        for node in fam['nodes']:
            if node['kind']!='CLGP':continue
            x=raw[node['offset']:node['offset']+node['size']]
            header=u32(x,4)
            try:
                assert header in (36,40) and u32(x,8)==header, ('CLGP header',header)
                field=u32(x,28)
                positions=[u32(x,ptr) for ptr in range(field,header,4)] if field<header else [field]
                for p in positions:
                    assert x[p:p+4]==b'TADP', ('PDAT tag',p,x[p:p+4].hex())
                    size=u32(x,p+4)
                    assert p+size<=len(x) and u32(x,p+8)==12345678, ('PDAT bounds/marker',p,size)
                    rec=parse_mip_body(x[p+36:p+size])
                    records.append({'family_id':fam['id'],'node':node['path'],'pdat_offset_in_node':p,'pdat_size':size,**rec})
            except Exception as ex:failures.append({'family_id':fam['id'],'node':node['path'],'error':type(ex).__name__+': '+str(ex)})
    x=(root/'DATA/BIKERS/TEMPLATE.MIP').read_bytes();assert u32(x,0)==len(x)-4
    template=parse_mip_body(x[4:])
    dump(out/'mip_structures.json',{'template':template,'clgp_pdats':records,'failures':failures})
    summary={'clgp_pdat_mip_structures_validated':len(records),'mip_level_records':sum(len(x['levels']) for x in records),'template_levels':len(template['levels']),'failures':failures,'status':'Structural pointers/dimensions/bounds validated; pixel orientation and runtime sampling semantics not proven'}
    dump(out/'mip_summary.json',summary);print(json.dumps({**summary,'failure_count':len(failures),'failures':failures[:3]},indent=2))
if __name__=='__main__':main()
