# P04 — Combat, recovery, AI và race rules

Ngày 2026-09-21. Core mới nằm cùng shared package với P03, chạy được ở .NET và Unity. Cơ chế xác minh từ P01 được giữ riêng với quyết định tuning/world-unit mới. Bằng chứng nguồn: [LOGIC_P01](../p01/logic/LOGIC_P01.md), [NATIVE_CONTACTS_AND_AI](../p01/logic/NATIVE_CONTACTS_AND_AI.md).

## State machine

`RiderMode` gồm Riding, Attacking, Hit, Airborne, Falling, Detached, Running, Remounting, Wrecked, Busted, Finished. Attack và hit là state có movement; falling/recovery có position rider và bike riêng. Wrecked/Busted/Finished là terminal cho run hiện tại.

Crash gây Falling tối thiểu42tick và đợi rider/bike chạm ground → Detached18tick → Running tốc độ tổng theo hai trục4,5m/s → tới bike trong một bước≤75mm → Remounting60tick → Riding. Khoảng cách tới bike quyết định thời gian chạy; không nhấn một nút để teleport về xe. Bike slide nhanh hơn rider sau crash nên tạo khoảng cách rõ. Crash từ airborne giữ độ cao rồi rơi, không snap. Remount phục hồi health/endurance, giữ bike condition đã mất và bảo vệ collision/hit90tick. Bike condition=0 không thể remount. Recovery vượt1.200tick chuyển Wrecked có event rõ, không teleport hoặc kẹt vĩnh viễn.

Các duration 42/18/60, run speed 4,5 m/s, crash slide/deceleration và remount protection 90 tick là **tuning mới**. P01 chứng minh các state/running branch, velocity raw 1.200, near-bike inequality, điều kiện bike còn tốt và timeout >1.200; chưa chứng minh chuyển chúng sang timing/đơn vị mới. Bản mới không copy các ngưỡng raw ngang bất đối xứng thành mét tùy tiện.

## Combat

Input attackSide−1=trái,+1=phải; Kick chọn numeric weapon3 cho đòn hiện tại. Weapon hiện mang Fist/Club/Chain ánh xạ numeric0/1/2. Một đòn bắt đầu ở Riding, dài24tick, impact tick tuổi8, được lặp từ `max(30, hitCooldown+1)`tick sau lúc bắt đầu. Vì cooldown strict, level0 repeat31tick cho held attack gây hit ởtick9/40/71; dùng repeat30 đã được phát hiện làm miss xen kẽ và sửa trước nghiệm thu. Impact ở ngoài range là miss; đang fall/recover không được tấn công. Attack timing/hit window này là thiết kế mới, không phải đã khép toàn bộ animation gốc.

| Gate | Quy tắc |
|---|---|
| Side | Target ở đúng dấu lateral; lateral=0 không trúng |
| Longitudinal | Khoảng cách strict <1,8 m |
| Lateral | Fist/kick strict <1,6 m; club <2,2 m; chain <2,6 m |
| Height | Chênh relative road height strict <1 m |
| Cooldown | Tick phải **lớn hơn** deadline target; level0..4 =30/24/18/12/6 tick |
| Target | Target ở state còn lái được; không đánh tiếp rider đã té/terminal |

World-unit reach là tuning có ordering tương đương recovered 5/7/8 raw reach families. Chưa được gọi là phép đổi chính xác các ngưỡng raw `<0x40`, lateral `(5/7/8)<<12`, height `<0x3000`.

Damage giữ đúng phép tính Q8 đã chạy instruction/native fixtures:

```text
ratioQ8 = trunc((endurance << 8) / maxEndurance)
effective = max(trunc(strength / 2), (ratioQ8 * strength) >> 8)
damage = trunc(effective * multiplierQ8 / 256)
multiplierQ8 = [256, 320, 384, 64]
health = max(0, health - 64 * damage)
endurance = max(maxEndurance / 2, endurance - 4 * damage)
kickBikeDamage = trunc(damage / 4) + 1
```

