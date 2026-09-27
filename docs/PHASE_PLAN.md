# Racing Bois — Kế hoạch thực hiện từng phase

**Ưu tiên mới 2026-09-26:** client chính là Windows 10/11 desktop; Web làm sau, backend online vẫn triển khai trên OCI. P08 nghiệm thu bằng bản Unity Windows chạy thật, content native đã cài và multiplayer native. Chi tiết: [P08 platform](p08/PLATFORM_PRIORITY.md).


Ngày cập nhật: 2026-09-26. Yêu cầu đã chốt: [REQUIREMENTS.md](REQUIREMENTS.md). Thiết kế đề xuất: [TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md). Bằng chứng reverse: [REVERSE_ENGINEERING_REPORT.md](REVERSE_ENGINEERING_REPORT.md).

**Trạng thái cập nhật:** P00 đã có hồ sơ; P01 reverse sâu/native traces nhưng full-logic gate còn mở; P02 có nền tảng đã kiểm chứng theo [P01_P02_STATUS.md](P01_P02_STATUS.md). P03/P04 có gameplay Web và assets mới, gồm gậy dựng theo concept. P05 đã triển khai multiplayer tại [P05_STATUS.md](P05_STATUS.md); còn nghiệm thu nhiều máy LAN/WAN, hình ảnh va chạm đối thủ và budget mạng. P06 đã triển khai slice `0.6.0` với assets/rig/clip/audio/VFX/UI, scene benchmark và gói chạy: [P06_STATUS.md](P06_STATUS.md). Review hình ảnh/cảm giác bởi người chơi, usability người mới, gamepad thật và benchmark browser dài hạn còn riêng. P07 source `0.7.0` đã triển khai account/SQLite/garage/shop/campaign/realm và có các suite native/application PASS: [P07_STATUS.md](P07_STATUS.md). Build Web cuối, nghiệm thu browser và gói P07 đã có receipt bàn giao local; 15 SKU/5×5 ô campaign không đồng nghĩa đủ 15 model hay 25 track. Kế hoạch bên dưới vẫn là tiêu chí cho từng phase, không tự đánh dấu mọi gate PASS từ một demo.

## Lộ trình tổng quan

| Phase | Kết quả phải giao | Điều kiện qua phase |
|---|---|---|
| P00 — Reverse tĩnh & tham chiếu | Inventory/hash, parsers, giải nén container, logic có địa chỉ, phân tích video, gap register | Chạy lại được, số liệu khớp nguồn, không tuyên bố quá bằng chứng |
| P01 — Khép các gap reverse | Đặc tả hành vi, cấu trúc track/sprite hoàn chỉnh, fixtures đo từ bản gốc | Có bằng chứng và test cho từng hệ thống; mọi gap còn lại phải được xử lý hoặc ghi quyết định rõ |
| P02 — Nền tảng & thử rủi ro sớm | Unity Web build, Blender MCP→prefab, simulation/server skeleton, transport spike | Browser thật ↔ server chạy; asset round-trip PASS; phương án mạng/VM architecture khả thi |
| P03 — Cảm giác lái | Một track graybox, xe, camera, traffic cơ bản, HUD đo | Đạt bộ bài thử lái, sense of speed, frame-time baseline |
| P04 — Combat, té xe, AI | Đánh/nhặt-cướp vũ khí nếu xác minh, damage, cảnh sát, ngã/chạy/lên xe, race states | Đúng đặc tả, test biên, AI không gian lận ngoài rule đã xác định |
| P05 — Online + LAN offline | Trận có authority, lobby tối thiểu, prediction/reconciliation, reconnect, LAN host | Nhiều máy qua Internet và LAN cắt WAN thực sự chơi được; attack input không phá state |
| P06 — Vertical slice hoàn thiện | Một đường đua đẹp và hoàn chỉnh, audio/VFX/UI, 8–16 người theo benchmark | Gameplay, đồ họa, assets checklist và web performance cùng PASS |
| P07 — Backend tiến trình | Account/profile, garage/shop, currency/inventory, campaign/rewards, lobby đầy đủ | Transaction/idempotency/recovery đúng; tách realm offline/online |
| P08 — Toàn bộ nội dung | Bộ đường đua, xe, nhân vật, props, animation, audio/UI/cinematic đủ baseline | Content mapping phủ toàn bộ, khối lượng tối thiểu đạt và không đếm trùng |
| P09 — OCI staging & kết nối toàn cầu | Deploy/backup/restore/rollback/observability, region tests, capacity report | Client Windows truy cập HTTPS/WSS public; DB private; tải và latency có số đo từ nhiều khu vực |
| P10 — Tối ưu & phát hành | Release candidate Windows 10/11, hardware/input matrix, soak, regression/parity, LAN package, tài liệu vận hành | Tất cả gate desktop bắt buộc PASS; không còn blocker gameplay/data/performance; Web nghiệm thu sau |

