# Racing Bois — phân tích video tham chiếu Road Rash PC

Ngày kiểm tra: 2026-09-21. Đây là evidence gameplay để lập kế hoạch, **không phải bản đặc tả toàn bộ mã nguồn Road Rash** và không thay thế audit thư mục `racing_bois_mod`.

Cập nhật yêu cầu sản xuất: **assets của Racing Bois phải được làm mới từ đầu**, dùng bản gốc để tham khảo và kiểm kê mức độ phong phú; không sao chép 100% assets gốc. Ảnh trích trong hồ sơ này chỉ là evidence nghiên cứu, không phải tài sản đưa vào build phát hành.

## 1. Nguồn và phạm vi thực sự đã xem

| Thuộc tính | Giá trị kiểm tra trực tiếp |
|---|---|
| Nguồn | `C:\Users\Liquid\Downloads\prompt\Road Rash PC (1995) - Big Game Mode (All Levels).mp4` |
| Thời lượng | 9.279,715556 giây = 02:34:39,716 |
| Video | AV1; 640 × 480; 4:3; 30 fps của bản ghi; 278.388 frame video |
| Audio | HE-AAC, stereo, 44.100 Hz; **chưa nghe/đánh giá audio** |
| Kích thước | 974.063.206 byte |
| SHA-256 | `a270cca1f0a9866b43ca629fe0df1facd0a64bbb3ccb25f557c812ec8407554a` |
| Nhãn năm | Tên file ghi 1995; màn hình đầu video có copyright ©1996. Không dùng tên file để suy ra chính xác bản executable. |

Đã trích và nhìn **312 ảnh, tương ứng 301 timestamp khác nhau**, trong **27 contact sheet**:

- `timeline/`: 162 ảnh; mỗi 60 giây từ đầu đến cuối, thêm intro/outro. 14 contact sheet; bao phủ toàn trục thời gian, nhưng có khoảng trống giữa mẫu.
- `focused/`: 108 ảnh; menu 00:00–00:40, jump/crash 01:58–02:07, kết quả/start 04:10–04:40, progression/shop 19:40–20:25, crash/recovery 30:57–31:15, combat 34:55–35:10, finale 02:34:08–02:34:38. 9 sheet.
- `shops/`: 42 ảnh; shop/purchase 20:30–20:57, 52:45–53:40, 59:25–01:00:05, 02:03:20–02:04:10. 4 sheet.

Mỗi nhóm có `metadata.json`, `frames.json`, `watch_report.md`, `invocation.json`, `watch_stderr.txt`, thư mục `frames/` và `contact_XX.jpg`. Tổng hợp tại [coverage.json](coverage.json). Ảnh gốc đã trích là 640×480; contact sheet thu nhỏ mỗi ảnh về 320×240 để khảo sát liên tiếp. Mọi timestamp dưới đây là thời gian tuyệt đối của video.

Đã dùng skill `watch` sau khi đọc script/preflight; local-only, `--no-whisper`, không upload audio/video, không sửa file nguồn. Script tái lập: `tools/reverse-engineering/video/sample_reference.py`. Trích dẫn `reason=transcript-cue` trong report là nhãn mặc định của tool cho timestamp ép buộc; **không có transcript** và không lấy timestamp từ lời nói.

**Giới hạn:** đây là khảo sát bằng ảnh theo thời gian và một số chuỗi dày, chưa xem liên tục mọi frame ở tốc độ thật. Chưa đo input, physics, hitbox, damage, AI seed, latency, âm thanh hoặc FPS của game gốc. Không tuyên bố suy ra 100% logic chỉ từ video này.

## 2. Những cơ chế được thấy trực tiếp

`O` = quan sát trực tiếp; `I` = suy luận cần kiểm chứng thêm; `D` = đề xuất thiết kế cho Racing Bois.

