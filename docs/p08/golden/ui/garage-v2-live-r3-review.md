# Garage v2 runtime layout review

Captured in the actual Unity Editor Game view at 1920×1080 and 1366×768 on 2026-09-26. Reference: `ArtSource/Concepts/P08/Golden/UI/garage-v2.png`.

The fresh `garage-v2-live-1920-r3.png` and `garage-v2-live-1366-r3.png` show the corrected full-width action rail and smaller inventory typography. Names, condition and actions no longer clip. The captures use the real Scale With Screen Size panel and output-pixel breakpoints. Remaining typography and vertical-spacing differences are visible; this is not a 100% fidelity acceptance.

These are explicitly labelled editor fixtures with Spark/Apex ownership and Apex selected. The old P06 bike/rider/road are still the scene background. Missing thumbnails, mismatching displayed bike and absent workshop remain failures. No profile was modified and no network transaction occurred.

The real content-error overlay was opened over the fixture. After focus settled, `content-retry` had focus, `ContentBusy=true`, `BlocksGameplayInput=true`, and zero visible career roots were enabled. The overlay and fixture were then closed and Free Aspect restored. This proves that specific focus-priority path; it does not replace mouse/keyboard/gamepad testing of every flow.

Earlier captures originally named `garage-v2-layout-*-r2` were invalidated when USS hot reload rebuilt the document. They show the main menu and were renamed `main-v2-hot-reload-*-r2.png`; they are not garage evidence. The older r1 capture remains historical evidence of the oversized layout.

UI/UX Pro Max's focus-not-obscured guidance was consulted as a general interaction principle. Its web WCAG results were not treated as a Unity certification or a replacement for the locked visual concept.
