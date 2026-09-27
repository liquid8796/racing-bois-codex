"""Rebuildable, read-only x86 analysis project; addresses are original image VAs.

Recursive decoding uses only reachable branches from explicit roots/direct calls.
Indirect edges remain unresolved unless a local CMP bounds an indexed jump table.
This is an analysis database, not recovered original source or coverage proof.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent / "vendor"), str(REPO / "tools/reverse-engineering/logic/vendor")]
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_GRP_RET, CS_GRP_JUMP
from capstone.x86 import X86_OP_IMM, X86_OP_MEM

SOURCE = Path(r"C:\Users\Liquid\Downloads\Unity\racing_bois_mod\RacingBois.exe")
EXPECTED_SHA256 = "66ab853c5b7b73b82a7c22a0478f5ba5b1066ed27028ef96449f5fe36a6101c5"
OUT = REPO / "docs/p01/logic"
ALIASES = {
    0x44b2e0: ("simulation_tick_batch", "clock"),
    0x44b3b0: ("simulation_tick_dispatch", "clock"),
    0x442e10: ("message_pump_then_tick_batch", "clock"),
    0x448200: ("application_initialize", "startup"),
    0x4163b0: ("counter_low32_sample", "clock"),
    0x44f800: ("poll_keyboard_joystick_bits", "input"),
    0x44fa80: ("keyboard_bits_candidate", "input"),
    0x440410: ("rider_input_bits", "input"),
    0x4163d0: ("race_scheduler_60hz", "clock"),
    0x416010: ("race_outcome_request", "outcome"),
    0x416120: ("race_teardown_result_transition", "outcome"),
    0x438c70: ("traction_and_lean_candidate", "physics"),
    0x4390c0: ("forward_velocity_integrator", "physics"),
    0x4391d0: ("gear_hysteresis_step", "physics"),
    0x439390: ("advance_longitudinal_segment", "physics"),
    0x4394c0: ("segment_curve_grade_delta", "physics"),
    0x4395e0: ("position_and_road_integration", "physics"),
    0x43a0c0: ("surface_region_classifier", "physics"),
    0x43a580: ("integrator_and_collision_dispatch", "physics"),
    0x43a610: ("road_edge_collision_candidate", "physics"),
    0x403d60: ("fall_transition_candidate", "recovery"),
    0x407bd0: ("detached_rider_update_candidate", "recovery"),
    0x40a410: ("rider_motion_update_candidate", "physics"),
    0x406890: ("rider_finish_check_candidate", "outcome"),
    0x437800: ("finish_transition_candidate", "outcome"),
    0x437860: ("finish_record_append", "outcome"),
    0x408e30: ("rider_behavior_0", "ai"),
    0x409000: ("rider_behavior_1", "ai"),
    0x4092d0: ("rider_behavior_2", "ai"),
    0x409ca0: ("rider_behavior_4", "ai"),
    0x40a4f0: ("rider_behavior_5", "ai"),
    0x40a560: ("rider_behavior_6", "ai"),
    0x40a5b0: ("rider_behavior_7", "ai"),
    0x40a600: ("rider_behavior_8", "ai"),
    0x40ac60: ("rider_behavior_9_noop", "ai"),
    0x40a9d0: ("recovery_run_speed_1200", "recovery"),
    0x40acd0: ("throttle_brake_command", "input"),
    0x40adb0: ("throttle_ramp_and_drive", "physics"),
    0x40aea0: ("brake_ramp_and_drive", "physics"),
    0x40af50: ("steering_command_filter", "input"),
    0x434660: ("local_player_input_dispatch", "input"),
    0x43ae90: ("animation_tick_advance", "animation"),
    0x4082f0: ("ai_relationship_and_speed_refresh", "ai"),
    0x408ad0: ("ai_behavior_selector", "ai"),
    0x408df0: ("ai_behavior_transition", "ai"),
    0x4092b0: ("target_ahead_of_extents", "ai"),
    0x4092e0: ("ai_attack_eligibility", "ai"),
    0x40a4a0: ("target_behind_near_predicate", "ai"),
    0x406b80: ("police_spawn", "ai"),
    0x407f30: ("rider_animation_and_bust_update", "recovery"),
    0x4409e0: ("traffic_or_police_spawn_dispatch", "ai"),
    0x440dd0: ("live_traffic_update", "ai"),
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--show", type=lambda s: int(s, 0))
    args = parser.parse_args()
    if hashlib.sha256(args.source.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise SystemExit("Unrecognized binary; fixed addresses must be re-audited.")
    pe = pefile.PE(str(args.source))
    base = pe.OPTIONAL_HEADER.ImageBase
    image = pe.get_memory_mapped_image()
    cs = Cs(CS_ARCH_X86, CS_MODE_32)
    cs.detail = True
    sections = [(base+s.VirtualAddress, base+s.VirtualAddress+s.Misc_VirtualSize)
                for s in pe.sections if s.Characteristics & 0x20000000]
    def code(va): return any(a <= va < b for a,b in sections)
    imports = {i.address: e.dll.decode()+"!"+(i.name.decode() if i.name else str(i.ordinal))
               for e in pe.DIRECTORY_ENTRY_IMPORT for i in e.imports}
    old = json.loads((REPO / "docs/reverse-engineering/logic/function_index.json").read_text())
    aliases = {int(r["va_start"],16):(r["analyst_label"],r["category"]) for r in old}
    aliases.update(ALIASES)
    roots = set(aliases) | {base + pe.OPTIONAL_HEADER.AddressOfEntryPoint}
    pending = collections.deque(sorted(roots))
    functions, instructions, edges, unresolved = {}, {}, [], []
    while pending:
        start = pending.popleft()
        if start in functions or not code(start): continue
        visited, queue, calls = {}, [start], set()
        while queue:
            va = queue.pop()
            recent = []
            while va not in visited and code(va) and abs(va-start) < 0x10000:
                ins = next(cs.disasm(image[va-base:va-base+15],va,count=1),None)
                if ins is None or ins.mnemonic in ("int3","ud2"): break
                row = (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
                visited[va] = row
                instructions[va] = row
                nxt = va + ins.size
                if ins.mnemonic == "call":
                    op = ins.operands[0]
                    if op.type == X86_OP_IMM and code(op.imm):
                        calls.add(op.imm)
                        edges.append((start, va, op.imm, "direct_call", "decoded"))
                    elif op.type == X86_OP_MEM and not op.mem.base and not op.mem.index and op.mem.disp in imports:
                        edges.append((start, va, op.mem.disp, "import_call", imports[op.mem.disp]))
                    else: unresolved.append((start,va,ins.mnemonic,ins.op_str))
                if ins.group(CS_GRP_RET): break
                if ins.group(CS_GRP_JUMP):
                    op = ins.operands[0]
                    if op.type == X86_OP_IMM:
                        target = op.imm
                        if code(target): queue.append(target)
                        edges.append((start,va,target,"branch", "decoded"))
                    else:
                        resolved = False
                        if op.type == X86_OP_MEM and not op.mem.base and op.mem.index and op.mem.scale == 4:
                            bounds = [r.operands[1].imm for r in recent[-8:] if r.mnemonic=="cmp" and len(r.operands)==2 and r.operands[1].type==X86_OP_IMM and 0<=r.operands[1].imm<128]
                            if bounds:
                                n = bounds[-1] + 1
                                targets = [int.from_bytes(image[op.mem.disp-base+j*4:op.mem.disp-base+j*4+4],"little") for j in range(n)]
                                if all(code(t) for t in targets):
                                    for target in targets:
                                        queue.append(target)
                                        edges.append((start,va,target,"switch_candidate","local_cmp_bound_requires_review"))
                                    resolved = True
                        if not resolved: unresolved.append((start,va,ins.mnemonic,ins.op_str))
                    if ins.mnemonic == "jmp": break
                recent.append(ins)
                va = nxt
        functions[start] = visited
        pending.extend(sorted(calls))
    OUT.mkdir(parents=True, exist_ok=True)
    db = OUT / "native-analysis.sqlite"
    with sqlite3.connect(db) as con:
        con.executescript("DROP TABLE IF EXISTS metadata; DROP TABLE IF EXISTS functions; DROP TABLE IF EXISTS instructions; DROP TABLE IF EXISTS membership; DROP TABLE IF EXISTS edges; DROP TABLE IF EXISTS unresolved; CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE functions(va INTEGER PRIMARY KEY,label TEXT,category TEXT,root INTEGER,instruction_count INTEGER); CREATE TABLE instructions(va INTEGER PRIMARY KEY,bytes TEXT,mnemonic TEXT,operands TEXT); CREATE TABLE membership(function_va INTEGER,instruction_va INTEGER,PRIMARY KEY(function_va,instruction_va)); CREATE TABLE edges(function_va INTEGER,source_va INTEGER,target_va INTEGER,kind TEXT,evidence TEXT); CREATE TABLE unresolved(function_va INTEGER,source_va INTEGER,mnemonic TEXT,operands TEXT);")
        meta = {"source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(), "source_path": str(args.source), "image_base":hex(base), "method":"recursive CFG, explicit analyst roots and reachable direct call targets", "limitations":"Indirect calls unresolved; local-CMP switch targets are candidates; no total-program runtime coverage claim."}
        con.executemany("INSERT INTO metadata VALUES (?,?)",meta.items())
        con.executemany("INSERT INTO functions VALUES (?,?,?,?,?)",[(a,*aliases.get(a,("sub_%08x"%a,"unclassified")),a in roots,len(v)) for a,v in functions.items()])
        con.executemany("INSERT INTO instructions VALUES (?,?,?,?)",instructions.values())
        con.executemany("INSERT INTO membership VALUES (?,?)",[(a,v) for a,vs in functions.items() for v in vs])
        con.executemany("INSERT INTO edges VALUES (?,?,?,?,?)",edges)
        con.executemany("INSERT INTO unresolved VALUES (?,?,?,?)",unresolved)
    folder = OUT/"functions"
    folder.mkdir(exist_ok=True)
    for start, (label, category) in aliases.items():
        rows=functions.get(start,{})
        (folder/(label+".tsv")).write_text("\n".join("%08x\t%s\t%s\t%s"%r for _,r in sorted(rows.items()))+"\n")
    summary = meta | {"functions":len(functions),"unique_instructions":len(instructions),"edges":len(edges),"unresolved_indirect_edges":len(unresolved),"analyst_aliases":len(aliases),"entry_points":[hex(a) for a in sorted(roots)]}
    (OUT/"analysis-project.json").write_text(json.dumps(summary,indent=2)+"\n")
    (OUT/"callgraph.json").write_text(json.dumps([{"caller":hex(a),"site":hex(b),"target":hex(c),"kind":d,"evidence":e} for a,b,c,d,e in edges if "call" in d],indent=2)+"\n")
    if args.show:
        for _,row in sorted(functions.get(args.show,{}).items()): print("%08x\t%s\t%s\t%s"%row)
    else: print(json.dumps(summary,indent=2))

if __name__ == "__main__": main()