| ID | Cơ chế / nội dung | Evidence video | Độ chắc chắn và giới hạn |
|---|---|---|---|
| V01 | Chọn Thrash Mode, Big Game Mode, Mano-A-Mano; Big Game giới thiệu năm level, chọn nhân vật, có tiền và nâng xe | 00:02–00:06, `focused/contact_01.jpg` | O: nội dung menu. Chưa thử Thrash/Mano-A-Mano; không thể suy ra network protocol từ tên chế độ. |
| V02 | Có tám tên nhân vật chọn được; portrait, tiểu sử, chiều cao/cân nặng, xe và tiền khởi đầu | 00:08–00:14 | O: Axle, Bose Jefferson, Cydney Bass, Milwaukee Jon, Pearl McKurdy, Rhonda the Rash, Slim Jim, Teflon Mike. Chỉ xem detail Axle/Jon. |
| V03 | Nhân vật có tài nguyên khởi đầu khác nhau | 00:08 Axle $200; 00:12 Jon $400; cùng hiển thị 400cc Corsair Swallow | O về số hiển thị. Chưa chứng minh chiều cao/cân nặng ảnh hưởng handling/combat. |
| V04 | Hub có club, shop, quay về; club có bulletin board, hội thoại và lựa chọn khác | 00:16–00:22; 20:42–20:51 | O về menu. Chưa audit toàn bộ hội thoại, save/load và các nhánh ẩn. |
| V05 | Năm vùng đua: The City, Sierra Nevada, The Peninsula, Napa Valley, Pacific Highway | 00:24–00:36, `focused/contact_02.jpg` | O: năm mục đường đua cùng xuất hiện. Mục Der Panzer Klub là quay về hub, không tính là track thứ sáu. |
| V06 | Điểm bắt đầu có nhiều tay đua, khán giả, đếm ngược số lớn rồi xuất phát | 04:36–04:40; 01:18:00; 02:03:55–02:04:05 | O. HUD xuất phát thường hiển thị hạng 14; đây là bằng chứng field ít nhất 14 vị trí trong các race thấy được, chưa chứng minh hard cap engine. |
| V07 | Camera đuổi sau lưng, xe gần giữa dưới màn hình, đường/horizon thay đổi theo dốc; dashboard cố định phía dưới | 00:45, 01:00, 01:58–02:07; toàn timeline | O. Chưa đo FOV, spring/damping hoặc camera smoothing. |
| V08 | Đường có cua, lên/xuống dốc, đỉnh dốc có thể làm xe bay; có chuyển động ngang đường | 01:58–02:00, 28:00–29:00, 01:16:00–01:17:00 | O về hành vi nhìn thấy. Chưa tách tốc độ/độ dốc quyết định airtime. |
| V09 | Xe và người có thể tách nhau khi crash; người bay/tumble, đứng dậy, chạy về xe rồi lên xe | 02:00–02:07; **30:59–31:09**, `focused/contact_06.jpg` | O về chuỗi state. Không chỉ teleport lại đường. Tại 30:59 có xe ngã sát đường đi; nguyên nhân va chạm chính xác cần frame/input trace dày hơn. |
| V10 | Crash làm mất thời gian và vị trí trong cuộc đua; đối thủ tiếp tục chạy | 31:00 hạng 8; 31:04 hạng 9; 31:05–31:09 hạng 10 | O về rank và sequence ~9 giây. **Không coi 9 giây là hằng số mọi crash**. Khoảng chạy về xe, thời gian tumble và traffic có thể khác. |
| V11 | Người lái có thể vươn tay đánh đối thủ bên cạnh khi cả hai vẫn chạy; overlap chiến đấu và điều khiển xe | **35:00–35:02**, `focused/contact_07.jpg`; 01:13:00 | O về pose/hành vi. Chưa xác nhận loại đòn, nút bấm, cooldown, hit result/damage từng đòn. |
| V12 | Traffic ô tô/van, phương tiện nằm đường, người đi bộ và khán giả tạo nguy cơ/không gian né tránh | 01:00, 02:04–02:07, 31:07–31:08, 48:00, 01:32:00, 02:28:00 | O về thực thể. Không suy ra spawn probability, AI lane logic, người đi bộ có collider hay điều kiện collision cụ thể từ ảnh đơn. |
| V13 | HUD có đồng hồ tốc độ, các thanh/trạng thái màu, hạng, số khoảng cách, tên người chơi và tên đối thủ gần | 01:00, 31:00–31:09, 35:00–35:10 | O về hiển thị. Ý nghĩa đầy đủ từng thanh/mũi tên/chỉ số cần đối chiếu manual/code/runtime; không tự đặt tên tất cả là HP/nitro. |
| V14 | Cuối chặng: ăn mừng, bảng top 3 với tiền thưởng và thời gian, quay về hub có tiền tăng | 04:22–04:26 | O: Jon hạng 1 nhận $1000; các hàng sau $750, $500; tiền hub $400→$1400. |
| V15 | Có điều kiện qualify toàn bộ track trong level để tiến level | **19:45** `LEVEL PROGRESSION`, sau đó 19:50 hub Level 2 | O: câu thông báo yêu cầu qualify trên mọi track. Chưa xác nhận qualify là top mấy, tie/DNF xử lý thế nào. |
| V16 | Các route ở level cao dài hơn; không chỉ thay skin | The City 5,3 mile tại 00:24; The City 8,4 mile tại 20:54; Sierra Nevada 9,8 mile và Pacific Highway 11,0 mile tại 53:05–53:10 | O về số menu. Chưa chứng minh toàn bộ geometry mới hay mở dài route cũ. |
| V17 | Shop có ba lớp Rat Bikes / Sport Bikes / Super Bikes; giá, trade-in, trang detail và buy confirmation | 19:55–20:39; 52:50–53:00; 59:35–59:50 | O. Thông số đại diện ở phần 4. |
| V18 | Mua xe dùng tổng tiền + trade của xe hiện tại; purchase thay đổi tiền và xe dùng trong race tiếp theo | 20:30–20:45; 59:40–01:00:05; 02:03:35–02:04:05 | O: $7024 − $6994 = $30; $19527 − $18999 = $528. Tỷ lệ trade-in chung chưa được suy ra. |
| V19 | Có finish toàn mùa với màn hình chiến thắng và kết thúc câu chuyện | **02:34:16–02:34:32**, hub Level 5 sau đó | O. Video quay về hub, không chứng minh có New Game+ hoặc mọi ending. |

