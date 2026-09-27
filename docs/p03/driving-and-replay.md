# P03 — Driving core và replay

Ngày 2026-09-21. Phần này mô tả core C# đã chạy test; nghiệm thu hình ảnh/camera/Web được ghi riêng bởi bước tích hợp Unity. Đây là cơ chế lái mới có tham chiếu các kết quả P01, không phải bản sao toàn bộ physics Road Rash.

## Nội dung đã triển khai

`Packages/com.racingbois.foundation/Runtime/Definitions/TrackDefinition.cs` định nghĩa route gốc mới dài **2.200 m**, rộng 13 m, vai đường mỗi bên 2 m, lane center ±3 m. Route có 11 đoạn: thẳng, cua rộng/hẹp, lên/xuống dốc và hai crest có thể làm xe rời mặt đường. Bán kính nhỏ nhất khoảng 139 m; gradient −55 đến +80‰. Tọa độ route tăng tuyến tính, không wrap ở đích. Hướng/position liên tục tại các điểm nối; thay đổi gradient tại crest được chủ đích dùng cho bài jump. Chưa coi đây là spline cảnh quan/art cuối P06.

Simulation chỉ đọc curvature/grade/elevation bằng số nguyên. `TrackDefinition.Sample` dùng lượng giác cho vị trí/hướng render, không quyết định gameplay. Road-space dùng mm, mm/s, tick 60 Hz; phép tích phân giữ remainder. Các giá trị world-unit này **không phải phép đổi đã được chứng minh từ raw velocity/longitudinal của bản gốc**. [DISPLAY_UNITS](../p01/assets/DISPLAY_UNITS.md) phân biệt displayed mph/miles với mét vật lý.

`DrivingDynamics` có throttle curve giảm torque theo vận tốc, drag, braking, traction offroad, filtered steer, lean và gear hysteresis. Rời vai đường ở tốc độ cao gây crash; tốc độ thấp bị chặn ở biên. Crest làm airborne khi chênh grade ≥60‰ và speed >32 m/s; gravity và height relative road quyết định landing. Collider tương đối được quét bằng slab AABB Q16; không chỉ test overlap ở vị trí cuối tick.

| Tham số mới | Giá trị / chủ đích |
|---|---|
| Tick | 60 Hz, tách render; phù hợp clock đã xác minh P01 |
| Top speed player | 58 m/s = 208,8 km/h; opponent 53–56 m/s |
| Full brake | 23 m/s² trước drag/grade |
| Steering response | Tiến tối đa 95 permille/tick tới input mục tiêu |
| Road edge / outer guard | ±6,5 m / ±9,3 m |
| Offroad | Engine 40%, drag tăng 3 m/s²; thêm drag khi >34 m/s |
| Bike contact | Motorcycle half-width0,475 m/half-length1,07 m/height1,2 m; pair Minkowski box dùng tổng hai half-size |
| Traffic contact | Coupe2,160×4,540×1,360m; van2,310×4,640×2,290m; cộng bounds motorcycle theo từng trục |
| Crest gravity | 164 mm/s giảm vertical velocity mỗi tick (~9,84 m/s²) |
| Hard landing | Relative vertical impact >10,5 m/s gây crash |

Tuning nằm trong `GameplayRules`, `DrivingDynamics`, `TrackDefinition`; P02 `PrototypeRules`/`RoadSpaceSimulation` được giữ nguyên để không phá chứng cứ transport ban đầu. Không dùng Unity PhysX làm authority và không giả định PhysX native/WASM deterministic.

`VehicleDimensions` lấy từ LOD0 bounds của assets mới Blender: bike mesh950×1.196×2.120mm, centerZ−10mm nên chọn half-length1.070mm và height1.200mm để phủ hết mesh (10mm/4mm conservative margins). Coupe/van dùng height thật, tránh airborne bike xuyên phần trên van. Traffic collider height xét chênh road elevation của hai object, khoảng giao bikebottom với vehicle vertical interval. Test bikebottom2m đi qua coupe nhưng va van, và lateral1,58m chỉ va van. Proxy gồm cả mirror bounds nên có thể chạm sớm ở bộ phận rỗng; dùng box conservative được chủ đích chấp nhận ở graybox.

## Hợp đồng tích hợp

`RaceSimulation.CreateDefault(seed:1996,botCount:5,level:0)` tạo world. `AddPlayer` nhận ID 1–999, tối đa 8 player; bot ID 1001+, cop 2001. `SetInput` nhận permille và side −1/0/+1, `Kick`; input stale sau 30 tick trở thành neutral. `Step(world)` chạy đúng một tick. Biến thể `Step(world, inputs[])` dùng index khớp `Riders[]`, không dùng player ID làm array index.

