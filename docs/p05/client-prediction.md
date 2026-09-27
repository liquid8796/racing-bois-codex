# P05 — Client, prediction và vòng đời phiên

`MultiplayerSession` là Application thuần C#, tách khỏi `RaceSession` dùng cho local practice. Client không gửi position, damage, health, finish hay credits làm sự thật. Các port transport, codec, clock và storage không phụ thuộc Unity.

## Đồng bộ tick

- Protocol v3 `MpInput` mang `sessionEpoch`, `raceEpoch`, sequence và `targetTick`. Target tick1 là bước mô phỏng60Hz đầu tiên tại `startServiceTick`. Server không diễn giải một gói input thành một khoảng thời gian tùy ý.
- Server chỉ tiêu thụ input đúng tick. Khi thiếu, giữ **analog của frame cuối đã thực thi** tối đa6tick, sau đó neutral; không lặp attack từ fallback. Frame tới muộn được resolve/expire, không rewind gameplay.
- Snapshot sau tickS mang `resolvedThroughTick=S`, `lastProcessedSequence`, `lastAppliedInputTick`, held analog và own checkpoint. `lastProcessedSequence` không phải latest intent received.
- Client khôi phục checkpointS rồi replay đúng các target tick>S đã gửi. Các tick trống dùng cùng fallback6tick. History tối đa120frame/120tick; không cho tab treo fast-forward cả quãng thời gian đã mất.
- Target liên tục chỉ được giữ khi còn vượt **arrival floor**: estimated room tick + RTT/2 + jitter +2tick dành cho queue/processing. Chỉ kiểm tra “target vẫn ở tương lai” là sai: native matrix đã thấy180–501late frame/~750 vì uplink đến sau deadline. Bản sửa dùng `max(nextContiguous, arrivalFloor)` và ceiling room tick+17, cho phép batch20Hz mà vẫn nằm trong server future window18tick. Countdown dùng room timeline âm để prime được tick1.
- Ping/pong dùng monotonic clock. Lead clamp2–16tick từ RTT/2+jitter+2tick; server future window18tick. Countdown chỉ prime các input đầu gần thời điểm go và không render chuyển động trước lịch start.
- Snapshot tick0 lặp trong countdown3giây vẫn phải cập nhật clock/freshness. Test integration đã bắt và sửa lỗi bỏ qua các snapshot này khiến timeout nhầm ngay trước xuất phát.

`RiderCheckpoint` bất biến: construction data là struct toàn value, propertyData trả bản sao. Checkpoint giữ toàn bộ public rider state, các remainder tích phân, filtered steering, vertical velocity, bike slide, recovery/bust timers, cooldown, attack gate và stored input. Previous-position fields được chụp lại tại mỗi bước; AI fields không dùng trong predictor player.

`RiderPredictor` gọi cùng `DrivingDynamics.Step`, swept `ResolveContacts(onlyRiderId)` và `CombatResolver.BeginAttack`. Sau native test phát hiện overshoot lớn khi va traffic, predictor đã bổ sung proxy rider/traffic/pedestrian gần nhất từ snapshot đã validate, copy vào fixed arrays riêng và cập nhật previous/current position từng tick. Traffic dùng đúng `VehicleDimensions`; actor velocity/acceleration lấy từ snapshot/history với clamp. Proxy chỉ dùng tối đa30tick tuổi, không tự spawn hoặc chạy AI.

Contact prediction chỉ quyết định pose/motion của own rider. Không resolve combat damage/steal/finish/reward; không gửi collision/hit claim. Biến động health nội bộ của helper khi crash/remount không được đưa vào HUD; `WithMotion` chỉ lấy motion, locomotion/attack pose. Health, bike condition, inventory weapon, rank, reward, qualification và event thật vẫn lấy từ authority. Wreck dự đoán chỉ hiện Falling cho tới khi server xác nhận Wrecked. Snapshot tiếp theo xóa được cả false collision và proxy đã despawn.

`CheckpointMapper` thuộc assembly mới `RacingBois.NetworkMapping`, tham chiếu Protocol+Simulation; hai assembly nền tảng không tham chiếu lẫn nhau. Server và client dùng chung một mapper, validator có giới hạn các enum/position/remainder/timer/input.

