# Racing Bois — P01 native logic evidence

Ngày 2026-09-21. Binary nguồn `RacingBois.exe` SHA-256 `66ab853c5b7b73b82a7c22a0478f5ba5b1066ed27028ef96449f5fe36a6101c5`. Nguồn chỉ đọc. Mọi dữ liệu trong thư mục này phục vụ nghiên cứu; không đưa assets gốc hoặc bản chuyển đổi vào production.

**P01 chưa đạt gate toàn bộ logic.** Đợt này chuyển nhiều kết luận từ chỉ đọc assembly sang kiểm tra thực thi instruction gốc, bổ sung clock, input, gear, surface, qualification và recovery. Phải phân biệt ba loại bằng chứng:

**Bổ sung sau baseline:** đã có native hit/damage cả4IDs, weapon transfer, police/Busted trace và4.001 AI eligibility fixtures. Xem [NATIVE_CONTACTS_AND_AI.md](NATIVE_CONTACTS_AND_AI.md); các mục combat/AI baseline bên dưới phải đọc cùng bổ sung này. Tổng instruction-level cases hiện6.075;100% logic vẫn mở.

1. **Static CFG:** project SQLite có thể mở lại và truy vấn, instruction bytes/VA, call graph và nhãn có nguồn. Không phải source nguyên bản.
2. **Original-instruction component execution:** chạy các routine x86 từ PE bằng Unicorn; bộ nhớ đầu vào kiểm soát; không thực thi Windows imports. Fixtures ghi mọi hook và kỳ vọng. Đây là kiểm chứng component, không phải gameplay capture.
3. **Instrumented native process:** chạy bản sao EXE với Frida và registry ảo, ghi các entry thực sự chạm tới. Startup/DirectDraw không đồng nghĩa một trận đua chạy được.

## Project phân tích lưu được

- [native-analysis.sqlite](native-analysis.sqlite): bảng `metadata`, `functions`, `instructions`, `membership`, `edges`, `unresolved`.
- [analysis-project.json](analysis-project.json): source hash, số lượng, roots, giới hạn.
- [callgraph.json](callgraph.json): callsite, caller, callee, import.
- `functions/*.tsv`: bytes chính xác và assembly theo alias analyst, các blocks reachable, bao gồm tail/shared blocks nếu reachable.

Số lượng cuối được ghi trong [analysis-project.json](analysis-project.json): 1.061 entry candidates, 71.395 unique instructions, 91 alias analyst, 529 indirect edges chưa resolve. Các con số này **không phải phần trăm parity**. Recursive traversal tránh coi mọi jump-table byte là instruction như linear sweep P00; tuy nhiên function pointers, callback tables và control-flow chưa được chứng minh đầy đủ. Switch lấy bound từ local `cmp` được đánh dấu candidate. Nhãn `candidate` và numeric behavior IDs không được tự biến thành tên production.

Ví dụ truy vấn lưu được:

```sql
SELECT printf('0x%x', source_va), printf('0x%x', target_va), kind
FROM edges WHERE function_va = 0x44b2e0;
```

## Clock và thứ tự cập nhật

`0x448243` lấy `QueryPerformanceFrequency` vào `0x4753e8`. Scheduler `0x4163d0`, tại `0x416526..0x416543`, chia frequency cho **60**, lưu số counter units/tick. `0x4165c1..0x41660e` lấy elapsed counter chia quantum đó, trừ số ticks đã xử lý, tính batch tiếp theo; batch thường được giới hạn 20. `0x442e10` xử lý messages/input rồi gọi `0x44b2e0` với số tick.

`0x44b30c..0x44b31e` tăng `0x4b7ecc` một đơn vị trước mỗi call `0x44b3b0`. Dispatcher có các divider 2 và 3 ở `0x44b3b0..0x44b3f7`; không suy rằng mọi object update đều chạy một lần/tick. `0x437860..0x43787c` độc lập đổi race tick sang hundredths bằng `ticks*100/60`.