## 3. Loop và state machine làm đầu vào thiết kế

Các mũi tên dưới đây mô tả chuỗi đã thấy, không phải tên class hay enum trích từ binary:

```text
Chọn mode → Chọn nhân vật → Hub
Hub ↔ Club / Bulletin board ↔ Chọn route
Hub ↔ Showroom ↔ Class xe ↔ Model/detail ↔ Mua/trade
Chọn route → Loading → Starting grid/countdown → Racing
Racing ↔ Steering / acceleration / airborne / melee / avoidance
Racing → Crash → Tumble/slide → Stand → Run to bike → Remount → Racing
Finish → Celebration → Results/reward → Hub
Qualify mọi route của level → Level progression → Hub level tiếp theo
Hoàn thành mùa → Champion ending → Hub
```

Những trục phải tồn tại đồng thời trong prototype:

1. **Tiến độ trên route và lái ngang:** tốc độ/độ cong/dốc, tìm line, tránh traffic, vượt đối thủ. Track phải có profile cao độ; đường phẳng không tái tạo được evidence V08/V09.
2. **Đua và đánh cận chiến đồng thời:** khoảng cách ngang/dọc, phía đánh, animation readable; không biến combat thành màn riêng hoặc pause race.
3. **Rider tách khỏi bike:** ít nhất hai entity/state trình bày riêng khi ngã; camera theo người; vị trí xe còn quan trọng cho thời gian hồi phục.
4. **Rủi ro và phần thưởng:** mất vị trí khi ngã, kết quả quyết định tiền/qualification, mua xe mở khác biệt giữa các chặng.
5. **Độ khó/content tăng theo progression:** route dài hơn, xe mạnh hơn, mùa gồm nhiều vùng và level. Công thức difficulty/AI vẫn là việc reverse tiếp.

## 4. Baseline content quan sát được — không nhầm với số asset file

