# Visual recovery inspection — 2026-09-27

## Apex V7 remains rejected

The reference `ArtSource/Concepts/P08/Golden/apex-v2.png` was inspected before authoring. SHA256: `f8b09f6d24e95724be935f0993bfcd02d2bfaf070e85982c1eba57e6a8479819`.

The preceding saved render has a detached-looking nose, flat triangular fairings and balloon-shaped tank. The V6 recipe still used the geometry that caused those defects. An isolated V7 experiment replaced the low-density fairing fan with quad bands, rolled its edge inward, connected the leading fairing contour toward the nose and replaced the all-round tank loft with defined shoulder profiles.

Actual V7 Blender renders are in `../apex/v7/`. They demonstrate a closed nose/side gap and a less rounded tank. **They still do not match the concept and are not accepted.** Visible differences remain: broad swollen fairing panels, incorrect vent/panel proportions, coarse tank shoulder facets, overly long thin tail, sparse frame/mechanical assembly, inaccurate nose/light shapes, tyre/brake details and insufficient material variation. More triangles do not repair these shape errors. No FBX, production descriptor, LOD acceptance, content mask or roster duplication was issued from V7.

- Source: `ArtSource/P08/Golden/Apex/V7/RB_Golden_Apex_v7.blend`.
- Source SHA256 after the three review renders: `72e6791a2ed1b6289ada7a41220b38cc3422b6f12132621776fad2827962b408`.
- Beauty render SHA256: `e321cdd70680d067a638edcd6366dd04c01adafa25de8f688aea6b97964fb946`.
- Side render SHA256: `36e4335d02ce4882ca121443f128d277c169c09301381e139b0c0808c1a60ca3`.

Reference cameras and lighting are only approximate in these diagnostic renders. No pixel-identical comparison or fabricated similarity percentage is claimed.

## Local anatomical-data route for Ash

The reference `ArtSource/Concepts/P08/Golden/ash-v2.png` was inspected before work. SHA256: `6fa1090e13547df14e578f0ac77504ae5722d99a031a09e5f575c2775f9ce7e6`.

The failed Ash face is a smooth mannequin with detached facial details and repetitive spike hair. Its procedural assembly is not a suitable roster foundation. A coherent anatomical base now exists at `ArtSource/P08/Golden/Ash/AnatomyV1/`, with an actual clay head render at `ash-anatomy-clay-front.png`. It uses MakeHuman core topology and thirteen numeric morph datasets. This is a licensed anatomical-data derivative, **not topology created entirely from scratch and not a completed Ash**. It still needs likeness sculpting, eyes, skin, brows/hair, original concept-specific garment construction, rig/pose deformation and concept comparison.

Source checkout: [MPFB2](https://github.com/makehumancommunity/mpfb2), pinned commit `3edf9df0551765be43563d047888cf7877eb89b4`, under `_local/mpfb2`. The upstream distinguishes GPL addon code from its CC0 asset data. Bundled base mesh, numeric targets, textures and rigs are covered by the [asset license](https://github.com/makehumancommunity/mpfb2/blob/3edf9df0551765be43563d047888cf7877eb89b4/LICENSE.md). Exact input hashes, morph weights, concept hash and the staged OBJ hash are in the anatomy `provenance.json`; adjacent copies preserve the source license.

The MPFB addon was **not installed or executed**. A task-only addon-registration attempt was rejected before execution by Blender MCP safe mode because `importlib` and class registration are not allowed. The rejection is preserved in `mpfb-setup-mcp.json`. Safe mode was never disabled. The implemented alternative imports a plain OBJ using the expressly supported Blender import operator and performs normal mesh/material/render operations through the direct pinned MCP. Numeric asset-data conversion happens in `prepare_ash_anatomy_input.py`; no addon source code is run by that converter.

The official [MakeHuman system assets pack](https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html) supplies CC0 eye, eyebrow and skin data for diagnosis. Download SHA256: `b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107`. Only selected static data were staged; the numeric `.mhclo` maps fit eyes and brows to the shaped anatomy. `surface-provenance.json` binds each input/output hash. Front, three-quarter and profile renders are actual 3D, with the UV-based skin texture and eye geometry; they do not use the concept as a billboard or render background.

The surfaced candidate has coherent ears, eyelids, nose and lips and is a better anatomical foundation. It is still bald, lighter-skinned and less angular than the Ash concept; brows, forehead, cheek/jaw proportions, nose/lip profile and skin character still differ. It has no jacket, gloves, helmet, haircut or game rig. **None of these diagnostic renders passes the 100% concept fidelity gate.** The next author must sculpt likeness against the locked front/profile references, then build concept-specific hair and sewn garment surfaces on this coherent topology before proceeding to portraits or roster duplication.

## Confirmed direct-tool availability

Live safe inspection found Hyper3D/Rodin disabled with no credential, Hunyuan disabled in local mode with no Tencent credentials, Sketchfab disabled/no credential and PolyHaven disabled. No service generation/upload/request was made. The configured local Hunyuan default port 8081 had no listener. Only local/free workflows are in scope.

Blender 5.2.1 LTS was started in a fresh task-owned hidden process after port 9876 had no listener. Factory Cube/Light/Camera state was verified before authoring. Calls used `tools/blender/mcp_client.py`, never Jarvis MCP. Safe mode remains enabled.

The user-owned Club source still hashes to `553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f`. Existing Apex, Ash and production content assets were preserved; all experiments have separate paths.
