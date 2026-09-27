# V4 immutable publication

`tools/p08/golden/ash_v4/publish_verified.py` publishes the frozen FBX and20new
PBR maps to Assets/RacingBois/Art/P08/Golden/Ash/V4 and creates descriptor.json.
It does not invoke Unity, edit the review fixture, replace Idle, modify a
production content mask or mark visual acceptance.

The delivery and staged descriptor hashes are pinned in the script. Complete
input/destination validation precedes writes. Conflicting files are rejected;
same-hash files are reused. Temporary copies are verified before atomic
no-replace publication. Sources and outputs are rechecked after copying.
Existing Unity .meta files are preserved. No previous asset version is deleted.

Seven isolated file-IO tests pass in publisher-tests.json. The actual first
run published21files; an actual second run reused21files with0asset writes and
no descriptor rewrite. Receipts:

- publish-receipts/20260927T015749.493875Z.json
- publish-receipts/20260927T015751.743141Z.json

Published descriptor SHA256:
`4fec141ea7b38ffdac559d4ecc89c53240f0eca73136cd767f92d4e6a11e2c87`

```powershell
& .\_local\blender-env\Scripts\python.exe tools/p08/golden/ash_v4/publish_verified.py --verify-only
& .\_local\blender-env\Scripts\python.exe tools/p08/golden/ash_v4/publish_verified.py
```

Native import and visual/performance acceptance remain separate open gates.