## Presentation

`SamplePresentation()` trả immutable `RaceWorldReadModel`, cùng `LocalRider` đã dự đoán. Root view đặt `ActorsAlreadyInterpolated=true` để không Lerp thêm lần nữa. Mỗi mẫu cache theo predicted tick, revision snapshot/event và bước smoothing60Hz; render333fps không tạo333bộ readmodel/giây khi tick không đổi.

Remote history tối đa32snapshot. Nội suy theo timestamp khi có cặp bao quanh; sau snapshot cuối, ngoại suy motion tới tick presentation của local, tối đa30tick/500ms rồi giữ nguyên. Horizon này bao gồm cả tuổi snapshot chiều xuống và input lead tương lai; cap18tick ban đầu không đủ cho250msRTT+jitter. Nếu own prediction vượt horizon proxy thì giữ nguyên presentation cuối, không tiếp tục chạy qua obstacle cũ. Spawn/despawn chỉ đổi tại boundary; không nội suy giữa các mode khác nhau.

Reliable Crash/Wrecked/Busted/Landed mới hơn snapshot giới hạn horizon của actor bị ảnh hưởng tại EventTick: không kéo tiếp velocity Riding qua một crash đã được xác nhận. Event cũ/duplicate không thay authority; snapshot mới hơn tự bỏ cap. Nếu local có confirmed crash nhưng predictor còn giữ pose lái (ví dụ melee chết cùng lúc), local tạm giữ pose checkpoint đã tính ở EventTick, từ ring121value checkpoints. Cách này tránh chỉ dừng đối thủ rồi tạo lệch tương đối với local; không tự đổi HP/mode/kết quả từ event.

Correction local cùng mode, nhỏ hơn4m được blend120ms; tổng offset cũng giới hạn4m. State boundary hoặc correction lớn snap về authority. Đây là presentation correction, không thay collision/gameplay. `MaximumCorrectionMeters` ghi cả các correction do server xác nhận fatal hit; không được chỉ báo `LastCorrectionMeters=0` cuối bài rồi nói cả bài không có correction.

`NearCombatResidualMeters` chỉ có nghĩa khi `NearCombatResidualSamples>0`: client lưu một cặp local/remote đang cách nhau<10m tại tick render, rồi so vector vị trí tương đối với snapshot authority **cùng tick** khi nó tới sau. Không có mẫu so sánh không đồng nghĩa sai số bằng0.

`MaximumSteadyResidualMeters`/`SteadyResidualSamples` và `MaximumContactResidualMeters`/`ContactResidualSamples` phân nhóm state/contact transition để chẩn đoán. Tổng `MaximumNearCombatResidualMeters` vẫn giữ mọi outlier, không lọc bỏ collision để làm số đẹp. Native matrix trước proxy có outlier12–21m; không được dùng các số thấp của harness sau đây để phủ nhận bằng chứng đó. Cần xem lần chạy native mới sau proxy ở báo cáo backend.

`Standings` và `RacingParticipantCount` giữ toàn bộ roster/rank/DNF từ server, tách khỏi actors bị lọc theo interest. HUD không nên lấy số mesh đang render làm mẫu số thứ hạng.

## Lobby, reconnect và dữ liệu local

API chính: `Connect`, `CreateLobby`, `JoinLobby`, `SetReady`, `StartRace`, `LeaveLobby`, `BackToLobby`, `RequestLobbyList`, `Step`, `Poll`, `SamplePresentation`, `NotifyVisibility`, `Disconnect`.