Mỗi phase có review artifact riêng và danh sách việc tiếp theo. P02 sẽ thử networking để phát hiện rủi ro trước khi đầu tư art; P05 hoàn thiện mạng gameplay. Mỗi phase cập nhật asset/content ledger và performance baseline.

**Cập nhật đã chốt:** bản gốc chỉ là tham chiếu. Mọi asset trong sản phẩm được làm lại từ đầu; dữ liệu giải mã trong P00/P01 chỉ ở thư mục nghiên cứu. Pipeline production kiểm tra cả provenance/source mới và việc không đưa file gốc vào build.

**Yêu cầu bổ sung xuyên suốt:** UI/UX theo [UI_UX_DIRECTION.md](UI_UX_DIRECTION.md); code theo [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md). Mỗi phase có review dependency/API, readability và extension points cần thiết. Không dồn maintainability/UI polish thành công việc cuối P10.

## P00 — Hồ sơ forensic và reverse ban đầu (đợt hiện tại)

Đầu vào: bản mod và video local, project Unity hiện có. Làm read-only với nguồn.

Đầu ra:

- Manifest từng file có SHA-256, phân loại magic, kích thước, duplicates và tổng.
- Parsers container CRSR/FAM, sprite DAT, media metadata; offset/size/decompression validation và research samples.
- PE imports/sections, disassembly/xrefs, save fields/checksum, bảng xe và các routine gameplay có bằng chứng.
- Timestamp gameplay reference, trạng thái được quan sát và giới hạn sampling.
- Requirements, kiến trúc, phase plan, môi trường MCP và danh sách gap.

Nghiệm thu: tổng parser đối chiếu manifest; checksum/decompression kiểm tra; chỉ rõ coverage static, chưa chạy dynamic. Nguồn không bị chỉnh sửa. Không đưa asset nghiên cứu thẳng vào bản phát hành.

## P01 — Khép khoảng trống và dựng đặc tả parity

Phụ thuộc P00. Đây là bước tiếp theo được đề xuất.

1. Lập bảng toàn bộ gameplay state: menu → character/bike → course → race → result → reward → qualify/level-up; cả crash, wreck, bust, pause, quit, reconnect nếu có.
2. Reverse đầy đủ track records: road curvature/height/width, scenery placement, lanes, spawn/finish, traffic, collision zones. Map offset→trường→unit, không đặt tên chỉ bằng phỏng đoán.
3. Hoàn tất giải mã sprites: CLGP/RRAN/CANS/FORM, pixel codec, palette index, transparency, frame duration, attachment/anchor; phân loại empty/variants. WAV/MIDI/SoundFont/video cũng cần kiểm tra khả năng đọc/chuyển đổi, không chỉ đọc header.
4. Dùng disassembler/decompiler có project lưu được để nối call graph của update loop, movement, combat, AI, race outcomes. Đặt alias cho hàm và biến chỉ khi bằng chứng đủ.
5. Chạy **bản sao** game trong môi trường Windows tương thích, kiểm soát registry/process. Launcher/batch gốc có side effects đã phát hiện; không dùng wrapper đó trực tiếp trong môi trường đang làm việc. Capture input + video + trạng thái/save before/after để xác nhận logic động.
6. Đo tăng tốc/phanh/tốc độ tối đa/steer/lean/va chạm, road slope/airborne, damage từng weapon, cooldown, steal, AI aggro, police/wreck, race prize/qualification. Tách random seed và đơn vị thời gian khỏi giả định frame rate.
7. Tạo `ParityMatrix` với source address hoặc timestamp, state input/output, tolerance, test ID và trạng thái; fixtures không lẫn save đã chỉnh sửa/invalid checksum.
8. Ghi difference ledger giữa bản mod và video PC: điều nào cùng bằng chứng, điều nào khác/chưa rõ. Chưa có binary vanilla để diff thì không tự tuyên bố mod và bản PC giống hoàn toàn.

Gate: mỗi hệ thống thuộc yêu cầu có đặc tả đo được; các số chưa khôi phục không được gắn nhãn “đúng bản gốc”. Gate “100% logic” chỉ đóng khi không còn gap trong scope đã chốt; nếu chưa đạt thì tiếp tục P01. Asset reference ledger dùng để lên thiết kế mới, không làm danh sách file gốc để tái sử dụng.

