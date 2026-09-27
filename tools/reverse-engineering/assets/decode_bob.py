"""BOB research previews using dimensions confirmed from native loader callsites."""
from audit_assets import *
def main():
    root=pathlib.Path(r'C:\Users\Liquid\Downloads\Unity\racing_bois_mod');out=pathlib.Path('docs/reverse-engineering/assets')
    pal=(root/'DATA/PALETTE.RAW').read_bytes();palette=[c for i in range(256) for c in pal[i*4:i*4+3]];rows=[];images=[]
    for p in sorted((root/'IMAGES').rglob('*.BOB')):
        d=p.read_bytes();name=p.name
        if p.parent.name=='HORIZONS':w=360 if name.startswith('L') else 720;proof='VA0x44c440,0x44c453 width720/360; stored rows=size/width'
        elif 'DASH' in name:w=320 if 'LO' in name else 640;proof='VA0x44c710 ->0x44c5f0 width640/320; stored rows=size/width'
        elif 'METER' in name:w=95 if name.startswith('LIL') else 190;proof='VA0x44c5d0 width190/95'
        elif name=='MATTE.BOB':w=640;proof='VA0x44c87d width640'
        else:
            rows.append({'path':p.relative_to(root).as_posix(),'status':'PENDING_LOADER_DIMENSIONS','bytes':len(d)})
            continue
        assert len(d)%w==0;h=len(d)//w
        im=Image.frombytes('P',(w,h),d);im.putpalette(palette)
        target=p.relative_to(root).as_posix().replace('/','_')+'.png';im.save(out/'samples'/target)
        rows.append({'path':p.relative_to(root).as_posix(),'status':'DIMENSIONS_CONFIRMED_PIXELS_PREVIEWED','bytes':len(d),'width':w,'height':h,'proof':proof,'palette_status':'RGBX global palette; runtime transparency/remap/crop not asserted','sample':f'samples/{target}'})
        if p.parent.name=='HORIZONS' and not name.startswith('L'):images.append((name,im.convert('RGB')))
    sheet=Image.new('RGB',(720,350*len(images)),(32,32,32));draw=ImageDraw.Draw(sheet)
    for i,(name,im) in enumerate(images):sheet.paste(im,(0,i*350+25));draw.text((5,i*350+5),name,fill='white')
    sheet.save(out/'samples/horizon_contact_sheet.png');dump(out/'bob_images.json',rows);csvdump(out/'bob_images.csv',rows)
    print('BOB decoded',sum(x['status'].startswith('DIMENSIONS') for x in rows),'pending',sum(x['status'].startswith('PENDING') for x in rows))
if __name__=='__main__':main()