World/riders là mutable state thuộc đúng một simulation owner. Client Application/Server phải copy sang readmodel/snapshot, không giao state core cho Presentation. `HeightMillimeters` và `BikeHeightMillimeters` là độ cao **trên mặt route**, phải cộng độ cao `Track.Sample` khi render. `BikeDistance/Lateral` tách khỏi rider khi recovery.

Thứ tự mỗi tick: tăng clock → nhận input/AI → movement → traffic → swept contacts → combat → police bust → finish → rank. Rider array duy trì thứ tự ID; finish cùng tick dùng ID thấp trước. `Events` chỉ chứa tick hiện tại; server 20 Hz phải lưu ring các event vừa phát trước khi tạo snapshot. Event ID tăng đơn điệu, dùng deduplicate VFX; đây chưa phải durable event journal.

## Kiểm chứng chạy được

```powershell
dotnet run --project src/Tests/RacingBois.Gameplay.Tests -c Release
```

[gameplay-validation.json](gameplay-validation.json) ghi **31 tests PASS**, 0 failures, runtime và SHA-256 từng source core/test. Bộ test bao gồm các điều kiện tuyến đường/lane/offroad/braking, input timeout, crest flight→landing, traffic đi xuyên từ phía trước sang sau trong một tick (vẫn bị swept contact chặn), recovery, combat, AI, police, pedestrian và race result. Crash khi đang cao2m giữ height rồi rơi theo gravity, không snap xuống ground. Soak301.000tick bổ sung xác minh actorID wrap không đụng namespace/active actor.

Fixture replay seed1996,5bot,level2 chạy **20.000tick** trên hai world độc lập, so rolling hash từng tick và khóa golden **`3F421751C31690CB`**. Hash bao gồm trạng thái rider/traffic/pedestrian/event, cảhai PRNG stream và bounds traffic; input được tạo từ scripted controller cố định. Replay này cố tình đổi lane/đánh/đạp, player bị wreck ở1.726,611m, cả5bot về đích: không dùng nó làm bằng chứng mọi người đều thắng. Golden được khóa sau khi sửa natural cop stopping-distance, held-attack cadence, airborne crash continuity, proxy khớp asset bounds và bổ sung pedestrian baseline.

Fixture khác bù cua và giữ tim đường hoàn thành route ở **tick2.585 /43,083s**, hạng1, health3.136, bike condition100. Đây là controller test có traffic/opponents, không phải human playtest hoặc thời gian khớp bản gốc. Khoảng chấp nhận authored completion là40–150s; P01 chưa cung cấp full-physics scale để tuyên bố tolerance so với game gốc.

`GameplayVerification.Run()` chạy riêng một world3000tick, trả immutable `{Passed,Hash,ExpectedHash,Ticks}`; expected **`ED162155D421B3CF`**. Không chạm live session, filesystem hay testframework. Có thể chạy trực tiếp trong Unity/IL2CPP/Web startup để so hash native. Optional observer xuất immutable frame mỗi tick. Lệnh test trên cũng ghi [gameplay-replay-timeline.json](gameplay-replay-timeline.json), chứa cả3.000input và state/hash sau mỗi tick để tìm tick đầu khác nhau; không dùng demo autopilot thay input người chơi.

| Thời gian full throttle đường thẳng | Speed (m/s) | Distance (m) |
|---|---:|---:|
| 1 s | 9,908 | 5,159 |
| 2 s | 18,417 | 19,503 |
| 3 s | 25,689 | 41,713 |
| 4 s | 31,878 | 70,633 |
| 5 s | 37,126 | 105,251 |
| 6 s | 41,563 | 144,695 |

Từ mốc 6 s, full brake mất **107 tick / 1,783 s**, quãng dừng **36,258 m**. Các con số này thuộc tuning mới, không được gắn nhãn recovered curve. P01 native sample 3.987→0 trong ≤36 tick vẫn ở raw units/thiết lập thí nghiệm khác.

Benchmark .NET Release dùng12world seed khác nhau, mỗi world8player+6bot+1cop và các pool traffic/pedestrian, mỗi world chạy1.000tick active. Native time của mỗi lần chạy được ghi trongJSON, thay đổi theo tải CPU; **0managed bytes được cấp phát trong core tick**. World construction, snapshot/serialization, Unity rendering, WASM, audio/GPU không nằm trong số này. Không dùng native microbenchmark thay gate browser1080pFPS/memory/CPU/GPU.

## Các gate chưa được chứng minh bởi tài liệu này

- Full original physics parity: toàn bộ 89 SPEC fields, nitro, traction/slope/collision branch và phép đổi raw units vẫn mở ở P01.
- Camera/player feel, sustained manual driving trong Web, đo CPU/GPU/frame-time/resident memory cần báo cáo Unity/browser riêng.
- Cross-runtime golden native↔WASM cần chạy chính fixture trên hai runtime; hai instance .NET chỉ chứng minh repeatability cùng runtime.
- Không có original sprite/texture/sound nào được dùng để tạo route hoặc core.