## P02 — Foundation, Unity MCP, Blender MCP và networking spike

Phụ thuộc baseline P01 đủ để chọn simulation. Chưa sản xuất hàng trăm assets.

- Thiết lập version control/ignore cho Unity, pin Editor/package commit; branch/release conventions của chính Racing Bois. Không áp workflow repo Jarvis sang đây.
- Chốt URP + Input System + web build settings, xử lý cảnh báo Input Manager/Dynamic Batching hiện tại, lưu boot scene và test scene.
- Kết nối Blender MCP đúng instance trên máy. Preflight hiện thấy Blender executable nhưng không có callable Blender MCP; phải hoàn thành connection test trước khi ghi production pipeline PASS.
- Tạo một asset nhỏ bằng Blender MCP; kiểm scale/pivot/UV/maps/LOD/collider/rig nếu có, export/import qua Unity MCP, dựng prefab, scene test, screenshot và Web build. Đây là phép thử cả chuỗi công cụ.
- Lõi `RacingBois.Simulation`, schema content, protocol version; headless server skeleton chạy simulation không phụ thuộc render.
- Chốt assembly/dependency boundaries, composition root và pattern phù hợp; UI navigation/input/focus spike và component/token conventions. Có architecture decision records ngắn cho quyết định quan trọng.
- Spike browser WebGL ↔ WSS authority với 2–8 synthetic riders; thử 150/250 ms RTT và packet loss/jitter. Nếu head-of-line không đạt, thử WebRTC/server route trước khi chốt.
- Preflight OCI read-only xác định VM architecture/capacity/region khi có target rõ. Thử binary/server image phù hợp; không mặc định Unity dedicated server hỗ trợ VM đã có.

Gate: fresh checkout build được; browser gửi input/nhận correction được; Blender→Unity artifact đạt checklist; chưa có missing reference/compile error; quyết định transport có số đo và ghi tradeoff.

## P03 — Driving graybox và camera

- Track ribbon/spline có thẳng, cua hẹp/rộng, lên/xuống dốc, vai đường, traffic lane.
- Throttle/brake/steer, acceleration curve, traction/off-road, lean, jump/landing và collision proxies theo P01.
- Camera chase, FOV/speed cue, horizon handling, HUD speed/rank/distance/health.
- Replay input fixture; debug overlays chỉ ở development build.
- Lấy browser profiler baseline trước art: CPU/GPU/frame time/allocations và resident memory.

Gate: các bài thử lane change/corner/braking/hill/collision không xuyên xe, không teleport hoặc mất camera; đường cong vận tốc và thời gian hoàn thành phù hợp tolerance đã chốt. Chưa cần đạt fidelity art ở phase này.

## P04 — Combat, recovery, AI và race rules

- State rider/bike rõ ràng: riding, attack, hit, airborne, falling, detached, running, remounting, wrecked/busted/finished.
- Hitbox trái/phải, weapon reach, damage/strength, cooldown, steal/disarm nếu được xác minh; deterministic event IDs cho networking sau.
- Té xe tách rider và bike; quãng chạy về xe/leo lên ảnh hưởng thời gian đua giống reference.
- Traffic, pedestrians nếu thuộc baseline, đối thủ chọn lane/tránh/đánh, police chase/bust; spawn/despawn có budget.
- Campaign/race qualification và rewards tạm chạy local data để kiểm gameplay; economy online chính thức ở P07.

Gate: đánh sai phía/quá xa/đang té không trúng; simultaneous hits/death/finish có thứ tự rõ; AI và race rules có replay regression; hồi phục sau crash không kẹt. Nghiệm thu combat bằng video side-by-side và các số đo, không chỉ bằng cảm nhận.

## P05 — Multiplayer có authority và LAN không Internet

- Server loop, snapshot quantization, interest management, input ack, prediction, reconciliation, remote interpolation.
- Lobby/create/join/code/ready/countdown/leave, room cap, slot ownership và late join policy.
- Server xử lý movement, combat, damage, police/AI, thứ hạng và result; không tin client claims.
- Tick/time-window validation, message limits, replayed-command protection, rate limits.
- Disconnect/reconnect/tab suspend/host lobby leave, version mismatch, joining full room, match end cùng lúc.
- Đóng gói LAN Host tự chứa runtime/dependencies, web assets và local profiles. Sau khi có bộ cài, cả lần khởi chạy host đầu tiên phải làm được khi WAN tắt, không tải runtime/CDN/auth bổ sung. Địa chỉ/QR được tạo rõ; test TLS hoặc local HTTP/WS theo browser. Local-network access prompt được xử lý rõ trong hướng dẫn.
- Thử 8 người trước, 16 theo mục tiêu nếu server/client budget đạt. Bots và synthetic load không thay toàn bộ test nhiều client thực.

