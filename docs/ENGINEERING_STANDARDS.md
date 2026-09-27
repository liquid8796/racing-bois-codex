# Racing Bois — Tiêu chuẩn kiến trúc và bảo trì source

Ngày cập nhật: 2026-09-22. **P02 đã triển khai các ranh giới Definitions/Simulation/Protocol, Client Application/Adapters/Presentation/Bootstrap và Server Application/Host. P07 bổ sung Server.Domain, Server.Infrastructure, storage port và career/account use cases.** Readmodel bất biến tách UI khỏi wire DTO; tests chặn dependency sai. SQLite chỉ nằm trong Infrastructure; composition root của Host chọn database, Application sở hữu transaction intent và snapshot được công bố sau commit. HTTP/password/database không chạy trên owner 60 Hz. Các pattern chưa có nhu cầu thực vẫn là hướng mở rộng, không dựng framework rỗng.

Theo yêu cầu bổ sung của người dùng, source phải có kiến trúc và design pattern phù hợp, dễ đọc, dễ dọn dẹp, dễ bảo trì và mở rộng tính năng về sau. Tài liệu này cụ thể hóa yêu cầu đó cho Unity Web C#, simulation dùng chung, .NET server có thẩm quyền và LAN offline; không thay thế [REQUIREMENTS.md](REQUIREMENTS.md), [TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md) hoặc tiêu chuẩn UI/UX riêng.

## 1. Nguyên tắc và phạm vi module

Một module có một trách nhiệm rõ, chủ sở hữu state rõ và API nhỏ. Gọi dependency tường minh; trạng thái trận không nằm rải rác trong scene, các biến static hoặc UI. Dùng composition thay cho chuỗi kế thừa sâu; interface phục vụ ranh giới hoặc biến thể thật, không tạo interface cho mọi class.

Khởi đầu bằng **modular monolith** cho account/lobby/garage/economy. Match worker là đơn vị chạy và scale riêng khi cần bảo vệ thời gian tick; vẫn cùng repository và phiên bản protocol/content. Chỉ tách thêm service khi số đo tải, failure isolation hoặc cách vận hành chứng minh nhu cầu. Không đưa message broker, distributed transactions, event sourcing hay Kubernetes vào chỉ để có kiến trúc “chuẩn”.

LAN dùng lại application/simulation/protocol của online với cấu hình host, storage và identity adapter khác. Không viết một bộ luật gameplay thứ hai cho LAN. Hệ thống account online và local profiles là hai realm độc lập; không tự đồng bộ tiền/vật phẩm offline vào online.

## 2. Assemblies và chiều dependency

Tên dưới đây là **ranh giới đề xuất**, không có nghĩa phải sinh toàn bộ project/framework trước vertical slice. Tạo assembly khi có code thực hoặc cần chặn dependency; module nhỏ chưa có code có thể giữ trong backlog.