Vì vậy **clock gameplay danh định 60 Hz**, tách khỏi render FPS. Các native race traces bên dưới xác nhận median60Hz trong môi trường thử. Network phase có hiệu chỉnh tick quantum; jitter, stall và scheduling các điều kiện khác vẫn còn mở. Không coi frame video là tick.

| Rule | Tick | Thời gian danh định | Điều kiện |
|---|---:|---:|---|
| Protection sau chuyển weapon | 300 | 5 s | `0x409888`; steal gate so sánh strict clock > timestamp |
| Hit cooldown level 0..4 | 30/24/18/12/6 | 500/400/300/200/100 ms | `0x40997c..0x40999c`; equality vẫn bị chặn |
| Recovery state timeout | >1.200 | >20 s | `0x40a650..0x40a65d`, nhiều điều kiện state/ownership |

## Movement, surface và gear

Các field sau vẫn ở **đơn vị nội bộ**, chưa quy đổi sang mét, km/h hay Unity world units:

| Field | Kết luận có code | Evidence |
|---|---|---|
| Object+0x1c | tiến dọc tuyến, traverse linked segment khi đổi block 256 đơn vị | `0x439390..0x4394bd` |
| Object+0x28 | tọa độ ngang, so sánh boundary sau `>>8` | `0x43a0c0` |
| Object+0x20 | trục dùng trong height/hit test; scale vật lý chưa khóa | `0x409c6d` và road/collision chain |
| Object+0xec | velocity dọc tuyến | `0x4390c0`, `0x43972b..0x439817` |
| Object+0x114 | drive/brake term | `0x40acd0`, `0x40adb0`, `0x40aea0` |
| Object+0x118 | steering/traction penalty term | `0x438c70`, `0x439122` |
| Object+0x23c | gear slot, clamp 0..6 | `0x4391d0` |
| Object+0x240 | throttle/brake ramp state | `0x40adb0`, `0x40aea0` |
| Object+0x288 | filtered steering term | `0x40af50`; combat also adds impulses here |
| Object+0x18 | update interval in simulation ticks | multiplies velocity/drive changes and behavior clocks |

Gear hysteresis routine uses 16-byte slots: `+0x1d0+16*g` drives positive torque, `+0x1d4+16*g` is upper shift threshold, `+0x1d8+16*g` lower threshold. It moves **at most one slot per call**, strictly above upper/below lower; equality keeps the slot. A slot count of seven does not establish seven real forward gears, because neutral/terminal slots require interpretation of data and UI.

Surface classifier returns numeric 0..3. It compares lateral `>>8` to segment+0xe0/e4 (inner) and +0xe8/ec (outer), with material+0x3c and flags+0x37. The inner interval uses strict inequalities. The full branch matrix is covered by 256 native-byte fixtures; names such as asphalt/gravel/grass remain unassigned until source material mapping is complete.

Velocity component at `0x4390c0`, contact field=0 branch:

```text
drag = (coefficient_150 * ((abs(v) >> 2) >> 8)) >> 8
steerLoss = trunc(abs(field_118) / 16)
a = drive - drag - steerLoss            if v >= 0
a = drive + abs(drag + steerLoss)       if v < 0
next = v + a * updateTicks
if v >= 0 and next <= 0: next = 100 if drive > 0 else 0
if v < 0 and next > 0: next = 0
```

The tested range avoids integer overflow. Ground contact adds material resistance and constant drag; traction, cornering and airborne collision are not reduced to this one equation. `0x43972b..0x439817` integrates longitudinal displacement using `(2*v - a*dt)*dt/2`, then division by256 before segment traversal. Lateral integration uses a different scale.

