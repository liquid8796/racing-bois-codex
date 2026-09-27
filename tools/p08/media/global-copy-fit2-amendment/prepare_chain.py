"""Create an immutable second fit amendment over the installed first amendment."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EFFECTIVE = HERE.parent / 'global-copy-effective'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def row(path): return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path))
def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(data)
def encoded(value): return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')

def main():
    plan_path = HERE / 'amendment.json'
    if plan_path.exists() or (HERE / 'before-effective').exists():
        raise SystemExit('Fresh immutable chain required')
    pointer = EFFECTIVE / 'current.json'
    old_pointer = json.loads(pointer.read_text(encoding='utf-8'))
    if old_pointer['active']['path'] != 'tools/p08/media/global-copy-fit-amendment/amendment.json':
        raise SystemExit('Unexpected prior effective chain')
    baseline = HERE.parent / 'global-copy-fit-amendment/authored-text-union.json'
    if sha(baseline) != 'b9269f11d6109e8767c6498fdc20f2ce46ff2b147ca3fe2b154ba921f15d2f2d':
        raise SystemExit('Expected first fit union changed')
    for source in sorted(EFFECTIVE.glob('*')):
        if source.is_file(): write_new(HERE / 'before-effective' / source.name, source.read_bytes())
    modules = []
    for name in ('Main', 'Career', 'Multiplayer', 'ClientMessages'):
        source = ROOT / f'Assets/RacingBois/Client/Application/UiText.{name}.Generated.cs'
        destination = HERE / 'before' / source.name
        write_new(destination, source.read_bytes())
        modules.append(dict(name=name, base=row(destination)))
    if sha(HERE / 'before/UiText.Career.Generated.cs') != 'e2b9c1cf7eaafb7316b133064ca84ec318641a6c70d44de3fa3bc44dd2e83131':
        raise SystemExit('Installed first Career fit amendment required')
    changes = json.loads((HERE / 'changes.json').read_text(encoding='utf-8'))
    plan = dict(schema=1, scope='reviewed-copy-fit-amendment', identity='global-copy-fit-20260928-02',
                baseUnion=row(baseline), authoredChanges=row(HERE / 'changes.json'), modules=modules,
                changes=changes, nativeUiAccepted=False, priorAmendmentPointer=row(HERE / 'before-effective/current.json'))
    write_new(plan_path, encoded(plan))
    new_pointer = dict(schema=1, active=row(plan_path), outputDirectory=HERE.relative_to(ROOT).as_posix())
    if pointer.read_bytes() != (HERE / 'before-effective/current.json').read_bytes():
        raise SystemExit('Concurrent pointer change')
    pointer.write_bytes(encoded(new_pointer))
    print('Prepared one Multiplayer cell; preserved prior pointer, tooling, module bases and Career fit')

if __name__ == '__main__': main()
