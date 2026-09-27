import sys,json,re,struct,hashlib,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent/'vendor'))
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
from capstone.x86 import X86_OP_IMM,X86_OP_MEM
ROOT=pathlib.Path(r'C:\Users\Liquid\Downloads\Unity\racing_bois_mod')
OUT=pathlib.Path(r'D:\Project\Unity\racing-bois\docs\reverse-engineering\logic')
OUT.mkdir(parents=True,exist_ok=True)
files=sorted(list(ROOT.glob('*.exe'))+list(ROOT.glob('*.DLL'))+list((ROOT/'TEXT').glob('*.DLL')),key=lambda x:str(x).lower())
summary=[]; allstrings=[]
for file in files:
 data=file.read_bytes()
 try: pe=pefile.PE(data=data)
 except pefile.PEFormatError as exc:
  summary.append({'file':str(file.relative_to(ROOT)),'size':len(data),'format_error':str(exc),'header_hex':data[:32].hex()});continue
 base=pe.OPTIONAL_HEADER.ImageBase
 sections=[{'name':s.Name.rstrip(b'\0').decode(errors='replace'),'rva':hex(s.VirtualAddress),'virtual_size':s.Misc_VirtualSize,'raw_offset':hex(s.PointerToRawData),'raw_size':s.SizeOfRawData,'characteristics':hex(s.Characteristics)} for s in pe.sections]
 imports=[]
 for entry in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
  imports += [{'dll':entry.dll.decode(errors='replace'),'name':i.name.decode(errors='replace') if i.name else '#'+str(i.ordinal),'iat':hex(i.address)} for i in entry.imports]
 exports=[{'name':e.name.decode(errors='replace') if e.name else None,'ordinal':e.ordinal,'rva':hex(e.address)} for e in getattr(getattr(pe,'DIRECTORY_ENTRY_EXPORT',None),'symbols',[])]
 strings=[]
 for enc,pat in [('ascii',rb'[\x20-\x7e]{4,}'),('utf16',rb'(?:[\x20-\x7e]\x00){4,}')]:
  for m in re.finditer(pat,data):
   try:rva=pe.get_rva_from_offset(m.start()); va=hex(base+rva)
   except:va=None
   item={'file':str(file.relative_to(ROOT)),'offset':hex(m.start()),'va':va,'encoding':enc,'text':m.group().decode('ascii' if enc=='ascii' else 'utf-16le')}
   strings.append(item);allstrings.append(item)
 resources=[]
 if hasattr(pe,'DIRECTORY_ENTRY_RESOURCE'):
  def walk(node,path):
   for entry in node.entries:
    p=path+[str(entry.name) if entry.name else str(entry.struct.Id)]
    if hasattr(entry,'directory'):walk(entry.directory,p)
    else:
     r=entry.data.struct; blob=pe.get_data(r.OffsetToData,r.Size)
     resources.append({'path':'/'.join(p),'rva':hex(r.OffsetToData),'size':r.Size,'sha256':hashlib.sha256(blob).hexdigest()})
  walk(pe.DIRECTORY_ENTRY_RESOURCE,[])
 item={'file':str(file.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'machine':hex(pe.FILE_HEADER.Machine),'timestamp':pe.FILE_HEADER.TimeDateStamp,'image_base':hex(base),'entry_rva':hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),'linker':[pe.OPTIONAL_HEADER.MajorLinkerVersion,pe.OPTIONAL_HEADER.MinorLinkerVersion],'subsystem':pe.OPTIONAL_HEADER.Subsystem,'sections':sections,'imports':imports,'exports':exports,'resources':resources}
 summary.append(item)
 (OUT/(file.name+'.strings.json')).write_text(json.dumps(strings,ensure_ascii=False,indent=2),encoding='utf8')
 if file.name=='RacingBois.exe':
  cs=Cs(CS_ARCH_X86,CS_MODE_32);cs.detail=True; insns=[]; refs=[]; imports_map={int(i['iat'],16):i for i in imports}; string_map={int(i['va'],16):i for i in strings if i['va']}
  for s in pe.sections:
   if not s.Characteristics&0x20000000:continue
   cs.skipdata=True
   for insn in cs.disasm(s.get_data(),base+s.VirtualAddress):
    insns.append(f'{insn.address:08x}\t{insn.bytes.hex()}\t{insn.mnemonic}\t{insn.op_str}')
    if not insn.id:continue
    for op in insn.operands:
     v=op.imm if op.type==X86_OP_IMM else op.mem.disp if op.type==X86_OP_MEM else None
     if v in imports_map or v in string_map:
      refs.append({'address':hex(insn.address),'instruction':insn.mnemonic+' '+insn.op_str,'target':hex(v),'import':imports_map.get(v),'string':string_map.get(v)})
  (OUT/'RacingBois.disassembly.tsv').write_text('\n'.join(insns),encoding='utf8')
  (OUT/'RacingBois.xrefs.json').write_text(json.dumps(refs,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'pe_inventory.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps([{k:v for k,v in i.items() if k not in ['resources','imports','sections','exports']}|{'imports':len(i.get('imports',[])),'resources':len(i.get('resources',[])),'exports':len(i.get('exports',[]))} for i in summary],indent=2))