Strength7/endurance đầy cho damage7/8/10/1, health delta448/512/640/64 và kick bike−1. Test core chạy cả pure formula và actual attack pipeline, gồm equality cooldown tick9==deadline9 không gây hit, tick9>deadline8 gây hit448. Kick lateral impulse 0,5 m thuộc tuning mới; bản này chỉ áp dụng impulse khi health hit được chấp nhận, trong khi P01 cho thấy một số impulse/animation gốc nằm ngoài health-cooldown branch. Khác biệt này được công bố, chưa gọi là parity.

Weapon steal chỉ khi attacker unarmed, target cầm club/chain và đang attack, protection đã hết strict `tick > stealUntil`, CRT PRNG `(random &3)==3`. LCG dùng đúng `state=214013*state+2531011 mod2^32`, output `(state>>16)&0x7fff`; transfer đặt protection+300 tick. Không quảng cáo là 25% mỗi hit/giây độc lập. Hai world cùng seed/input cho cùng kết quả. Steal tiêu thụ impact của đòn; hành vi nối animation và mọi branch multiplayer gốc vẫn là giới hạn.

Tick xử lý combat theo hai bước: thu các hit hợp lệ trên cùng trạng thái trước damage, rồi apply. Hai rider đánh chí mạng cùng tick vẫn gây cả hai hit. Nhiều attacker đánh cùng target thì ID thấp nhất nhận health hit trước; target cooldown chặn các health hit còn lại. Collision/crash xảy ra trước combat; combat/fatal crash xảy ra trước finish. Test hai người vừa đi qua vạch vừa đánh chết nhau cho cả hai Falling, không ghi finish/reward. Event ID tăng đơn điệu cho Attack/Hit/WeaponStolen/Crash/Landed/Remounted/Wrecked/Busted/Finished/TrafficSpawned.

## Đối thủ, traffic và cảnh sát

`RaceBrains` là AI được viết mới. Đối thủ chọn lane, bù độ cong, tránh traffic phía trước, đổi lane vượt xe chậm, phanh khẩn cấp khi chưa kịp tránh và áp sát người chơi ở cự ly gần để combat. Decision lane cách nhau 24–41 tick; steering vẫn tính mỗi tick. Attack gate dùng threshold aggression [4,8,25,64,256] đã xác minh theo level. Toàn bộ decision/navigation/pursuit không được gắn nhãn recovered AI: các relationship/natural spawn/behavior6–7 vẫn mở trong P01.

Traffic là object riêng, không dùng bike FSM. Pool cố định 12, spawn cách nhau tối thiểu 240 tick ở trước nhóm player active 180–245 m; xe thuận chiều17–26 m/s lane+3 m, ngược chiều16–23 m/s lane−3 m. Despawn sau nhóm hoặc ngoài route, tái dùng instance. Không spawn trước mặt rider trong vài mét và không cấp phát object mỗi tick. Multiplayer interest/nhiều player cách xa nhau sẽ được cải thiện ở P05; hiện tổng pool bounded, không cam kết mật độ vô hạn cho mọi player rải trên tuyến.

Một cop có ID2001, club, bắt đầu90m phía sau. Cop hoạt động khi player đã đi≥350m, chase/điều chỉnh tốc độ theo target, attack khi có gate. Pursuit tính braking-distance envelope bằng integer square root trước contact; test natural chase đã bắt lỗi cop phanh quá muộn, vượt quá stopped player163m và không thể bắt, rồi xác minh bản sửa tự đến/bust player đứng ở500m từ spawn−90m. Giữ trong5m dọc,2,6m ngang khi player<5,5m/s đủ180tick sẽ Busted. Fine=400×(level+1). Cop phanh khi không còn player active hoặc vượt đích quá50m; tránh coast vô hạn làm snapshot vượt miền hợp lệ. Tất cả khoảng cách/activation/timer này là tuning mới; P01 native có quan sát Busted180tick countdown nhưng không chứng minh chính các điều kiện mét này.