| Module / assembly đề xuất | Trách nhiệm | Được tham chiếu |
|---|---|---|
| `RacingBois.Gameplay.Definitions` | ID gameplay, đơn vị, dữ liệu bike/weapon/route/mode đã chuẩn hóa và kiểm tra | BCL subset được cả Unity Web và .NET hỗ trợ |
| `RacingBois.Simulation` | Step tick, state rider/bike/race, movement, collision gameplay, combat, AI và finish rules | `Gameplay.Definitions` |
| `RacingBois.Protocol` | Wire DTO, message IDs, version negotiation, snapshot/event contracts | Các ID/value type cần thiết trong `Gameplay.Definitions`; không tham chiếu `Simulation` |
| `RacingBois.Client.Application` | Session state, input flow, prediction/reconciliation, lobby/shop use cases, read models và ports | `Simulation`, `Protocol`, `Gameplay.Definitions` |
| `RacingBois.Client.Presentation` | MonoBehaviour/views, camera, Animator, audio/VFX, UI presenters và read-model binding | `Client.Application`, `Gameplay.Definitions`, Unity runtime APIs |
| `RacingBois.Client.Adapters` | Unity/browser input, transport, asset loading, platform clock/storage adapters | `Client.Application`, `Protocol`, Unity/browser adapter APIs đã được thử |
| `RacingBois.Client.Bootstrap` | Tạo object graph, chọn adapter/quality/profile, quản lý lifetime | Application, Presentation, Adapters; các module này không tham chiếu ngược Bootstrap |
| `RacingBois.Server.Domain` | Invariant account/profile/ownership/wallet và transaction state | BCL; chỉ dùng ID/value type gameplay nếu thực sự cần |
| `RacingBois.Server.Application` | Account/lobby/garage/reward use cases, orchestration match, ports storage/identity/clock | Server.Domain, Simulation, Protocol |
| `RacingBois.Server.Infrastructure` | PostgreSQL/SQLite, filesystem, auth/transport implementations, telemetry | Server.Application/Domain và Protocol; phụ thuộc thư viện ngoài nằm ở đây |
| `RacingBois.Server.Host` | HTTP/WSS endpoint, composition root, config, startup/shutdown; profile OCI hoặc LAN | Server.Application, Server.Infrastructure và các contracts |
| `RacingBois.Authoring.Editor` | Export dữ liệu, validators, prefab checks, authoring tools | Definitions và public authoring contracts; UnityEditor chỉ trong assembly Editor |

Chiều chính:

```text
Client Bootstrap → Presentation / Adapters → Client Application
                                              ↓
                                  Simulation → Definitions
                                              ↑
Server Host → Infrastructure → Server Application → Server Domain

Client Application / Server Application → Protocol → Definitions
```

Quy tắc bắt buộc:

- `Simulation`, `Definitions`, `Protocol`, `Server.Domain` không tham chiếu `UnityEngine`, `UnityEditor`, MonoBehaviour, scene/prefab, DB driver, transport SDK, UI hoặc filesystem trực tiếp.
- Presentation gửi intent qua API Application; không giữ mutable simulation state, tự trừ máu hoặc gọi DB. Chỉ prediction coordinator trong Application được dùng simulation dự đoán.
- Protocol DTO không phải domain entity và không serialize toàn bộ object graph simulation. Có mapping rõ, validation độ dài/range và quyền sở hữu ở ingress server.
- Ports được khai báo ở module sở hữu use case. Infrastructure/Adapters triển khai chúng; Application không `new` concrete DB/network implementation.
- Dùng Unity `.asmdef` và `.csproj` references để compiler chặn chiều sai, không chỉ dựa vào tên folder. Editor/test dependencies không lọt vào player build.
- Game logic dùng **một nguồn C# duy nhất**; Unity và server build từ cùng nguồn/package revision. Không copy/paste file shared sang hai thư mục hoặc sửa DLL riêng mà quên rebuild bên còn lại.
- Pin compiler/language/API compatibility sau round-trip P02; target runtime của server có thể mới hơn, nhưng shared code không mặc định dùng mọi API server hỗ trợ. Không chốt profile chỉ từ việc Editor compile được.

Đề xuất tổ chức: shared package có `Definitions/Simulation/Protocol`; Unity client theo feature như `Race`, `Lobby`, `Garage`, `Settings`; server code nằm ngoài thư mục Unity runtime; Editor tooling tách riêng. Không dùng `Managers`, `Helpers`, `Common` hay `Utils` làm nơi chứa mọi thứ. Code nghiên cứu và asset extract nằm ngoài runtime/build packs.

## 3. Quyền sở hữu state và luồng tác động

Luồng chuẩn của thao tác đua:

```text
Input thiết bị → Player intent → Command có sequence/tick
   → Prediction cục bộ để phản hồi nhanh
   → Transport → Server kiểm tra → Simulation authority
   → Snapshot/event có ID → Reconciliation/read model
   → Camera/animation/audio/VFX/HUD
```

Server sở hữu vị trí/tốc độ hợp lệ, hit/cooldown/damage, rider/bike crash state, vị trí tiếp đất, quãng chạy về xe, remount, thứ hạng và kết quả. Ragdoll/particle có thể biểu diễn đẹp hơn nhưng không quyết định thời gian hồi phục hay damage. VFX có thể chạy sớm theo prediction; phải gắn event identity để confirmation/replay không nhân đôi âm thanh, impact hoặc reward.

