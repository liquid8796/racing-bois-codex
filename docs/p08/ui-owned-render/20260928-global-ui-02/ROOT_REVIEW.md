# Manual owned UI render — 1920 x 1080

The original helper run 01 stopped after warming its copied Regular font. Giving
that copied font a name different from its filename caused Unity to add an
ImportLog object, which correctly failed the strict subasset-membership check.
The failed run and its copied assets remain preserved. A read-only comparison
after the failure found all six original font/material/atlas serialized hashes,
both atlas pixel hashes, both file hashes and clean dirty flags unchanged.

R2 retains the copied font's name. Its fresh run 02 passed the same strict
ownership check, copied-TTF dependency closure and complete 248-codepoint warming
for both fonts. Original source/meta/member/atlas snapshots remained exact.

An attached RuntimePanel in the quiet Editor preview scene did not automatically
lay itself out. Invoking its own Update and Render established layout but left
the initially cleared target blank. The observed working order was the owned
panel's Update, Repaint with an EventType.Repaint event, then Render. No global
panel update or unrelated UI was driven. Capture then produced the actual
`menu-enu-initial.png`, SHA256
`ba8cb0165f4daa24b4c09a6d9337e58d6d8bf7a7b406459e2527daa08c1a1f55`.

Root inspected that image. The English menu text is readable; its 20 reported
text regions have no ellipsis. The panel has a 1600 x 900 layout rendered into
1920 x 1080 pixels, following the copied source PanelSettings scale policy.
This is UI-only rendering over a cleared target. It contains no background
environment, bike or rider and establishes no scene-composition fidelity.

The corresponding locked main-v2 reference was also inspected, SHA256
`9b7ad175234636c591846552178f2d25a279434763ce5d0f252af738c6c8e95e`.
The reference's full composition and precise typography remain unaccepted;
this isolated language check does not replace that visual gate. The reference
shows Apex while the synthetic initial menu selects Spark 450 by current rules.

Detach, two-update barrier and Dispose completed successfully. The release
receipt confirms original preservation; transient document/texture/preview
objects were released and persistent owned copies remain private/ignored.
