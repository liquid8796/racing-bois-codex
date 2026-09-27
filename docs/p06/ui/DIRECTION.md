# P06 UI direction and integration

The existing UI Toolkit client is developed into one graphite/amber motorsport system. This work uses the `ui-ux-pro-max` skill's verified keyboard-focus and reduced-motion recommendations. The installed skill has no Unity Toolkit stack entry, so its web/mobile implementation examples were not copied. No 3D asset or raster image is created by this UI task; the layout, monogram, controls and motion are code-native. Existing packaged Noto Sans remains the only font dependency.

## Visual decisions

- Brand: compact RB monogram, restrained route indexing, large editorial game title; the route remains visible behind the left-aligned home panel.
- Surfaces: graphite `15,25,30` at 96% opacity, warm white `246,242,230`, muted `188,198,198`, amber `255,174,78`. Green `139,224,183` denotes ready/saved; coral `255,143,127` denotes error/low condition. Status always includes words.
- Hierarchy: road and opponents stay unobstructed through the center. Rank sits at upper left; condition and speed are anchored at opposite lower corners. Recovery and confirmed combat text remain compact.
- Shared controls: 48-reference-unit main buttons, 44-unit secondary compact controls and input fields; stable 2-unit borders avoid layout changes on focus. Buttons, inputs, dropdowns, toggles and HUD slider have visible focus treatment.
- Motion: new panels use 180 ms opacity/6-unit translation; controls use 120 ms color feedback. Hiding takes effect immediately, so stale controls cannot receive input while a screen transitions. Reduced motion removes both transitions and entry displacement.
- HUD size: 85–115%, anchored around the outer corners so expansion moves inward. This intentionally scales HUD clusters, not the whole document. A narrow/short viewport class reduces panel spacing; the existing 1600×900 PanelSettings reference remains unchanged by this task.
- Results: local practice identifies its local currency; multiplayer shows official persistence state and context-specific next steps. A results screen no longer displays the lobby's ready instruction.

`static-check.json` verifies all 74 named view queries resolve to the 72 unique UXML elements. All measured primary/secondary/status text token pairs exceed 4.5:1 even with the translucent panel composited over a white background. This is a token check, not a claim of complete accessibility compliance or rendered browser contrast.

## Integration API (RaceScreen)

The previous public API remains available.

| API | Contract |
|---|---|
| `ApplyPreferences(bool reducedMotion, bool audioEnabled, float hudScale)` | Apply stored cosmetic settings without raising change events. HUD scale clamps to 0.85–1.15. |
| `PreferencesChanged(bool, bool, float)` | Persist cosmetic settings in the existing adapter; never send them as authoritative game state. |
| `SetQuality(int)` / `CurrentQualityIndex` | Reflect Low=0, Medium=1, High=2 without raising an event. |
| `QualityChanged(int)` | Composition root applies its graphics service and persists this choice. View does not edit URP/global quality. |
| `UiFeedbackRequested` | Composition root may play one short UI feedback sound if audio is enabled. Static buttons are registered once by RaceScreen. |
| `BlocksGameplayInput` | True for an open settings overlay, focused text input, or explicit HUD control focus during a race. Feed neutral gameplay input and clear buffered attacks while true. |
| `OpenSettings()` / `CloseSettings()` / `SettingsOpen` | Settings state belongs to the view. Opening clears cruise. Closing during a race returns focus to the root. |
| `HandleBack()` | Returns true when it consumed a settings-close, connection-sheet-close or return from HUD control focus. Root should not also leave the race for that same input. |
| `SetGamepadNavigation(bool)` | Changes control hints and seeds home focus only when switching device mode. Does not synthesize navigation events. |
| `IsTyping` | Covers every TextField in the document, including room and join-code input. |

`MultiplayerLobbyView.UiFeedbackRequested` covers dynamic room-list buttons. Root should connect it to the same feedback sound; static lobby buttons already pass through RaceScreen's document-wide button registration.

## Input ownership and focus

The installed Input System 1.20 package supplies Unity 6 `InputForUI` automatically (`activeInputHandler: 1`). In `InputSystemProvider.SelectInputActionAsset`, absence of a project-wide UI action map selects `DefaultInputActions`. That map contains UI/Navigate (keyboard and gamepad), Submit and Cancel. A second EventSystem or manual duplicate Navigate/Submit loop is unnecessary and could process one press twice.

The default UI action map also binds WASD and the gamepad stick. RaceScreen therefore consumes NavigationMove/Submit while a race owns root focus. Tab can deliberately focus a HUD button; then `BlocksGameplayInput` makes gameplay neutral until Back returns to root. Pointer clicking cruise immediately returns focus to root. Gamepad Start should call `OpenSettings` from the composition root. Native UI Cancel dismisses the active settings/connection panel. During settings, focus is retained inside the overlay, with explicit first/last Tab wrapping.

Screen entry focuses the appropriate primary action once; snapshots never steal focus from text being typed. Repeated lobby list refreshes reuse existing rows and buttons, preserving control identity. Up to eight room/member/result rows are pooled lazily. Unknown long names are plain text and truncate with a full-name tooltip. Join-by-code becomes enabled at six characters; server validation remains authoritative. Full rooms say `ĐÃ ĐỦ NGƯỜI` rather than appearing joinable.

## Validation boundary and remaining acceptance

Completed within this UI task: source review, named-control binding check, token contrast calculation and `git diff --check` on owned files. No Unity import/play/build was run by this agent; the root agent coordinates that shared editor.

Required runtime acceptance, to be recorded by the parent report rather than inferred from source:

1. Unity compilation, USS/UXML import without errors or warnings.
2. Home/network typing, room creation/join/ready, result-pending and persisted results in the built browser.
3. Settings overlay rapid open/close, Escape/Cancel, focus restoration, slider and dropdown with keyboard; no concurrent gameplay input while using UI.
4. Actual gamepad navigation/submit/cancel and Start-to-settings on supported hardware. Provider source verification alone is not hardware acceptance.
5. 1280×720, 1366×768, 1920×1080 and ultrawide; both HUD scale extremes; reduced motion on/off.
6. Browser capture of motion and UI sound, plus a first-time-player usability test. No new participant test or screen-reader support is claimed here.

P05's physical-LAN and cross-network acceptance gaps and the measured remote collision-presentation residual are unaffected by these UI changes.