Simulation nhận input, step duration/tick, dữ liệu content và RNG state tường minh. Không đọc `Time.deltaTime`, đồng hồ hệ thống, input device, `UnityEngine.Random`, global state hoặc thứ tự callback scene. Dùng thứ tự entity/event ổn định; quy định đơn vị, rounding và tie-break. Chia sẻ source không tự chứng minh float/physics bit-identical giữa WebAssembly và native: có cross-build replay tests và server correction.

Mỗi match có một owner của mutable state. Worker song song có thể chạy nhiều match; network callbacks đưa command vào bounded queue thay vì sửa match state đồng thời. DB/HTTP/file I/O không được block tick loop. Match finish tạo kết quả có ID duy nhất; application lưu reward bằng transaction/idempotency. Queue đầy, command trễ, restart và partial failure phải có policy rõ.

Content definitions bất biến trong một trận; cấu hình mới chỉ áp dụng ở ranh giới version/match đã chốt. Quality settings/VFX density của client không được thay hitbox, khoảng đánh hoặc tốc độ.

## 4. Design patterns dùng khi giải quyết được vấn đề cụ thể

| Pattern | Dùng ở đâu | Cách giữ đơn giản / điều tránh |
|---|---|---|
| State machine | Race phase; rider riding/airborne/crash/run/remount; session connect/load/reconnect | Transition và guard tường minh, có owner. Tách các chiều độc lập như movement/action thay vì một enum chứa mọi tổ hợp; không để nhiều flag tạo state bất khả thi. |
| Strategy | Rule mode, AI decision policy, biến thể attack hoặc vehicle behavior thật sự khác nhau | Chỉ một implementation thì dùng concrete type; không tạo hierarchy cho mỗi con số balance. Registry/factory hữu hạn, đăng ký tường minh. |
| Command | Input gameplay, create/join lobby, purchase/ready intent | Command có context và validation; client request không phải bằng chứng hành động đã thành công. Không cần generic command bus cho mọi thao tác nội bộ. |
| Domain event | Hit resolved, rider crashed, race finished, purchase committed | Event mô tả sự việc đã xảy ra; order, ID và lifetime rõ. Dùng typed event theo phạm vi match/session; không dùng global event bus khiến luồng code không truy được. |
| MVP / MVVM có chọn lọc | Lobby/garage/settings/HUD read models | MVP mặc định cho screen đơn giản; MVVM khi binding framework đã được xác minh và giảm boilerplate thật. Presenter/ViewModel test được không cần scene. Không ép cả hai pattern vào cùng màn. |
| Adapter | Browser/native transport, clock, input, content source, identity, PostgreSQL/SQLite | API nhỏ gắn với nhu cầu domain. Chọn online/LAN tại composition root, tránh `if (isOffline)` rải khắp gameplay. |
| Dependency injection | Nối application, ports và concrete implementations khi boot | Constructor injection cho pure C#; Unity component nhận dependencies qua bootstrap/serialized references được validate. Manual wiring đủ thì không cần container; không service locator hoặc reflection auto-scan mặc định. |
| Factory | Tạo match/session/entity view với config và lifetime đúng | Factory cụ thể, đăng ký compile-time; không factory-of-factories hay reflection tạo mọi class theo chuỗi. |
| Object pool | VFX/audio emitters, entity views và message buffers có tần suất cao đã profile | Có reset contract, cap, lease/return và cleanup ownership; không pool mọi object. Pool không được giữ player/session/content cũ sau match. |
| Repository + transaction boundary | Wallet/ownership/results ở server, khi giúp giữ invariant | API theo use case/aggregate; tránh generic CRUD repository che transaction hoặc `IQueryable` lọt tới UI. Không dựng event sourcing đầy đủ chỉ vì wallet có ledger. |

