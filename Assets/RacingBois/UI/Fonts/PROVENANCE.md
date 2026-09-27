# UI typeface

Noto Sans Regular, from the Noto project (not from the original game).

- Source: https://github.com/notofonts/noto-fonts/tree/main/hinted/ttf/NotoSans
- Download: https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf
- SHA-256: b85c38ecea8a7cfb39c24e395a4007474fa5a4fc864f6ee33309eb4948d232d5
- License: SIL Open Font License 1.1, included in OFL.txt.
- Downloaded 2026-09-21. The Unity SDF atlas is generated locally by FoundationBuilder for Vietnamese UI coverage.

This is a general-purpose licensed typeface dependency, not extracted game art. All Racing Bois prop geometry, texture artwork, UI layout and visual identity in this foundation were newly authored.

## Desktop concept typography — 2026-09-27

Noto Sans ExtraBold is from the same official Noto font repository and uses the included SIL OFL1.1 license. It provides actual heavy glyphs for main-v2 headings/actions rather than only synthetic bold on the Regular face.

- Source/download: https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSans/NotoSans-ExtraBold.ttf
- SHA256: `1cfa3aa25ee505ee66cbf12e29b13b4b8dd0f8ca9e89d08e7ca36f3788d80a57`.
- SDF generated locally via Unity MCP using TextCore, sampling48/padding5,2048atlas. Latin/Vietnamese glyph ranges preloaded; dynamic fallback remains enabled.
- Typeface/layout/scene fidelity still requires actual rendered concept comparison; the font selection itself is not a100%match assertion.
