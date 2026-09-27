import json, pathlib, struct,sys
sys.path.insert(0,'tools/reverse-engineering/logic/vendor');import pefile
root=pathlib.Path(r'C:\Users\Liquid\Downloads\Unity\racing_bois_mod');out=pathlib.Path('docs/reverse-engineering/logic')
allstrings=[]
for file in sorted((root/'TEXT').glob('*.DLL')):
 try:pe=pefile.PE(str(file))
 except:continue
 for typ in pe.DIRECTORY_ENTRY_RESOURCE.entries:
  if typ.id!=6:continue
  for block in typ.directory.entries:
   for lang in block.directory.entries:
    d=lang.data.struct;b=pe.get_data(d.OffsetToData,d.Size);p=0
    for i in range(16):
     n=struct.unpack_from('<H',b,p)[0];p+=2;s=b[p:p+2*n].decode('utf-16le');p+=2*n
     if s:allstrings.append({'file':file.name,'language_id':lang.id,'id':(block.id-1)*16+i,'text':s})
(out/'localization_strings.json').write_text(json.dumps(allstrings,ensure_ascii=False,indent=2),encoding='utf8')
(out/'ENU_strings.tsv').write_text('\n'.join(f"{s['id']}\t{s['text']}" for s in allstrings if s['file']=='ENU.DLL'),encoding='utf8')
saves=[]
for f in sorted(list((root/'SAVES').glob('*'))+[f for f in root.iterdir() if f.is_file() and f.stat().st_size==160]):
 b=f.read_bytes();saves.append({'file':str(f.relative_to(root)),'hex':b.hex(),'u32':list(struct.unpack('<40I',b)),'ascii': ''.join(chr(x) if 32<=x<127 else '.' for x in b)})
(out/'saves_raw.json').write_text(json.dumps(saves,indent=2),encoding='utf8')
print('Total localized strings',len(allstrings),'EN',sum(x['file']=='ENU.DLL' for x in allstrings));print('\n'.join(s['file']+' '+s['ascii']+'\n'+str(s['u32']) for s in saves))
