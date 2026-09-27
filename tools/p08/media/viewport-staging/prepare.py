"""Stage a guarded target-texture viewport correction without touching Assets."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TARGET = 'Assets/RacingBois/Client/Presentation/RaceScreen.cs'
plan = json.loads((HERE.parent / 'global-copy-main-staging/handoff.json').read_text())
expected = next(row['candidateSha256'] for row in plan['files'] if row['target'] == TARGET)
original = (ROOT / TARGET).read_bytes()
assert hashlib.sha256(original).hexdigest() == expected
text = original.decode('utf-8')
replacements = [
    ('        private int viewportWidth, viewportHeight;',
     '        private int viewportWidth, viewportHeight;\n        private UIDocument boundDocument;'),
    ('            root=document.rootVisualElement;surface=root.Q("surface");',
     '            boundDocument = document;\n            root=document.rootVisualElement;surface=root.Q("surface");'),
    ('''        private void Update()
        {
            if (root != null && (viewportWidth != Screen.width || viewportHeight != Screen.height))
                UpdateResponsiveLayout(surface.contentRect);
        }
        private void UpdateResponsiveLayout(Rect bounds)
        {
            viewportWidth = Screen.width; viewportHeight = Screen.height;
            // ScaleWithScreenSize may keep logical bounds constant as output pixels shrink.''',
     '''        private Vector2Int OutputPixels()
        {
            var target = boundDocument != null && boundDocument.panelSettings != null
                ? boundDocument.panelSettings.targetTexture : null;
            return target != null ? new Vector2Int(target.width, target.height)
                : new Vector2Int(Screen.width, Screen.height);
        }
        private void Update()
        {
            if (root == null) return;
            var pixels = OutputPixels();
            if (viewportWidth != pixels.x || viewportHeight != pixels.y)
                UpdateResponsiveLayout(surface.contentRect);
        }
        private void UpdateResponsiveLayout(Rect bounds)
        {
            var pixels = OutputPixels();
            viewportWidth = pixels.x; viewportHeight = pixels.y;
            // A target texture has its own output size; logical bounds can stay constant.'''),
]
# Retain the exact prior bytes, then normalize this mixed-ending candidate to CRLF.
newline = '\r\n' if b'\r\n' in original else '\n'
normalized = text.replace('\r\n', '\n')
for before, after in replacements:
    assert normalized.count(before) == 1, before
    normalized = normalized.replace(before, after, 1)
lines = normalized.splitlines(keepends=True)
cleaned = sum(bool(line.strip('\n')) and not line.strip() for line in lines)
assert cleaned == 2
candidate = ''.join('\n' if line.strip('\n') and not line.strip() else line for line in lines).replace('\n', newline).encode('utf-8')
for name, content in (('before-RaceScreen.cs', original), ('RaceScreen.cs', candidate)):
    with (HERE / name).open('xb') as output:
        output.write(content)
identity = dict(schema=1, target=TARGET, beforeSha256=expected,
                candidateSha256=hashlib.sha256(candidate).hexdigest(),
                metaSha256=hashlib.sha256((ROOT / (TARGET + '.meta')).read_bytes()).hexdigest(),
                whitespaceOnlyLinesCleaned=cleaned,
                scope='Use actual UIDocument render-target pixels for responsive layout; ordinary desktop Screen fallback unchanged.')
with (HERE / 'handoff.json').open('x', encoding='utf-8') as output:
    json.dump(identity, output, indent=2)
    output.write('\n')
print(json.dumps(identity))