Gate: ≥2 máy khác mạng Internet chơi chung; ≥2 máy trong LAN tắt WAN, client cold cache vẫn load/join/race xong; reconnect không nhân đôi player/reward; server từ chối speed/teleport/damage fraud; network impairment matrix có báo cáo. Một VM single-region không được quảng cáo là ping thấp toàn cầu.

## P06 — Vertical slice đạt chất lượng hình ảnh cuối

Một route đại diện có cua, dốc, cảnh quan, traffic, combat và crash; tối thiểu một bike+rider hoàn thiện, đối thủ/cảnh sát, đủ props tạo mật độ gameplay.

- Blender production source, rigs/clips, LOD, UV/maps, collider và prefab cho mọi nội dung slice.
- Lighting/probes/shadows, sky/terrain/road decals, dust/sparks/skid, camera response và UI đủ chất lượng cuối.
- UI gồm tokens/shared controls, mouse/keyboard/gamepad focus, loading/error/empty/offline states, menu/lobby/HUD/results có motion/sound mới. Usability test với người chưa biết game, hỗ trợ reduced motion và UI scale.
- Engine RPM layers, impact/weapon/tire, ambient/music có mix và ducking hợp lý; browser audio unlock sau tương tác người chơi.
- Art benchmark scene và stress scene cùng camera gameplay; screenshot trong Unity và browser.
- Checklist [REQUIREMENTS.md](REQUIREMENTS.md) có kết quả tự động và visual review.

Gate: gameplay và hình ảnh được duyệt cùng nhau, không dùng screenshot tĩnh thay gameplay capture; medium 1080p mục tiêu 60 fps và frame-time/memory/loading đạt budget. Nếu không đạt thì tối ưu slice trước khi nhân rộng content.

## P07 — Tài khoản, progression, shop và persistence

**Trạng thái 2026-09-22:** runtime `3cac900` / `0.7.0` đã bàn giao local với account/recovery/revocation, SQLite migration/constraints, ledger và giao dịch idempotent, garage/shop/UI, public/private lobby và checkpoint LAN có chữ ký. Các suite persistence/client/multiplayer/regression, Web cuối, browser và gói phát hành có receipt tại [P07_STATUS.md](P07_STATUS.md). Chỉ Canyon Run đang chơi được; cấp campaign hiện tại được máy chủ kiểm tra, các tuyến chưa có content khóa đến P08. Native ARM, LAN/WAN nhiều máy và nghiệm thu production vẫn có gate riêng.

- Account/session/guest policy, profile, garage, ownership, shop/trade/repair/fines theo luật đã chốt.
- Campaign có cấu trúc đủ levels/routes, tiền thưởng, inventory và wallet ledger; giá/transaction có thẩm quyền server. Chỉ mở route đã có nội dung và cấp hiện tại; art/track còn thiếu thuộc P08.
- Lobby đầy đủ, private/public, invitations bằng code/link, matchmaking theo region/latency nếu dùng.
- Save/version migration, unique transaction IDs, idempotent result application, database constraints.
- Realm offline riêng. Export/import local save có validation; không tự sync tài sản LAN vào economy online.
- API/object access checks, session expiry/revoke, account recovery policy, audit logging không lộ bí mật.
- Chính sách game over khi mọi xe hỏng và không đủ tiền sửa: sau xác nhận mất garage/campaign, reset atomically về starter nguyên vẹn và $0; giữ account/ledger/receipts, không cấp lại tiền khởi đầu.

Gate: crash API/DB/retry không mất/nhân đôi tiền; concurrent purchases không overspend; client không sửa inventory người khác; server restart/restore giữ state hợp lệ; online/offline separation được test.

## P08 — Hoàn thành khối lượng content tối thiểu bản gốc

Mở `ContentParityLedger` từ inventory đã xác minh. Baseline sơ bộ P00 có 5 course files, 15 bike SKU và 8 bộ portrait nhân vật; các số file/frames/media nằm trong báo cáo asset. SKU/portrait không tự chứng minh số mesh/rig độc lập.

