# V19 candidate04 — retained unsuccessful geometry study

**Visually unaccepted; an additional geometric ordering check also fails. No
Assets export, production promotion, budget adjustment or mask change.**

The actual render is `candidate04-gameplay.png`. Broken horizontal beds,
staggered upper groups and lower talus termination are more visible than03.
However, the faces read as angular stepped/jigsaw facets, with insufficient
natural roughness. They do not match the locked concept's fractured sandstone.
The unchanged road, near cliff, valley and lighting differences also remain.

Triangle totals are **1,849,868 / 922,557 / 375,261**, reduced from03's
3,795,244 / 1,778,515 / 705,975. Points are concentrated at fracture shoulders
and bed transitions rather than dense uniform surface sampling. Far33–44 remain
the only changed36 meshes;616 others, camera/light/world/color state and
material/image membership are exact before/after matches.

The original author check passes closed-manifold, positive aggregate volume,
duplicate-triangle, UV cross `>1e-14` and physical cross squared `>1e-16 m^4`
requirements. UV/physical minima are0.00659701407130342 and0.002657806995557621.
These checks do **not** establish freedom from folded side strips.

Independent review identified that changing fracture positions between beds also
changes the position used for top-height displacement. Actual saved-mesh checking
confirms **319 non-increasing vertical edges in18 of78 closed components**, with
a minimum adjacent-ring height difference of **−1.8460464477539062m**. Every
expected connecting edge was found, so this is a measurement of the authored
ring topology, not an inferred index layout. See
`candidate04-ring-order-audit.json` for actual world-space witnesses.

The ring check is not a complete self-intersection test. It establishes that the
intended upward ordering fails and warrants a fresh geometric correction; the
candidate is not described as geometrically clean merely because its topology
is manifold. The source, failed check, successful narrower checks and actual
render remain unchanged. A next candidate should preserve monotonic ring heights
and reduce the artificial facet stepping before any export decision.

Source03, source04, the concept and previous receipts are retained. The direct
pinned Blender MCP server ran in safe mode on the owned port9877. No Unity,
Jarvis, paid service or unrelated authoring asset was used or modified.