| Hạng mục | Mức tối thiểu thấy được | Ý nghĩa cho plan |
|---|---|---|
| Vùng/route menu | 5 | Cần ít nhất 5 bộ nhận diện môi trường nếu muốn ngang bề rộng tham chiếu. Chưa chứng minh mỗi vùng là asset bundle hay mesh riêng. |
| Level | 5 được nêu trong menu; Level 1,2,3,5 được thấy trực tiếp | Ma trận mục tiêu đề xuất 5 vùng × 5 tier = 25 race configuration; **25 là scope suy ra để lập kế hoạch, chưa kiểm kê độc lập từng event trong video**. |
| Nhân vật chọn được | 8 mục | 8 nhân vật/profile không đồng nghĩa 8 rig khác nhau; palette/skin chia sẻ rig có thể hợp lý. |
| Class xe | 3 | Rat, Sport, Super; mỗi class có 5 tên lựa chọn hiển thị ở các shop được lấy mẫu. |
| Mục xe shop | 15 slot menu qua 3 class | Rat: Banzai/Corsair/Kamikaze/Perro/Killer Rat. Sport: Diablo/DMG/Kamikaze/Perro/Stiletto. Super: Banzai/Corsair/Diablo/Kamikaze/Stiletto. Không khẳng định 15 unique mesh hoặc toàn bộ hidden unlock. |
| Quy mô field | Ít nhất 14 vị trí trong race sampled | Dùng 14 tổng rider làm target content/stress tham chiếu; số người thật trong online room là quyết định thiết kế/benchmark riêng. |
| Môi trường | Thành phố dốc, phố thương mại/suburban, đồi nông nghiệp/vườn nho, núi/rừng, bờ biển/vách đá/hầm | Phải lập danh mục landmark/road kit/foliage/traffic/props, không chỉ đổi màu skybox. |
| Frontend/meta | Mode, profile/portrait, hub, club, track board, shop class, shop detail, loading, result, level-up, season ending | Cần asset UI/illustration/audio tương ứng, bên cạnh world mesh. |
| Rider animation | Lái thẳng/cua, tư thế bay, vươn tay đánh, crash/tumble/slide, đứng/chạy, remount, ăn mừng | Danh sách action nhìn thấy; chưa có số clip/frame, rig/bone hoặc blend graph. |

Một số xe thấy trang/tên rõ:

- 400cc Corsair Swallow, starter của Axle/Jon; $3249 trong shop (20:10).
- 250cc Kamikaze ZYX 250, giá $3497 (20:00).
- 125cc Perro Pico, giá $2999 (20:05).
- 600cc Stiletto Aggressore, $6994, 75 HP / 410 lbs; `HANDLING: Predictable`, `ACCELERATION: Strong`, `TOP SPEED: Competitive` (20:30–20:36). Đây là chuỗi UI, chưa phải giá trị physics đã tìm ra.
- 1000cc DMG M10, $16875 (20:25/52:45).
- 750cc Kamikaze ZYX 750, $11988 (20:20).
- 750cc Kamikaze ZYX 750N, $21789 (53:00).
- 1000cc Diablo Vipera N, $40000 (52:55).
- 600cc Corsair Raven N, $18999 (59:40).
- 900cc Stiletto Assassino N, $34888 (02:03:35).

Đây là dữ liệu tham chiếu khi khảo sát. Theo yêu cầu cập nhật, toàn bộ assets sản xuất của Racing Bois phải được làm mới từ đầu: model, texture, material, rig/animation, UI/portrait, âm thanh/nhạc và cinematic tương ứng. Tên xe/nhân vật/nhãn được ghi ở trên chỉ dùng nhận diện evidence; nội dung Racing Bois có thiết kế và nguồn tạo mới riêng. Giữ loop gameplay và độ phong phú tương đương không có nghĩa tái dùng hoặc sao chép 100% hình ảnh/âm thanh gốc.

**Đo “khối lượng assets ít nhất bằng game gốc”:** video chỉ cung cấp lower bound của nội dung nhìn thấy. Cần lấy số lượng/hạng mục/bytes/unique content từ manifest audit `racing_bois_mod`, rồi so cả bề rộng chơi được và độ đa dạng asset. Không dùng dung lượng video, dung lượng build nén, file duplicate hay tăng texture resolution để tự chứng nhận bằng asset count gốc.

## 5. Thị giác và motion cần giữ khi chuyển sang Unity 3D web

Quan sát:

