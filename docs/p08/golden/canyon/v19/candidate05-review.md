# V19 candidate05 — vertical ordering repaired, visual acceptance still withheld

The actual render is `candidate05-gameplay.png`. The exaggerated jigsaw offsets
in04 are reduced. The Far chain nevertheless remains too vertically fluted and
planar, with insufficient natural broken bedding and face detail compared with
the locked concept. **Visually unaccepted; no Assets export or production change.**

## Demonstrated correction

04 reseeded column positions between beds, then evaluated the height displacement
at those changing XY positions. This produced319 non-increasing vertical edges
across18 components.05 attaches a stable height profile to each column identity.
The bounded top/bedding terms give a vertical derivative lower bound above0.70;
XY staggering is limited to16% of the smaller adjacent joint interval. Smaller
terrace/crack/block offsets reduce artificial stepping without dense resampling.

After saving05, the owned Blender session **reopened that file from disk**.
The same ring topology/connectivity predicate used on04 then measured all78
components: **zero non-increasing edges, all expected connecting edges present,
minimum upward difference1.3149070739746094m**. See `candidate05-reload.json` and
`candidate05-ring-order-audit.json`. This fixes the demonstrated ordering defect;
it is not a claim of a complete arbitrary self-intersection test.

The36 changed meshes also pass unchanged closed-manifold, positive-volume,
duplicate-triangle, primary UV cross `>1e-14` and physical cross squared
`>1e-16 m^4` checks. Minimum UV/physical values are0.04703676883946173 and
0.10055663890670985. The audit preserves616 other scene meshes exactly, plus
camera/light/world/color state and material/image membership.

Whole-scene triangle totals remain exactly **1,849,868 / 922,557 / 375,261**,
equal to04. No triangle budget is increased and no runtime/native performance
acceptance is claimed. Road, near cliff, Bend/Opposite modules and their existing
visual discrepancies remain outside this correction.

## Preserved render-path failure

The first render guard compared forward slashes literally. Reloading the saved
file normalized its stored render path to Windows backslashes, so that guard
stopped before rendering. `candidate05-render.json` retains the failure and
`candidate05-saved-render-path.json` records the exact stored/resolved path.
`render_candidate05_saved.py` normalizes separators before checking the same
exact owned destination; the successful actual render receipt is
`candidate05-render-saved.json`. The retry does not edit or save the source.

04 source/render/failure receipts and every earlier locked input remain intact.
The05 freeze manifest binds the saved source, actual image, scripts and receipts.
All work used the owned direct pinned Blender MCP with safe mode enabled; no
Unity, Jarvis, paid service, Assets write or visual-acceptance entry was involved.
