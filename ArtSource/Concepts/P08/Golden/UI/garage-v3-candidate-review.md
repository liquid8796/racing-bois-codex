# Garage v3 reference correction candidate — not promoted

Created with the built-in ImageGen tool on 2026-09-28 Bangkok. The exact model
version is not exposed. Both supplied references were opened before editing:
the locked garage-v2 screen and the later locked Spark-v1 motorcycle master.
The original reference files remain unchanged.

The intended correction is only the first inventory thumbnail: garage-v2 uses
the older P06 two-headlamp Spark, while the newer standalone Spark master uses
one round headlamp. The new thumbnail now depicts the copper/cream single-lamp
motorcycle with brown saddle and stacked exhausts. This uses the concept master,
not an unaccepted 3D render, as its source.

The output was inspected at its full 1672x941 size. Text/navigation, Apex and the
workshop retain the same overall composition, but the image generator changed
pixels throughout the screen. The thumbnail's mirror also reaches the first
row's upper boundary. This is not a strictly isolated thumbnail replacement and
is not promoted over garage-v2. The original locked reference and its runtime
hash constants remain in force; the reference mismatch remains an open gate.

The adjacent JSON records exact image/prompt/input hashes and the bounds/count
of changed pixels outside the requested edit area. These are edit-invariant
diagnostics, not a similarity or concept-fidelity score. No UI/3D acceptance or
production mask changes follow from the generated candidate.

Prompt: garage-v3-candidate-prompt.txt. Generated image:
garage-v3-candidate.png. The original tool output is retained in Codex's generated
images directory; the project copy is byte-identical.