- Chủ thể chính chiếm vùng giữa thấp, cho nhiều khoảng nhìn trước. Dải HUD khá lớn ở đáy nhưng không che hướng cua. Xe/nhân vật khác dễ phân biệt bằng màu áo và silhouette.
- Góc dốc, khúc cua và landmark chuyển cảnh tạo nhịp cảm giác tốc độ; đường nhiều lane trong phố, hẹp hơn ở đồng quê/bờ biển. Traffic và đạo cụ có scale tương đối dễ đọc.
- Có horizon núi xa, sky sáng xanh/mây trắng, đá/vách núi, cỏ/cây, nước biển xanh, mặt tiền nhà nhiều màu, cầu/guardrail/hầm. Đây là sự đa dạng scene nhìn thấy, không phải bằng chứng kỹ thuật shader gốc.
- Visual nguyên bản là pixelated/sprite-like trong nhiều vật thể và nhân vật. Không thể dùng frame output để khẳng định tất cả tài sản là 3D mesh hay cấu trúc render bên trong.
- Crash được nhấn mạnh bởi tách người/xe, quãng bay/trượt và chạy về; motion readability quan trọng hơn chỉ particle lớn.

Đề xuất D cho Racing Bois, không gán là cơ chế gốc:

1. Giữ composition/camera đọc đường, tăng chất lượng bằng URP material/light hợp web, model silhouette rõ, texture atlas, shadow/contact phù hợp từng tier. Chốt pipeline sau benchmark prototype.
2. Road spline có curvature + banking/cao độ + shoulder; roadside kit thay đổi theo biome. Chia đoạn và stream/cull để world phong phú mà không tải tất cả cùng lúc.
3. Hit VFX, sparks, skid/dust, landing puff, camera impulse mức vừa phải; ưu tiên thấy hazard/opponent. Mọi VFX có quality tier và pooling; tránh blur quá mức làm khó đọc cua.
4. Animation/pose người và bike tách tầng để lái và đánh đồng thời; recovery có vị trí world thực. Animation root motion không được tự quyết định world position trong authoritative multiplayer.
5. Audio cần một pass riêng: engine theo RPM, gear, wind, tyre, hit/crash, crowd, ambience từng biome, UI và soundtrack. **Chưa có nhận xét chất lượng/định lượng âm thanh từ pass này.**

Không được dùng video 30 fps để chứng minh Unity web đạt 30/60 fps. Benchmark phải chạy actual Web build trên hardware/browser mục tiêu, cùng field và content density, đo p50/p95 frame time, memory và asset load.

## 6. Multiplayer: phần mới cần thiết kế, video không xác nhận

Video không chứng minh lobby, matchmaking, tài khoản, persistence, remote hit validation, LAN discovery hay số player mạng. Đây là yêu cầu mới của Racing Bois.

Các state trực tiếp ảnh hưởng online cần server có thẩm quyền: race phase/countdown; input/tick; bike/rider transform và velocity; airborne/crash/recovery; health/stun/weapon nếu chốt gameplay; hit/collision; route checkpoint/finish/order; reward/qualification; currency/purchase/inventory. Tên target/rank/HUD là projection từ state, không phải nguồn thật.

Các thử nghiệm phải có trong phase mạng:

- Hai người áp sát rồi đánh cùng lúc, chạm lane và traffic, một người airborne; thứ tự hit/result phải nhất quán giữa server và cả hai browser.
- Crash cùng thời điểm finish; player đang chạy về xe bị mất kết nối; reconnect không tạo xe thứ hai hoặc reset thiệt hại/trả thưởng hai lần.
- Người join lobby rồi rời/đổi xe/ready nhiều lần; host browser đóng không khiến authoritative match biến mất nếu server quản lý room.
- Replay một request mua/nhận thưởng hoặc gửi state tốc độ/tiền giả: server dùng input/transaction hợp lệ và kết quả trận được xác thực.
- Test LAN và internet là hai đường kết nối triển khai; cùng protocol/game rules. Đo riêng RTT, jitter, loss và reconnect. Không coi kết nối thành công là đã giải quyết chất lượng real-time toàn cầu.

Các điểm trên là tiêu chí plan đề xuất, chưa chứng nhận backend hay OCI nào đã triển khai.

## 7. Các khoảng trống phải đóng để dùng chữ “giống y chang” có căn cứ