Pedestrian là baseline **đã nhìn thấy** trong video V12: đoạn31:06,5–31:08,0 cho thấy người băng qua bên cạnh bike đang remount. Vì vậy P04 bổ sung pool6 người, Waiting/Walking/Stumbled, gồm đi/chờ ở shoulder±7,7m và mỗi3spawn có một người sang đường. Spawn cách≥300tick và ở trước player150–220m; không xuất hiện tức thì ngay đầu xe. Despawn sau nhóm120m, tái sử dụng instance. Roadside đi dọc tuyến; crossing đi ngang1,2–1,6m/s, chờ ở shoulder trước lượt tiếp. Stream PRNG riêng không thay đổi draw sequence traffic/combat.

Swept contact dùng proxy radius0,3m/height1,8m: impact>12m/s làm bike crash(health−350,condition−8), tốc độ thấp dừng xe và hit-stun nhẹ. Pedestrian Stumbled180tick với pose không graphic, rồi Waiting120tick→Walking; không teleport. Collider chỉ hoạt động khi không Stumbled, tránh trừ damage lặp trên một người đã ngã. Test xác minh spawn budget/distance, roadside không drift, crossing liên tục, high/low-speed contact, hồi phục và cùng collision rule trên shoulder. Đây là **rule/tuning mới**, không claim đã reverse được original pedestrian AI, spawn probability, collider hay damage.

Traffic IDs giới hạn3001–3999, pedestrian4001–4999, wrap và skip ID đang active. Soak301.000tick giữ hai ID đầu đang active qua thời điểm wrap để xác minh không reuse nhầm hoặc đụng namespace. Event ID riêng vẫn tăng đơn điệu; vòng tái dùng actor ID cách xa cửa sổ event transient.

## Race và campaign local

Finish chỉ nhận rider đang có state lái được đã vượt2.200m. Police không dự rank. Rank đang đua theo distance rồi ID; người đã finish giữ rank. Finish cùng tick ID thấp trước là tie policy mới, vì higher-level original tie order chưa khép. Finish event/result chỉ được tạo một lần.

Offline qualification hạng1–3; bảng reward hạng1..14 `[1000,750,500,400,300,250,200,160,130,100,70,50,30,20]×(level+1)` và fine400×(level+1) lấy từ P01. Bản mới tạm áp dụng reward cho mọi finish hợp lệ; chưa claim khép toàn bộ branch reward eligibility/mode trong binary.

`LocalCampaignProgress` thử cơ chế 5 course bits, qualify mask0x1f tăng level0..4, cuối level4 Completed. Run ID monotonic chặn apply lại reward/fine. Credits chỉ là **local provisional data**, không phải số dư tài khoản online, không ghi vào database OCI. Đây là rule scaffold có tests đủ25course/level outcomes; **chỉ có một route playable** ở P03/P04, chưa có5environment×5variation để tuyên bố full campaign content.

## Bằng chứng và giới hạn nghiệm thu

Chạy `dotnet run --project src/Tests/RacingBois.Gameplay.Tests -c Release`. [Kết quả](../p03/gameplay-validation.json):31/31PASS gồm wrong-side/reach/height/fallen misses, damagepool, cooldown equality/held hitcadence, simultaneous fatal+finish, CRT steal, recovery không snap, wreck không remount, police contact180tick/natural chase, collider theo art bounds, rank/reward idempotence, campaign, boundedAI/traffic/pedestrian,301.000tick actorID soak và20.000tick golden replay. [P03](../p03/driving-and-replay.md) chứa performance/route metrics và3000tick startup golden dùng cross-runtime.

Các test controlled contact arena chỉ chứng minh luật khi đã có contact; natural chase fixture bổ sung một stopped target, không chứng minh chase mọi tình huống. Replay có bot combat, cả5bot finish và một player aggressive bị wreck. Controller giữ tim đường có player về đích43,083s. Human Web combat capture, đối chiếu video side-by-side với original và đo cảm giác timing/pose phải được lưu riêng; test C# không thay được gate đó. Chưa có tuyên bố100%logic, toàn bộ content, final art, production multiplayer hay parity physics.