Không dùng Singleton làm đường tắt cho dependency. Một application có thể chỉ có một audio/config object, nhưng object đó vẫn được bootstrap sở hữu và truyền rõ. Static phù hợp với hằng số hoặc pure function không mutable state, không phù hợp với `GameManager.Instance` chứa toàn bộ session/gameplay/economy.

## 5. Data-driven content và phiên bản

Xe/vũ khí/route/AI/mode config có ID ổn định, schema version, units, range và cross-reference validation. Authoring có thể dùng ScriptableObject trong Editor; trước runtime server phải export sang contract thuần dữ liệu, không bắt server đọc Unity asset hoặc GUID scene. Không serialize dictionary/type tùy ý từ nguồn không tin cậy.

Manifest release phân biệt `applicationVersion`, `protocolVersion`, `simulationRulesVersion`, `contentSchemaVersion`, `contentHash` và `saveSchemaVersion`. Chỉ thêm trường version có trách nhiệm cụ thể; không dùng một số build để ngầm đại diện tất cả. Handshake xác nhận bộ rules/content phù hợp; snapshot/replay lưu phiên bản cần để tái hiện. Bản cũ bị từ chối bằng thông báo rõ hoặc qua migration đã test, không tự load “gần giống”.

Build content là pipeline có validate → export → hash → package → browser/server integration check. Khi có thể, cùng input tạo cùng artifact; ghi khác biệt do compiler/platform thay vì tự tuyên bố reproducible. Runtime không tải script/code gameplay tùy ý từ VM để lách build/version control.

Database/save migrations có thứ tự, fixture của phiên bản cũ, backup/restore và compatibility window. Rollback app không mặc định rollback được schema phá hủy. LAN export/import phải có version và integrity validation; integrity checksum không biến dữ liệu người dùng tự sửa thành dữ liệu online đáng tin.

Production assets được làm mới từ đầu theo REQUIREMENTS; source design/`.blend`/audio/UI mới được trace tới asset ID. Extract/reference dùng nghiên cứu, không là dependency runtime. Dùng cùng manifest kiểm soát content Unity client, OCI server và LAN package.

## 6. Giới hạn Unity Web, AOT và bất đồng bộ

Tài liệu Unity Web hiện nêu C# managed threads không được hỗ trợ; timer dựa vào thread và timeout của `CancellationTokenSource` có hạn chế; Web AOT không hỗ trợ `Reflection.Emit`. Vì vậy không dùng thread/timer/JIT như giả định nền tảng của shared/client code. Tài liệu được đọc ở nhánh 6000.0; phải xác minh lại trên Editor **6000.5.7f1**, build settings và browser mục tiêu của project. [Unity Web technical limitations](https://docs.unity3d.com/6000.0/Documentation/Manual/webgl-technical-overview.html)

Chuẩn triển khai đề xuất:

- Deadline/timeout client đi qua platform clock/scheduler được cập nhật bởi player loop hoặc browser adapter đã test. Cancellation khi rời màn hình/session vẫn phải tường minh; không giả định `CancelAfter` sẽ hoạt động đúng vì Editor PASS.
- `async` không đồng nghĩa chạy ở background thread. Không `.Wait()`/`.Result` trong frame/update hoặc chain UI/network; không `async void` ngoài entry point event bắt buộc, và entry point phải quan sát exception.
- API Unity được gọi ở context Unity hợp lệ. Phần server được dùng concurrency khi cần, nhưng không kéo threading assumptions đó vào shared simulation hoặc Web client.
- Serialization/DI/registry ưu tiên explicit code hoặc generation tại build được chứng minh AOT-compatible. Reflection không bị cấm toàn bộ; mọi use case reflection phải có bằng chứng build stripped/AOT vẫn giữ đủ type/method và không cần runtime code generation.
- Giữ serialize/deserialize golden fixtures và test thật bản Release Web với stripping như phát hành. Không chữa thiếu type bằng tắt stripping mọi assembly mà không đánh giá download/memory.
- Không đặt serialization, shader/material creation, reflection lookup, scene-wide object search hoặc allocation lớn trong hot path tick/frame. Tối ưu từ profiler; không biến mọi code thành cấu trúc khó đọc chỉ để tránh allocation chưa đo được.
- Browser transport/file persistence/audio là adapter đã thử; không mặc định API .NET native dùng được trên Web. LAN host native có runtime/dependencies tự chứa; browser LAN không cần tải dependencies từ Internet.