[bike-component-bench.json](bike-component-bench.json) initializes all 15 exact SPEC payloads using original `0x405ea0`, executes throttle→velocity→gear components for 1.800 ticks and brakes to zero. It records per-second values and the seven slots per SPEC. All 15 reached zero under the component setup. Rider initialization parameter75 is an **explicit experiment input**, not a claimed recovered character mass. This is not a measurement of real race acceleration/top speed: the entire object dispatcher, traction, slope, nitro, collision and rendering are outside the bench.

## Input, combat và recovery

`0x440410` reads a 24-byte mailbox by rider slot: payload DWORD+5 and availability byte+9. First read clears availability, second returns0. This is a consume-once mailbox; it cannot directly be used as a held-key state in the new client.

Local-player handler `0x434660` xác nhận bit0x1=throttle,0x2=brake,0x4 và0x200 là hai hướng lái. Nhánh input bị bỏ qua nếu `0x4753c8 != 0` (attract/demo), chuyển qua behavior controller. Native probe đã phát hiện và tách rõ trace autopilot trước khi đo điều khiển bàn phím; không dùng trace đó để kết luận throttle/brake.

Combat range/damage formulas P00 are now executed from original instruction bytes. There are 960 strict-side/range boundary cases, 112 damage-producer cases and24 damage-pool/ownership cases. Damage-producer tests capture the downstream call `0x4052c0` instead of pretending animation/network recipients ran. Pool fixtures separately cover accepted ownership2 and ignored ownership−1, positive damage/clamps. Other ownership/network branches remain open.

Recovery routine `0x40a600` meaning is substantially clearer:

- State `object+0x2f4 == 2`, animation `rider+0x80 == 0x26`, behavior8 is the running/recovery branch.
- `0x40a9d0` returns **1.200 internal velocity units**.
- Near-bike check: `abs(bike.longitudinal-rider.longitudinal) <= 9`, because `1200/128` truncates to9; `abs((bike.lateral-rider.lateral)-6000) <= 6000`.
- With condition>0 and near bike, both lateral positions become old rider lateral+6000, rider velocity becomes0, animation0x29 is requested, state becomes3.
- With condition0 and near bike, animation0x25 is requested; no successful remount.
- State3 waits until animation is no longer0x29, then calls `0x404560`, which restores state0, rider condition pool and riding parameters. Animation completion timing remains unmeasured.

50 recovery boundary fixtures execute the full decision routine but stub the two animation setters. They prove numeric branch behavior, **not the animation or recovery duration in a race**.

Animation runtime `0x43ae90` dùng20-byte frame descriptors; duration ở+0xc là signed byte. Deadline đầu=`clock+duration`; equality `clock==deadline` đã advance. Mỗi call advance tối đa một frame, deadline sau cộng duration frame mới vào deadline cũ, không cộng vào clock hiện tại. Flags+0xd low nibble0 advance tuần tự;1 với queuedID255 loop tới high nibble và tăng loop count; các nhánh khác chuyển queued animation/reset frame. 28 native-byte fixtures kiểm tra equality, clock nhảy xa, loop/queued transition. Kết hợp loader CANS raw+8 chia20, positive valid duration có thời gian danh định `trunc(raw/20)/60` giây; không diễn giải rawvalue trực tiếp là milliseconds.

Behavior dispatch table `0x465980` has ten code targets, indexed by `rider.link_1d8+0x160`. State0 and9 are no-ops;1 is navigation candidate;2 tail-jumps to1;3 uses attack choice;4 pursues a target;5/6/7 update target coordinates;8 is recovery. Labels for police vs opponent roles, aggression, avoidance and every transition remain open. This table must not be advertised as the complete AI FSM.

## Finish, qualification và campaign

`0x437800` sets bit0x10 on rider/bike and appends (rider pointer, clock) to a finish table, unless already flagged. `0x437860` increments result count; local finish-position byte is zero-based. Order is the call order into this routine; resolving simultaneous physical crossings at the higher dispatcher remains open.

