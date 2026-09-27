# Racing Bois — mandatory user rules

- **Never use Jarvis MCP while working in Codex.** This includes discovery, read-only calls and any Jarvis MCP bridge to Blender, Unity, image generation or other capabilities. Use direct Unity MCP, the direct pinned Blender MCP server and the built-in image generation tool. Apply the same restriction to every delegated agent.
- Asset recovery uses **local/free tools only**, per the user's explicit choice. Do not submit paid image-to-3D jobs, buy credits or provision paid cloud generation services.
- **UI and 3D assets must match the finalized 2D prototype concepts 100%.** Concepts are the visual specification, not loose inspiration. Generate and inspect the 2D concept before new modeling or UI implementation. Preserve the exact approved reference version and its hash.
- Compare actual rendered output with the corresponding concept view: silhouette, proportions, geometry, component placement, materials, color, details, typography and layout. Record differences and keep mismatching candidates unaccepted. Do not claim 100% fidelity from mesh checks, compilation or a fabricated similarity score. Resolve inconsistent reference views before production; never silently weaken the requirement.
- Primary client: Unity Windows10/11 desktop; Web later. Online backend and data remain on OCI. Offline LAN uses its own local realm.
- Source must use appropriate established design patterns, clear responsibility/dependency boundaries and readable, maintainable, extensible code.
- Preserve the pre-existing user change to `ArtSource/Weapons/RB_Club.blend`. Do not overwrite or include it in automated cleanup. Protected SHA256: `553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f`.