## 7. Quy ước giúp source dễ đọc và dọn dẹp

- Naming bằng tiếng Anh nhất quán theo domain; tên nêu ý nghĩa/đơn vị như `SpeedMetersPerSecond`, `AttackCooldownTicks`, không `value1`, `magicSpeed`. Constants dùng tên giải thích luật; balance nằm trong validated content khi phù hợp.
- Class/method có một vai trò; tách khi có lý do thay đổi hoặc ownership khác, không theo ngưỡng số dòng máy móc. Public API nhỏ, implementation `internal`/private theo nhu cầu; mutable collections không lộ ra ngoài owner.
- Comment giải thích lý do, invariant, unit và tradeoff khó thấy từ code. Không ghi lại từng dòng lệnh. Public contract và schema có mô tả input/output/failure/lifetime.
- Formatting/analyzers được pin và chạy chung; nullable analysis áp dụng nơi compiler/project hỗ trợ đã xác minh. Cảnh báo không được tắt cả project để che lỗi cụ thể; suppression phải hẹp và có lý do.
- Lỗi expected như lobby full/content mismatch/insufficient funds dùng typed result/error code; unexpected failure có exception/log context. Không catch rồi bỏ qua, trả success giả hoặc ghi token/password/key vào log.
- Subscription, cancellation, pooled object, native buffer, network connection và downloaded asset handle có owner/lifetime rõ; dispose/unsubscribe khi rời screen/session/match. Test lại nhiều vòng create/join/leave, không chỉ lần boot đầu.
- Một feature thay đổi phải tìm được qua folder/module theo domain. Bỏ dead code/flag đã hết thời hạn khi đủ bằng chứng; không giữ hai implementation song song vô hạn “để sau”. Migration/deprecation có phiên bản và điều kiện xóa.
- Dependency/package được pin sau preflight, lưu lý do chọn và license/provenance phù hợp; không nâng đồng loạt unrelated libraries trong một gameplay change.
- Quyết định lớn có ADR ngắn: bối cảnh, lựa chọn, tradeoff, bằng chứng và khi nào xem lại. Không viết tài liệu hình thức cho từng helper.

## 8. Ví dụ mở rộng không sửa mọi hệ thống

| Thay đổi | Vị trí cần thay đổi có chủ đích | Phần phải giữ nguyên nếu contract không đổi |
|---|---|---|
| Thêm vũ khí dùng cùng cơ chế cận chiến | Weapon definition + validation, newly authored model/animation/VFX/audio, registry/content manifest và tests range/damage/cooldown | Transport, account, lobby, race phase và wallet không biết tên từng vũ khí. HUD đọc metadata/action state. |
| Thêm loại vũ khí có hành vi mới | Strategy/attack resolver mới + đăng ký rõ, state/event contract và version nếu cần, tests server/prediction | Không chèn `switch (weaponName)` trong AI/UI/network/economy; không hứa mọi tính năng mới đều chỉ cần config. |
| Thêm route/biome | Authoring track data, new asset packs, checkpoints/collision/spawn validation, race config và streaming/performance capture | Controller, combat và lobby logic không chứa tên route cố định; server/client dùng cùng exported route hash. |
| Thêm game mode | Mode rules/score/finish policy, lobby options/read model, result contract có version nếu thay meaning | Reuse movement/combat/transport khi luật không đổi; thưởng đi qua server application với validation riêng, không UI cộng tiền. |
| Đổi WSS sang transport đã được chọn sau benchmark | Adapter + host endpoint/config + impairment tests | Simulation và gameplay policies không phụ thuộc SDK transport hoặc connection object. |
| Chạy LAN mất Internet | Host composition chọn local identity/storage/content, bundle toàn dependencies | Cùng simulation/protocol và luật trận; online wallet không được thay bằng local save qua một flag trong UI. |