- `LeaveLobby` giữ kết nối để chọn phòng khác. `BackToLobby` sau kết quả dọn hết world/history cũ.
- `Disconnect(clearLease:true)` gửi `MpGoodbye`, chờ Accepted tối đa1giây rồi mới đóng transport/xóa resume receipt. Server thu hồi lease và chuyển host ngay. Nếu không nhận ACK, UI nói rõ chưa được server xác nhận; không gọi đó là confirmed logout.
- Network drop giữ lease theo grace của server. Client retry có backoff0,5/1/2giây, tối đa3lần; chỉ reset budget sau2giây kết nối ổn định. Resume giữ rider/room, đổi sessionEpoch, xóa pending input cũ và lấy checkpoint mới. Snapshot epoch cũ bị bỏ qua.
- Reliable `Accepted/Error` từ epoch cũ vẫn phải consume/ACK sequence của lease rồi bỏ qua action cũ. Bỏ chúng trước khi advance cursor đã gây reconnect loop trong native downstream stall và được sửa bằng regression riêng. `session_replaced` dừng auto-retry để hai tab không giành lại một lease liên tục.
- Visibility loss gửi neutral rồi đóng/reserve; visibility return chỉ resume token hiện có. Không chạy bù thời gian tab đã ẩn. Room authority vẫn là server, không phụ thuộc browser chủ phòng.
- Hello nonce giữ qua retry trước Welcome để server trả lại cùng lease nếu Welcome đầu bị mất. Sau Welcome có nonce mới cho reconnect sau. Resume invalid không tự biến thành guest mới.
- Reliable lobby/event/result messages dùng sequence và ACK; duplicate không phát hiệu ứng lại. Gap yêu cầu reconnect/replay/full state; các message vượt giới hạn hoặc snapshot không hợp lệ không mutate nửa chừng world đang hiển thị.
- `resultsPending` dừng input/prediction khi server giữ world hoàn tất trong lúc retry persistence; repeated same-tick snapshots vẫn chứng minh kết nối còn sống. Không công bố result trước commit. `input_late/input_future` khôngterminal chỉ đi vào counters, không để một thông báo lỗi gây hiểu nhầm tồn tại mãi trên UI.

Port storage:

| Port | Phạm vi |
|---|---|
| `IPlayerProfileStore` | ProfileId/name/color cosmetic; không chứng minh quyền sở hữu server |
| `IProfileCredentialStore` | Capability profile do server cấp, scope theo endpoint+realm; lưu persistent |
| `IResumeReceiptStore` | Opaque resume capability theo endpoint và tab; không dùng chung receipt giữa các tab |
| `IMonotonicClock.NowSeconds` | Thời gian network/prediction; không lấy wall-clock làm tick |

Fresh guest bỏ qua saved capability, không ghi đè saved identity. Result credits là số dư tuyệt đối server trả về, không cộng reward ở client. Cả profileToken và resumeToken không nằm trong room/readmodel/telemetry. Name chống control character và `< >` markup, display≤24ký tự/room≤40ký tự. Disconnect trước Connect không truy cập store với endpoint rỗng; có regression dùng store nghiêm ngặt.

## Bằng chứng

```powershell
dotnet run --project src/Tests/RacingBois.P05Client.Tests -c Release
```

[client-validation.json](client-validation.json) có32testsPASS và SHA-256 source dùng ở lần chạy. Harness dùng **MultiplayerService thật, MultiplayerSession thật và JSON**, với transport FIFO, queued callbacks và clock kiểm soát; nó drain asynchronous persistence ở ranh giới control mà không tăng fakeclock. Đây không phải browser/WAN/LAN nghiệm thu trên nhiều máy hoặc phép đo latency disk thực.

| RTT đặt / đo | Max sai số vị trí tương đối khi combat gần | Mẫu so cùng tick | Max local correction |
|---|---:|---:|---:|
|0ms network /≈8,33ms gồm queued polling|0,030m|160|1,879m khi xác nhận fatal hit|
|150ms /≈150ms|0,230m|156|0m trong tình huống này|
|250ms /≈250ms|0,505m|153|0m trong tình huống này|

Tolerance regression cho ba bài tương ứng0,15/0,6/1,0m. Đây là hai rider với scripted input cụ thể, không phải cam kết mọi scene hoặc mọi ping đều đạt. Bài250ms cần khoảng317ms extrapolation tại mẫu cuối; stall lâu hơn phải freeze/resync thay vì kéo prediction vô hạn. TCP ordered stall không được gọi là packet-loss test.

