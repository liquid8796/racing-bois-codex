# Actual Unity Windows WSS evidence

The isolated player uses the production BrowserSocketTransport, MultiplayerSession, UnityWireCodec and UnityMonotonicClock. It is a real Windows Mono player with ordinary TLS, a private guest lobby and normal authoritative inputs. It does not certify full game rendering, assets, hardware input or eight-hour stability.

## Preserved failures and fixes

- `protocol6-20260927-0640.json` failed. In about99seconds it opened14connections despite one intended resume, moved only about58m and did not receive a logout acknowledgement. Source/player hashes remained unchanged. Do not relabel this run as successful merely because TLS connected.
- A separate reproduction used the installed Unity Mono6.13 runtime and the actual transport source. With a frame synchronization context, the original sent1199/received434 messages and accumulated849 outstanding sends; without that context it received all1199. Four native I/O awaits now use ConfigureAwait(false), while Unity callbacks still execute exclusively through Poll. The corrected frame-context experiment sent/received1200/1200, with at most2outstanding messages. The permanent real-WebSocket regression fails the original and passes the fix.
- `transport-fix-20260927-0704.json` passed the strengthened native gate: exactly2opens/2welcomes, one planned resume, no unexpected reconnect,1604authoritative samples,1301post-resume samples, real progress692m, and acknowledged room leave/logout. It retains raw race-turnover rejections; it did not conceal them.
- A narrowly scoped retired-input range now prevents confirmed completed-race inputs still in flight from producing a persistent UI error. A real server-order fixture and negative controls cover unknown sequences, terminal/control errors, other rooms/sessions, running races and reused countdown sequence numbers. Raw errors and reliable acknowledgements remain observable.
- `turnover-20260927-0727.json` and its `.launch.json` passed96.594seconds with exact before/after source/player/build hashes. Two connections and one planned resume; no unexpected reconnect; leave/logout acknowledged. Raw27race_epoch and3input_late observations remain in the report; the only session cause was the planned resume, and the final session error was clear.

The final local regression at `../regression/20260927T002210Z/receipt.json` passes261groups. OCI f's148ARM groups refer to its original packaged client-test source, preceding these later client-only fixes; they do not claim coverage of the newer adapter/turnover changes. The actual native reports bind their own current client source.

The first0635native build also remains failed in its receipt: its artifact compiled successfully, but an idempotent SceneManager.SetActiveScene return value was incorrectly treated as restoration failure. A direct engine control proved the scene was already active. The builder now verifies final scene identity, and later builds record successful restoration. No global SaveAssets call is used by the diagnostic builder.

All reports omit credentials/raw packets. The public staging endpoint is the existing OCI sslip.io HTTPS/WSS host. Regional HTTP reachability and this one Windows-origin game connection are not evidence of geographically distributed gameplay or a complete P10 release.