| Khoảng trống | Evidence cần bổ sung / phép thử |
|---|---|
| Throttle/brake/steering/lean/traction | Input log + speed/position trace, thay một input mỗi lần; ghi exact executable/build. |
| Airborne/landing/crash trigger | Đo cùng đoạn dốc ở nhiều tốc độ; collision mesh/response hoặc runtime instrumentation. |
| Punch/kick/weapon/block/steal | Mỗi action cần input, pose, range/cooldown, hit/hurt, damage, knock-off condition. Video pass này chỉ xác nhận vươn tay đánh. |
| Health/bike damage/stun/repair | Xác định từng thanh HUD và điều kiện threshold; không suy ra từ màu. |
| Nitro/gear/model stats | Nút/action, số lần, duration, recharge, torque/speed handling; hậu tố N và đèn HUD chưa đủ chứng minh công thức. |
| Police/arrest/fines | Phân loại actor từ executable/asset rồi kiểm chứng trigger, chase/bust/result. Skin xe đen/trắng trong video chưa đủ để tuyên bố toàn bộ luật cảnh sát. |
| AI/overtake/combat/personality | Tình huống lặp và trace; loại bỏ ảnh hưởng seed/traffic/level; tên rival không tự chứng minh personality. |
| Qualify, tie, DNF, retries, season | Boundary test từng rank và finish condition; tất cả UI branches. |
| Save/load và economy | Quy tắc persist, trade, sửa xe, thưởng/trừ phạt; chống double transaction trong thiết kế online. |
| Track population/content exhaustiveness | Đối chiếu manifest binary và map/event table; audit tất cả route/tier và hidden content. |
| Audio/feel và animation timing | Nghe video tại tốc độ thật; sample sequence cao hơn/trace; input-to-display test. |
| Multiplayer gốc | Không nằm trong pass Big Game này; không suy ra từ menu Mano-A-Mano. |

Với mỗi cơ chế, bảng parity nên có `reference evidence → extracted logic/data → Racing Bois implementation → test/replay evidence → status`. Trạng thái hợp lệ: observed, inferred, extracted, implemented, verified, unknown; không cộng % parity chung từ số đầu mục đã viết.

## 8. Đề xuất phase dựa trên evidence

Đây là đầu vào để ghép với kế hoạch chính và kết quả reverse binary, chưa bắt đầu code game:

1. **Reference closure và baseline:** hợp nhất manifest mod + evidence video; chốt danh mục 5 vùng, progression, rider/bike classes; ghi unknown cụ thể và test để đóng.
2. **Handling/combat greybox:** một đoạn đường đủ cua/dốc/jump, traffic, 14 rider tổng để test; lái/đánh/ngã/chạy về xe. Gate là capture/replay chứng minh V06–V12, không phải chỉ scene đẹp.
3. **Web/network technical slice:** build web thật + authoritative two-player; kiểm chứng prediction/correction và hit/crash ở latency mục tiêu trước nhân rộng content/art.
4. **Vertical slice có chất lượng đích:** một race hoàn chỉnh cùng hub → shop → race → result → economy; asset production-ready/camera/VFX/audio; đo performance thật.
5. **Mở rộng content/progression:** hoàn thiện nhiều vùng/tier/bike/character; manifest đếm unique asset và playable coverage; tránh asset clone để tăng count.
6. **Online/LAN và persistence vận hành:** lobby/accounts/transaction/reconnect/region behavior; deploy OCI chỉ sau kiến trúc và preflight hạ tầng; test failure/load/backup restore.
7. **Polish và nghiệm thu:** video so sánh các tình huống cụ thể; kiểm tra art/rig/UV/collider/prefab; browser matrix/network soak; release gate dựa evidence, không tuyên bố “100%” khi còn unknown.

## 9. Tái lập các ảnh bằng chứng

Từ project root, PowerShell (đường dẫn output có thể đổi sang folder mới để giữ evidence cũ):

```powershell
python 'tools\reverse-engineering\video\sample_reference.py' `
  'C:\Users\Liquid\Downloads\prompt\Road Rash PC (1995) - Big Game Mode (All Levels).mp4' `
  --watch 'C:\Users\Liquid\.agents\skills\watch\scripts\watch.py' `
  --out 'docs\reverse-engineering\video\timeline'
```

`--timestamps` nhận danh sách giây nguyên, ví dụ `'1859,1860,1861,1862,1863,1864,1865,1866,1867,1868,1869'` cho crash/recovery. Các lệnh chính xác của ba lượt hiện tại đã được giữ trong từng `invocation.json`.

Không ghi đè hoặc xóa video tham chiếu; công cụ chỉ đọc nó. `watch` sẽ thay các ảnh cue trong **folder output được chỉ định** khi chạy lại, vì vậy dùng folder mới nếu cần giữ các lượt audit riêng.