Các checks khác: checkpoint round-trip+replay exact qua driving/airborne/recovery/attack; không alias mutable state; reject hostile internal fields; v2 Busted fine âm đúng level; create/join/ready/countdown; cache/event dedupe; interest/state boundary và stale cap; atomic snapshot rejection; mất Welcome không nhân profile/lease; resume giữ rider; suspended tab không fast-forward; explicit logout ACK và host transfer; guest không ghi đè cap; expired resume fail closed; full race→persisted results→lobby không nhân reward; upstream stall700ms có expiry/missing input và history bounded.

Các regression bổ sung:20Hz batch+600ms stall giữ kết nối; replay old-epoch reliable control không tạo gap; result IO pending không reconnect; replaced lease dừng fight;24tick future oncoming-contact sai số<20mm với proxy so với>5m nếu không dự đoán contact; false contact được authority xóa; airborne đi qua coupe nhưng va van đúng height; fixed proxy replay không cấp phát object theo tick.

Sau sửa arrival floor, hai bài20Hz có jitter ghi nguyên counters: nominal150msRTT/±20ms mỗi chiều cho0late/816và0late/813input,0future,1connection; nominal250ms/±50ms cho0late/749và0late/787,0future,1connection. Missing ticks vẫn là71/31 ở bài250ms; không xóa chúng để biến báo cáo thành hoàn hảo. Measured RTT gồm polling/FIFO nên khác nominal(≈276–320ms trong bài250ms). Native matrix phải chạy lại binary mới để xác nhận budget<5%late; harness không thay kết quả socket thật.

## Đối chiếu socket thật sau freeze

Đã đọc [backend/network-matrix.json](backend/network-matrix.json) sinh lúc2026-09-21T16:45:06+07:00 và [backend/source-manifest.json](backend/source-manifest.json). Manifest khớp `MultiplayerSession.cs` SHA`ee6c755680ab1ae361ca4bfeda4be2093b5148fe93e45922284d3b1f5083e11c` và `RemoteMotionSampler.cs` SHA`a0d48dcf5d00484fce61791b28ad4d6ca7e8d091e69eb337923256c0701a9d3f`, tức đã gồm arrival floor/proxy/event cap.

- Cả8scenario transport PASS. Loopback8 người:0late/0future. Bài250ms+jitter50 có1/720late ở một peer(≈0,14%), peer còn lại0/717; future0. Đây là pass budget input, không tự chứng nhận mọi tiêu chí hình ảnh.
- Own contact prediction giảm mạnh overshoot: max own correction trong hai peer250ms là0,066/0,695m, thay vì các outlier16m trước proxy. Steady relative residual cao nhất khoảng1,175m ở bài này.
- **Observer remote contact vẫn có outlier:** khoảng3,795m loopback,11,366m ở150ms+jitter20 và15,897m ở250ms+jitter50. Các giá trị vẫn nằm trong overall/contact metrics, không bị lọc khỏi báo cáo.
- Event cap không thể sửa đoạn dự đoán một crash còn chưa xảy ra tại thời điểm snapshot hoặc chưa được truyền tới observer. Ở hai bài latency cao, `maximumEventCappedRemotes=0`; event và snapshot tiếp theo thường đến cùng đợt sau khoảng observer đã extrapolate sai. Đây là giới hạn visual prediction còn mở, không được gọi là full matched-condition parity/stable final multiplayer feel.

[backend/live-ws.json](backend/live-ws.json) lúc16:46:04+07:00 xác nhận8client với default bots/combat/resume và actual hit: observed victim health3648, event4. Những test này chạy client ứng dụng native qua socket; browser/device/network external gate vẫn riêng. Muốn thu nhỏ observer outlier hơn nữa cần một bước validation cho remote contact prediction/handling input chưa biết; không giả rằng thêm event filter sẽ giải quyết được thông tin chưa tới.

P03/P04 golden31tests vẫn giữ `ED162155D421B3CF` (3000tick startup) và `3F421751C31690CB` (20000tick) sau khi tách helper prediction. Browser thực, transport WS/WSS/proxy và các gate hai máy/hai mạng phải đối chiếu báo cáo riêng; người dùng hiện có một máy nên không tự chứng nhận các gate môi trường đó từ harness này.
