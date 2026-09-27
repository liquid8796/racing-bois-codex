# Root review through V19-06

Root inspected actual gameplay renders 02, 03, 05 and 06 against the already
inspected top gameplay view of locked canyon-v2. Camera, road and near-cliff
placement remained fixed during this Far-chain study.

Candidate 02's broad smooth stepped masses were too artificial. Candidate 03
added visible fractures but produced a continuous ribbed wall and repeated talus
apron. The saved-mesh audit subsequently rejected 04's 319 inverted vertical
edges despite its manifold/UV checks. Candidate 05 retains the lower triangle
cost and fixes that predicate to zero on actual disk-reloaded geometry.

Candidate 06 uses measured local CC0 surface detail and existing cliff materials.
The visible wall has more horizontal surface breakup and less uniform fluting,
but several broad faces, ledge patterns and the long close wall still differ
from the concept's irregular fractured mesas and deep setbacks. The unchanged
road, near cliff, valley, foliage, rail and lighting also retain their earlier
differences. **None of these candidates is visually accepted.**

06 reports 2,017,316 / 996,229 / 403,721 whole-scene LOD triangles, zero inverted
vertical edges across 90 authored components, 616 other meshes unchanged, and
preserved existing material/image data. These bounded geometry/preservation
checks do not establish native rendering, performance or visual fidelity.

The cumulative candidate06 manifest binds all six saved sources, scripts,
renders and retained failures. There is no Assets export or production binding.
Later composition iterations remain separate from this frozen checkpoint.