`0x416010` request0x7f resolves outcome2 if offline finish index<3, outcome3 otherwise. A nonzero network flag changes the qualifying threshold to index<1. `0x416120` maps outcome2→UI transition0x1e,3→0x1f,4→0x1d, other→0x1c. `0x449150` maps0x1c→Wreck,0x1d→Busted,0x1e→Win/Level/Final,0x1f→Lose using source literal pointers. Only transition0x1e ORs the selected course bit, and mode3 skips that OR. Thus **offline top-three qualification is now connected across the outcome→UI→mask chain**, with 28 threshold and60 course-bit native-byte cases.

Qualification mask is accepted only when exactly31 (`0x1f`), not any superset. Level0..3 increments, level4 requests final transition; 35 cases cover masks including invalid extra bits. Menu handlers, currency rewards after every possible end condition, save-tail semantics, and full campaign playthrough still need trace.

## Native compatibility probe

[native-probe-first-attempt.json](native-probe-first-attempt.json): actual copied EXE reached application initialization, attempted legacy `Lalloc.VXD` (blocked device path), then displayed **Could not find any CD-ROM drive** and exited.

[native-probe-system-ddraw.json](native-probe-system-ddraw.json): virtual CD drive/cwd and in-memory game registry allowed content initialization. DirectDrawCreate succeeded. The native renderer requested exclusive flags83 and 640×480 at8-bit then16-bit; display mutation guard blocked both, so no gameplay tick was reached.

