# P01 bổ sung — native hit, weapon transfer và AI/police

Ngày2026-09-21. Binary và renderer wrapper giữ cùng hash đã ghi trong [LOGIC_P01.md](LOGIC_P01.md). Đây là bổ sung cho bộ2074 fixtures và bốn native scenarios ban đầu; không thay thế hay xóa bằng chứng cũ.

**Đã khép có điều kiện** native weapon damage cho cả4 numeric IDs, một weapon-transfer path, cooldown equality, attack eligibility và danh tính/dispatch của opponent, cop và traffic. **Chưa khép toàn bộ AI hoặc100% game logic.**

## Điều kiện thí nghiệm được công bố

`native_probe.py --race --scenario hit/steal/police` giữ wrapper windowed, registryảo, fontsFR_PRIVATE, source read-only, seedCRT1996 và input polling có kiểm soát.

- **Hit arena:** chọn một rider đối thủ đang có trong race. Ngay trước mỗi call hit-processing gốc `0x4096f0`, đặt tọa độ player sát target: longitudinal−16, lateral−8192 so với target rider. Đây là placement được giữ trước từng cơ hội hit; không phải vật lý chạy cạnh nhau tự nhiên. Endurance target reset về native maximum, health/bikecondition đặt20000 **một lần mỗi weapon case**, để đọc nhiều hit mà không chết giữa bài. Các va chạm phụ do placement vẫn có thể xảy ra; validator chỉ nhận calls từ original weapon-damage producer.
- **Steal arena:** ngoài placement trên, target được equipID2 và khởi động attack qua **hàm chọn animation gốc** `0x4095d0`, để target ở attack frame đầu theo đúng gate. Không thay outputPRNG; branch transfer phải tự đạt random gate gốc.
- **Police:** gọi original spawn `0x406b80` tại tick180 trên segment hiện tại. Đây là controlled initial spawn; không chứng minh điều kiện spawn tự nhiên. Sau đó giữ nguyên AI/collision/recovery/bust code.

Không thay thế công thức/quyết định hit/range/damage/AI recipients. Frida đặt instrumentation/trampoline trong process để quan sát; EXE trên đĩa không bị sửa. Ngoài quan sát có các test initial conditions nêu trên. Các đợt cuối không có native exception hoặc Frida script error; không sửa file nguồn/bản sao. Registrywrites khi thoát race được virtualize, không chạm HKLM thật.

## 12 hits native và bốn cooldown-equality cases

Trace: [native-probe-hit.json](native-probe-hit.json). Validator: [native-contact-validation.json](native-contact-validation.json).

| Numeric attack | Tick hit | Base/effective strength trong bài | Native damage | Health delta | Bike-condition delta |
|---:|---|---:|---:|---:|---:|
|0|142,177,219|7|7|−448|0|
|1|260,291,322|7|8|−512|0|
|2|376,411,446|7|10|−640|0|
|3|495,526,570|7|1|−64|−1|

Validator đọc stats trước call thật, tính Q8/rounding/clamp theo công thức reverse, rồi so với stats sau call. Tất cả12 mutations khớp cả endurance, health và condition. Hệ số1/1.25/1.5/0.25 có integer truncation, vì vậy strength7 cho damage7/8/10/1. Không lấy delta health làm damage trực tiếp: poolhealth dùng64units/damage, endurance dùng4units/damage.

Strict cooldown được xác nhận trong trường hợp range và hit window đều đi tới range checker:

| Tick | Deadline target trước call | Range checker | Target animation trước call | Health delta |
|---:|---:|---:|---:|---:|
|290|290|accepted|4|0|
|291|290|accepted|0|−512|
|292|321|không cần hit lần nữa|9|0|

Có4 equality observations được validator kiểm. Vì original code dùng `clock > hitUntil`, expiry bằng clock vẫn chặn damage; cooldown30ticks ở level0 cho hit tiếp theo sớm nhất tick+31 nếu các gate khác thỏa.

Giới hạn: recipient ownership trong các native cases này là NPC do local process có quyền xử lý; network authority cases khác và timing combat khi di chuyển tự nhiên vẫn cần coverage. Kick impulse nằm sau damage-cooldown branch trong mã `0x4099fb`; không được tự coi cooldownhealth đồng nghĩa chặn mọi impulse/animation effect.

## Weapon transfer thực sự trong process

Trace [native-probe-steal.json](native-probe-steal.json), tick158:

```text
before: attacker weapon0, target weapon2
after:  attacker weapon2, target weapon0
attacker.stealUntil = 458 = 158 + 300
```

Các weapon fields/currentattack thay đổi trong original controller, không phải phần setup của kết quả. Setup target attack được nêu rõ ở trên. PRNG sử dụng original CRT với seed1996; không ép `(random & 3)` bằng3. Đây là bằng chứng native cho một chiều/chủng loại transfer và deadline5s danh định, không chứng minh tất cả weapon combinations, reverse-steal timing hoặc xác suất độc lập mỗi giây.

## AI attack eligibility:4.001 cases original instructions

[ai-decision-fixtures.json](ai-decision-fixtures.json) thực thi routine `0x4092e0` bằng Unicorn. Không có function substitution/Windows imports; có instruction observer. Dùng **nhánh PRNG mode3 thật** và globalcaptured random làm input fixture để duyệt đủ256 low-byte outcomes; không phải multiplayer test.

Recovered rule, trong miền integer không overflow:

```text
attacker.hitUntil < clock AND target.hitUntil < clock
abs(((attacker.velocity - targetRider.velocity) >> 4)
    + attacker.longitudinal - targetRider.longitudinal) < reachParameter * 16
abs(attacker.lateral - targetRider.lateral) < reachParameter * 8192
(random & 255) < aggression[level] * attacker.updateTicks
```

Aggression thresholds levels0..4 ở `0x465a10`: **[4,8,25,64,256]**. Đây là threshold trên một eligible evaluation, không phải xác suất theo giây hay mọi tick.

Nếu attacker là globalcop `0x4642dc`, thêm gates: currentattackID phải bằng1; target internalcharacterID<10; quan hệcop với target field+4 lớn hơn baseline+0x7c trong record12bytes. 4.001 cases phủ levels×dt1/2/3×256random outcomes, equality cooldown, strict distance, signed velocity prediction, police attack/character/relation gates.

## Runtime roles và behavior dispatch

Trace [native-probe-police.json](native-probe-police.json) đọc behavior ngay tại indirect dispatch `0x407c8e`, ghi transition qua routine gốc `0x408df0`.

| Role đã chứng minh | Nhận dạng live | Behavior IDs quan sát |
|---|---|---|
|Local player|pointer==global0x4642d8, slot0, internalcharacter0, ownership0|8 recovery và9 falling/no-op trong tracecop|
|Opponents|native racer constructors, template0x463ad8, ownership1, các slot đối thủ|1,2,3,4,5|
|Police|pointer==global0x4642dc; spawn constructor template0x464310; slot15; **internalcharacter9**; ownership2; weapon1|1 và4|
|Traffic|objecttype32, template0x46dde0, updatecallback0x440dd0, .CAR loader family|mode1 hoặc3; **không dùng bảng10 motorcycle behaviors**|

Constructor input15 của cop **không bằng** internalcharacterID sau setup; live characterID là9. Không dùng số slot/constructor argument thay cho semantic identity.

| Behavior | Callback | Bằng chứng/mô tả được phép |
|---:|---|---|
|0|0x408e30|no-op; initial state, chưa có ý nghĩa gameplay riêng|
|1|0x409000|navigation/lane-update chain; opponent vàcop đều dùng|
|2|0x4092d0|tail-jump thẳng tới behavior1; selector chọn khi target phía trước extent trong intent1|
|3|0x409460|attack choice/attack handling; opponent được quan sát vào state3|
|4|0x409ca0|target pursuit/relative speed positioning; opponent vàcop được quan sát|
|5|0x40a4f0|rear-target/lateral-follow branch; đối thủ được quan sát vào state5|
|6|0x40a560|handler follow-target tồn tại; **chưa tìm thấy trigger reachable** trong audited selector|
|7|0x40a5b0|handler follow-target tồn tại; **chưa tìm thấy trigger reachable** trong audited selector|
|8|0x40a600|recovery/running/remounting, đã quan sát native|
|9|0x40ac60|no-op trong falling state, đã quan sát native|

Selector `0x408ad0` có direct transitions1,2,3,4,5,8,9; constructor khởi tạo0. Chưa có direct transition tới6/7 trong các callsites đã audit. Điều này thu hẹp gap, **không đủ để tuyên bố6/7 unreachable toàn chương trình** khi còn indirect/data-driven entry paths.

Đã thêm đầy đủ CFG slices của `ai_relationship_and_speed_refresh`, `ai_behavior_selector`, `ai_behavior_transition`, `ai_attack_eligibility`, `police_spawn`, `live_traffic_update`. Relationship decay/selection và speed adjustment/rubberband được xác định có trong `0x4082f0`, nhưng chưa có differential fixtures đầy đủ cho toàn hàm này.

## Bust outcome và traffic lifetime correction

Cop native0→1 tại tick181,1→4 tại658. Local crash0→9 tại558,9→8 tại742. Originalcode requestoutcome4 tại963 với countdown180; native race teardown trả transition**29/0x1d** tại1142, map nguồn tới Busted. Hai timestamp cách179ticks theo thời điểm hook; không tự sửa số đo thành180. Campaign cash/fine không được kiểm chứng trong bài này: harness dùng state khởi tạo có cash0 và không chạy toàn luồng user menu.

Sampling traffic ban đầu giữ constructor pointers sau khi pool được recycle, tạo số mode không hợp lệ. Các records `native_traffic_state` trong trace `*-before-traffic-lifetime-fix.json`/`*-25s.json` **bị loại khỏi evidence**. Tool đã sửa để chỉ đọc vehicle **ngay trong callback update gốc0x440dd0**, khi object sống. Trace cuối có15 live vehicle observations, objecttype32, trafficType0..10, mode1/3 hợp lệ. Đây là15 observations/instances, không phải30 transitions. Không suy fulltrafficFSM từ chúng.

## Gate sau bổ sung

- PASS bounded: native damage4IDs, exact pool mutations, cooldown equality, weapon2 transfer, cop identity/pursuit/Busted result, motorcycle-vs-traffic dispatch distinction.
- PASS component:4.001 AI eligibility fixtures, cộng2.074 gameplay/animation fixtures trước đó = **6.075 instruction-level cases**; các số này không phải phần trăm game.
- OPEN: complete relationship/rubberband/avoidance behavior; natural police spawning; unclassified handlers6/7 reachability; all animation hit windows and weapon combinations under natural motion; full traffic collision/avoidance; full UI/economy/campaign traces; matched native-vs-Unity differential tests.

Gate100% logic vẫn OPEN. P02 có thể dùng những công thức đã kiểm và giữ extension points cho phần chưa khóa, nhưng không dùng contact arena để quảng cáo vật lý hoặc gameplay tự nhiên đã đạt parity.