Tiêu chí mở rộng tốt là diff có phạm vi dễ giải thích và các invariant cũ vẫn đúng. Không đo bằng số design pattern, số abstraction hoặc yêu cầu “không sửa dòng nào”; khi rule/contract thay đổi thật thì sửa tường minh và version hóa là đúng.

## 9. Kiểm thử kiến trúc và hành vi có ý nghĩa

| Lớp kiểm tra | Bằng chứng / lỗi cần bắt |
|---|---|
| Dependency boundaries | Build/assembly reference checks chặn Simulation→Unity/DB, Client→server infra, runtime→Editor; phát hiện dependency cycle và đưa research assets vào player pack. |
| Pure simulation | Input/tick fixtures kiểm acceleration, side/range attack, cooldown, crash/run/remount, simultaneous hit/finish, qualify/tie/DNF. Tests xuất phát từ đặc tả/evidence, không chép lại công thức implementation. |
| Cross-build replay | Chạy cùng fixture/content trên .NET và actual Web build; ghi sai lệch và tolerance; mismatch không được che bằng chỉ so final rank. |
| Protocol contract | Golden payload, truncated/oversized/unknown-version, duplicate/reordered/stale command, enum/range invalid và entity không thuộc session. |
| Persistence | Concurrent buy không overspend; kết quả trận retry không double reward; rollback/restart giữa commit/apply; migration từ save/DB fixture cũ. |
| Presentation lifecycle | Prediction confirm không phát effect hai lần; reconnect không tạo duplicate view; join/leave nhiều vòng không giữ subscription/pool state/asset handles cũ. |
| Web release | AOT/stripping, cold load, input/audio focus, browser timeout, reconnect/tab suspend; Editor unit PASS không thay thế. |
| Offline LAN | Host lần đầu và client cold cache chạy khi WAN tắt; không outbound dependency bắt buộc; restart giữ local profile và không mở đường nhập reward online. |
| Performance | Capture frame/tick/memory/load/network trước và sau thay đổi có nguy cơ; budget từ TECHNICAL_ARCHITECTURE, ghi hardware/browser/build/content hash. |

Test pyramid theo rủi ro: nhiều test nhanh cho invariant domain/simulation; integration cho storage/transport/build; ít scenario end-to-end nhưng chạy đúng browser/máy. Không viết test chỉ kiểm getter/setter, tên class hoặc cấu trúc nội bộ không phải contract. Lint/build thích hợp là đủ cho thay đổi documentation/reversible nhỏ; bổ sung test khi có behavior/invariant cần bảo vệ.

## 10. Gate review cho mỗi thay đổi source

- [ ] Module/state owner và chiều dependency rõ; không thêm singleton/service locator hoặc global event shortcut.
- [ ] Luật gameplay/economy có authority đúng; prediction/presentation không trở thành nguồn kết quả chuẩn.
- [ ] Nếu đổi contract/content/save: compatibility, migration/version và fixture đã được cập nhật.
- [ ] Lifetime/cancellation/unsubscribe/pool reset và failure path được xử lý; không để exception/task mồ côi.
- [ ] Tests/checks theo rủi ro PASS; nếu đụng Web/AOT/network, có bằng chứng browser cần thiết.
- [ ] Nếu đụng hot path/assets: có số đo phù hợp hoặc lý do không ảnh hưởng; không gắn nhãn performance PASS từ suy đoán.
- [ ] Tên/log/comment rõ, code thừa được dọn, docs/ADR chỉ cập nhật phần quyết định thay đổi.
- [ ] Không chứa asset extract, secret hoặc dependency ngoài Internet bắt buộc trong gói LAN offline.

P02 cần xác nhận cấu trúc shared-source/assemblies, build targets, composition roots và một luồng browser→server→snapshot chạy thật. P03–P07 bổ sung patterns khi các feature xuất hiện. Trước P08, thử ít nhất một mở rộng weapon/route qua pipeline này để chứng minh kiến trúc dễ mở rộng bằng một thay đổi thực, không chỉ bằng sơ đồ.