[ddraw-provenance.json](ddraw-provenance.json) pins upstream cnc-ddraw7.1.0.0 ZIP/DLL hashes. Only `ddraw.dll` and a task-specific GDI/windowed640×480 configuration are extracted into ignored `tools/p01/logic/runtime-copy`. No installer, global DLL registration, system registry import, launcher or batch execution. This upstream explicitly supports Road Rash and actual windowed mode; [official repository](https://github.com/FunkyFr3sh/cnc-ddraw). Frida interception follows its [official API](https://frida.re/docs/javascript-api/).

Windowed wrapper vượt qua gate đồ họa. Probe race đầu gặp null-surface exception `0x41df62`, caller `0x424292`: timer credits còn sống sau khi harness bỏ qua menu. Đây là lỗi điều kiện khởi tạo của probe. Cancelling timers1..16 của **chính window game** trước transition course khép lỗi này; gameplay routines không bị thay thế.

Đã chạy native có kiểm soát: bỏ qua media/menu trước đua, đặt mode2/character1/level0/bike4/course1, tắt attract/demo và joystick, cấp input bits tại kết quả hàm polling. Ba bài brake/steering/combat ép CRT seed1996. Trận vẫn chạy renderer, physics, gear, road, traffic, animation và collision nguyên bản. Đây là khởi tạo test được công bố, không chứng minh luồng menu/campaign tự nhiên.

| Bài đo native | Kết quả thực đo | Giới hạn |
|---|---|---|
| Keyboard drive/crash/recovery |46 samples tick30..1380; idle0; throttle722@150,3987@300,7785@600; crash observed state1@660→state2→state3→state0@1350 | không lái nên ra lề/va chạm; không dùng làm straight-line max-speed; trace này chưa cố định seed |
| Brake |182 samples tick6..1092; 3987 internal velocity ở tick300; brake first sampled stop336; lặp900→936 | stop trong≤36ticks/0.6s, độ phân giải6ticks; mọi sample state0 |
| Steering |131 samples tick6..786; bit0x4 → steer−5053@270; bit0x200 → +6689@330; đổi hướng trở lại rõ ràng | raw units; road curvature vẫn hoạt động; mọi sample state0 |
| Combat animation |132 samples tick6..792; input0x20 animation22,20ticks;0x40 animation26,24ticks;0xA0 animation24,80ticks | không có target bị hit; không có damage call, không coi là damage/steal parity |
| Clock |median observed60Hz trên cả4 trace | instrumentation/renderer wrapper hoạt động, không phải benchmark hiệu năng browser |

[native-trace-summary.json](native-trace-summary.json), `native-*.csv`, [native-probe-keyboard-trace.json](native-probe-keyboard-trace.json), [native-probe-brake.json](native-probe-brake.json), [native-probe-steering.json](native-probe-steering.json), [native-probe-combat.json](native-probe-combat.json) giữ clock, input, state, đơn vị nội bộ và các thay đổi animation. Không có exception trong ba bài đo cuối.

Baseline11 frame buffers640×480, cộng7 frame bổ sung hit/steal/police, được lấy trực tiếp trước DirectDraw Unlock trong process game, cùng palette thực, rồi decodePNG: [chỉ mục18frames](native-frames/index.json). [Frame tick600](native-frames/tick-000600.png) và[police scenario tick300](native-frames/police/tick-000300.png) đã xem và xác nhận scene/rider render đúng; đây là scene buffer trước ghép HUD, không phải desktop screenshot và không phải video60fps. Các ảnh là research-only.

API containment không phải OS security sandbox; nó bao các import đã kiểm tra, chặn network/child-process, ảo hóa registry game và giới hạn file mutations trong bản sao. Mỗi run kết thúc đúng PID đã spawn. 374/374 file gốc được đối chiếu hash/kích thước/tập đường dẫn; không file nào thêm/xóa/sửa. Các native run cuối không sửa file trong bản sao.

Kiểm tra cleanup phát hiện game nạp bốn font bằng API đăng ký font session-wide. Đã gỡ đúng44 registration refs từ **đường dẫn runtime-copy do task tạo**, không đụng font gốc/installed fonts; [biên bản](native-font-cleanup.json). Harness hiện thay hai API font bằng `AddFontResourceExA/RemoveFontResourceExA` với `FR_PRIVATE`; font chỉ trong process, tự hết khi process đóng. [Probe riêng sau sửa](native-probe-private-fonts.json) đã nạp cả bốn font thành công bằng flags16, khởi động tới content và DirectDraw, không exception. Không còn process RacingBois do task để lại.

## Remaining P01 gates and decisions

| Gate | State | Next evidence |
|---|---|---|
| Saved disassembler/call graph project | PASS, bounded coverage | Resolve 529 indirect edges as required by remaining behaviors |
| Clock nominal units | PASS static + native median60Hz | Other scheduling/network conditions remain open |
| Component formulas and boundaries | PASS 2.074 gameplay +4.001 AI fixtures | Broaden input/ownership domains only for uncovered behavior |
| All 15 bike component exercise | PASS | Real straight-line/slope/corner/brake traces with matched controls |
| Actual controlled native launch | PASS for bounded original-race scenarios | Full user-driven menu/campaign and video capture remain open |
| Physics/collision/airborne | OPEN | Full update ordering, surface/collision data and measured movement |
| AI/police/traffic | PARTIAL; live roles/active1..5/8/9, attackeligibility andBusted traced | Complete relationship/avoidance/spawn and6/7 reachability remainopen |
| Combat/recovery | PARTIAL; native4-ID damage, cooldown equality, weapon2 transfer andcrash/recovery observed | All natural-motion/weapon variants, network branches, more recovery conditions |
| Outcomes/qualification | PARTIAL | Top3/mask chain validated; race ordering/economy/whole progression trace |
| Menu/UI/audio/video flow | OPEN | Every state transition and media trigger, input behavior |
| Mod-vs-PC differences | OPEN | No vanilla PC executable; video alone cannot prove code identity |
| 100% logic | OPEN | No unresolved required behavior and differential gameplay fixtures |

Decision: P02 may create a replaceable simulation skeleton and toolchain/transport spikes using versioned provisional rules. Do not freeze these recovered numeric internals as final Unity meters or claim parity. P03/P04 require the outstanding P01 gameplay measurements to be completed or a deliberate product behavior decision to be recorded.