- Tất cả đường đua, biome và level/difficulty variants theo đặc tả; không coi 5×5 là 25 mesh track độc lập nếu thực tế không như vậy.
- Bộ xe/character/weapon/traffic/police/scenery/props, animation states, HUD/menu/shop/results/dialog.
- Audio/music/cinematics và toàn bộ art được làm mới từ đầu với mapping rõ ràng; không bỏ qua phần media chiếm dung lượng lớn, không đưa bản trích xuất hoặc bản re-encode gốc vào sản phẩm.
- Mỗi asset có semantic ID, original reference, thiết kế/source sản xuất mới, production replacement, QA state, dependencies và build pack. Kiểm hash để phát hiện copy trực tiếp kết hợp review source mới; hash khác không đủ chứng minh sáng tạo mới.
- Mọi nhóm nội dung phải đạt hoặc vượt baseline chức năng. Theo dõi thêm disk size/download size/triangle/clip counts; không dùng byte padding hoặc file duplicate để đạt “khối lượng”.
- Packaging theo route/biome/content hash. Client Windows và gói LAN cài toàn bộ nội dung cần offline; runtime chỉ giữ shared actors và route đang dùng. Web tải theo nhu cầu khi được triển khai sau.

Gate: không có dòng nội dung bắt buộc chưa mapping; asset count đủ theo loại đã thống nhất; độc lập rà soát inventory và playable content; mọi prefab production PASS checklist; mọi cảnh chơi được ở Windows quality tiers. Browser có gate riêng trong đợt Web sau.

## P09 — OCI staging, vận hành và global connectivity

- Chốt đúng VM/region/domain/budget/concurrent players; không thay đổi dịch vụ project khác.
- Deploy asset origin/API/match workers/DB trên OCI VM cho client Windows; volume permissions, firewall/TLS, immutable release và migration strategy. Web client được bổ sung sau.
- Backup + restore drill, failure-domain protection, RPO/RTO, disk capacity/log retention, alert thresholds.
- Kiểm Content-Encoding/MIME/CORS/cache, partial/corrupt download/version mismatch và interrupted patch.
- Load test theo match capacity thực: tick p99, CPU/RAM/egress, DB latency, lobby throughput; thiết lập giới hạn có queue/backpressure.
- Đo người chơi/agents thực ở ít nhất SEA/EU/NA. Nếu một region không đủ thì triển khai workers OCI đa region có dự toán và điều phối; data residency/authority của account giữ rõ.

Gate: public URL truy cập từ ngoài LAN, DB không public, restore/rollback thực chạy; match duration/latency/capacity có báo cáo, không suy từ spec OCPU. Thử mất worker/restart proxy/DB outage và graceful degradation.

## P10 — Release candidate, tối ưu cuối và phát hành

- Regression toàn parity matrix, campaign từ đầu đến cuối, đủ xe/nhân vật/đường đua, online/LAN, save migrations.
- Ma trận Windows 10/11 trên PC/laptop thật: fullscreen/windowed/borderless, keyboard/gamepad, remap, audio, resize, focus lost, suspend/resume và reconnect. Browser matrix Chrome/Edge/Firefox được nghiệm thu riêng khi làm bản Web.
- Profile trên máy tham chiếu và laptop cấu hình thấp hơn; cold/warm cache, shader warmup, streaming, frame-time distribution, heap/GPU memory, GC và sustained clocks.
- Soak 8–24 giờ, fuzz malformed protocol, reward race conditions, reconnect storm, backup/restore, content rollback.
- Build reproducible, version/content/protocol compatibility policy, changelog, known issues, operator/LAN host/user guide.

Gate phát hành: không còn blocker trong gameplay/netcode/save/economy; không có Console Error/Warning liên quan asset; các mục tiêu performance và content coverage đạt trên ma trận đã công bố. Nếu một mục chưa đạt, phát hành scope nhỏ hơn phải được ghi rõ thành quyết định sản phẩm, không gắn nhãn “đã đủ 100%”.

Gate code và UX: dependency graph không vòng/lẫn authority, không view thao tác economy trực tiếp; một bài thử mở rộng weapon/track/rule không buộc sửa hàng loạt class không liên quan; public behavior có test phù hợp. UI dùng được bằng controls đã công bố, focus/Back/pending/error nhất quán và hiệu ứng không làm hỏng frame pacing.

## Công việc đầu tiên của phiên tiếp theo

P08 đang triển khai theo [P08_STATUS.md](P08_STATUS.md): hoàn thiện và review roster/content, nghiệm thu Unity native rồi build Windows 10/11 với assets cài sẵn. Concept 2D luôn có trước assets 3D/UI mới; Web thực hiện sau. Các gate reverse P01, mạng thực P05 và hình ảnh/performance P06 tiếp tục được theo dõi, không tự đóng khi chuyển phase. Chưa ước lượng thời gian hoàn thành toàn game vì khối lượng art, các gap parity và OCI capacity chưa được nghiệm thu đầy đủ.
