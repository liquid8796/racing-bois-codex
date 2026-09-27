# Racing Bois — kiểm toán logic native từ bản mod

Ngày phân tích: 2026-09-21. Nguồn chỉ đọc: `C:\Users\Liquid\Downloads\Unity\racing_bois_mod`.

## Kết luận và giới hạn bằng chứng

Đã khôi phục có bằng chứng instruction-level các phần **save/checksum, bảng 15 xe và giá, đổi xe, phí sửa/phạt, progression 5 level, hit range, hệ số damage, chuyển vũ khí, một phần AI/PRNG và định dạng state mạng**. Có 39 vùng mã được tách riêng kèm VA, file offset và SHA-256. Đây **không phải toàn bộ source code và chưa đạt 100% logic**. Không chuyển số lượng strings, số instruction hay 39 vùng mã thành phần trăm parity.

Theo cập nhật của người dùng, **toàn bộ assets production phải làm mới từ đầu; bản gốc chỉ làm tham chiếu**. Evidence, strings và dữ liệu trích xuất trong thư mục audit là tài liệu nghiên cứu, không được đưa thẳng vào Unity build.

Không chạy `RacingBois.exe`, launcher, batch hay import registry; không sửa originals. Toàn bộ kết luận runtime dưới đây là suy ra từ binary/data, chưa được xác thực bằng debugger/gameplay có kiểm soát. Các nhãn hàm đều do người phân tích đặt, không phải tên symbol của nhà phát triển.

Mức bằng chứng:

- **C — code/data:** instruction hoặc byte cụ thể trực tiếp chứng minh thao tác; còn có thể thiếu điều kiện ở caller khác.
- **V — validated:** kết quả decoder kiểm tra lại độc lập trên tất cả mẫu liên quan trong folder.
- **T — text:** nội dung localization cho biết tính năng/ý định, không tự chứng minh implementation.
- **H — hypothesis:** tên ngữ nghĩa/đơn vị suy luận; không được dùng làm tiêu chí nghiệm thu parity trước khi xác minh.
- **U — unrecovered:** chưa có bằng chứng đủ.

## Binary và nguồn gốc kỹ thuật

| Mục | Kết quả |
|---|---|
| Main executable | `RacingBois.exe`, 541,184 bytes, PE32 x86 machine `0x14c` |
| SHA-256 | `66ab853c5b7b73b82a7c22a0478f5ba5b1066ed27028ef96449f5fe36a6101c5` |
| Image base / entry | `0x400000` / VA `0x4583c0` |
| Linker metadata | 3.0; PE timestamp là metadata có thể bị sửa, không chứng minh ngày phát hành |
| `.text` | VA `0x401000`, raw offset `0x400`, virtual size 394,895 bytes |
| Imports | 267 symbols, gồm DirectDraw, DirectSound, WinMM, WinSock, TAPI và Win32 |
| Exports main | 0; không có symbol gameplay nguyên bản qua export table |
| Launcher | PE32 x86, 38,400 bytes; chưa reverse toàn bộ launcher |
| Các DLL hỗ trợ | AWEMAN32, RacingIcon, RacingProp là native PE |
| Locale DLL | ENU/DEU/ESP/FRA/ITA chứa resource strings |
| Font giả đuôi DLL | BADLOC/FUTB/FUTD/FUTR có sfnt/TrueType signature, không phải PE |

Imports DirectDraw/DirectSound cộng với palette/sprite/container native chứng minh đây không phải Unity project đã build; không thể lấy C# hoặc scene Unity từ thư mục này. Không có suy luận rằng đổi tên executable đã đổi toàn bộ engine.

`racing_bois.bat` chứa `taskkill -F -IM explorer.exe`, chạy game rồi `start explorer.exe`; `cra.bat` gọi registry import. File `REGEDIT.REG` viết nhánh HKLM `SOFTWARE\Vexalith Interactive\RBois95`, Path và các lựa chọn game. Đây chỉ là quan sát nội dung file, chưa thực thi.

## Chế độ, campaign và UI

**T:** ENU IDs 2–5 mô tả Thrash và Big Game; IDs 13–14 mô tả Mano-à-Mano. IDs 16–20 đặt tên 5 địa điểm The City, Sierra Nevada, The Peninsula, Napa Valley, Pacific Highway. IDs 32–39 có 8 nhân vật chọn. IDs 58/60/62 có Rat/Sport/Super. IDs 91–95 có level 1–5. IDs 72–73,88–89 mô tả 320×240 và 640×480.

**C:** vùng `0x41f6d0..0x41f70a` kiểm tra byte `0x4b8a13 == 0x1f`; khi đạt điều kiện, xóa mask. Nếu level byte `0x4b8a12 == 4`, trả transition `0x23`; nếu chưa, tăng level rồi trả `0x20`. Do đó **5 level chỉ số 0..4** và **5 bit qualification** là bằng chứng mã, không chỉ suy từ text.

**C:** `0x449186..0x4491b2` map lựa chọn course 1..5 sang `1,2,4,8,16` rồi OR vào qualification mask trong nhánh event tương ứng; multiplayer mode 3 bỏ qua đoạn OR. Chưa khẳng định course-selection 1..5 map chính xác thế nào sang mọi file course nếu không đối chiếu loader/course table.

**C:** global mode `0x4753b0 == 2` tham gia cash/progression; mode 3 có network behavior; ID 1 và 2/3 phân biệt ở các handler. Tên mode phải đối chiếu UI trước khi đóng băng API enum mới.

**C:** `0x41f630..0x41f69e` khởi tạo lại level, qualification, tiền và xe trong nhánh mode 2. Bảng tiền uint16 tại `0x469000` và bảng xe theo internal character ×5 tại `0x4641c8` đã trích vào `economy_tables.json`. `0x415fc0` map selection index 1..8 sang internal IDs `[8,7,2,5,4,6,3,1]`; index 0/default map0. Không tự đặt tên nhân vật vào các index nếu chưa xác minh UI.

## Xe, kinh tế và progression đã khôi phục

**C/V:** loader `0x405e30..0x405e7d` mở `Data/BikeSpec.RSC`, truy vấn type `0x53504543` (`SPEC`) với IDs1..15, lưu pointer ở `0x47ea40[index]`. Parser container của asset audit xác nhận 15 records, mỗi record 356 bytes = 89 int32. Internal bike index là SPEC ID−1.

Tên xe không được đoán từ thứ tự showroom: bảng jump ở `0x420b0c` dẫn tới string ID chính xác; giá uint32 tại `0x468fc0`.

| Index | SPEC ID | Tên resource | Giá |
|---:|---:|---|---:|
| 0 | 1 | Sport 450 | 4,495 |
| 1 | 2 | Swallow | 3,249 |
| 2 | 3 | ZYX 250 | 3,497 |
| 3 | 4 | Rat | 5,489 |
| 4 | 5 | Pico | 2,999 |
| 5 | 6 | Super Sport | 29,998 |
| 6 | 7 | Raven N | 18,999 |
| 7 | 8 | Vipera N | 40,000 |
| 8 | 9 | ZYX 750N | 21,789 |
| 9 | 10 | Assassino N | 34,888 |
| 10 | 11 | Vampiro | 13,796 |
| 11 | 12 | DMG M10 | 16,875 |
| 12 | 13 | ZYX 750 | 11,988 |
| 13 | 14 | Grande | 9,199 |
| 14 | 15 | Aggressore | 6,994 |

**C:** `0x421606` chặn mua đúng xe đang sở hữu. `0x42161c..0x421694` thực hiện:

```text
trade = price[currentBike] >> 1
if cash + trade < price[selectedBike]: reject
else:
    cash += trade - price[selectedBike]
    currentBike = selectedBike
    dirtySave = true
```

`>>1` là làm tròn xuống đối với giá không âm: Sport450 bán lại 2,247, không phải 2,247.5.

**C:** handler `0x4214e0..0x421595` chỉ xử lý kinh tế ở mode2. Nhánh khác event `0xc3` tính repair = unsigned `price[currentBike]/10`, lấy phần nguyên. Nhánh event `0xc3` tính fine = `400*(levelIndex+1)` bằng LEA/shift. Không đủ tiền sẽ chọn text ID198 (hết tiền/game over) rồi gọi profile reset; đủ thì trừ tiền. Text IDs194 và197 độc lập xác nhận repair/fine tương ứng.

**C:** bảng reward tại `0x46ab48`, stride `0x4c`, bắt đầu `[1000,750,500,400,300,250,200,160,130,100,70,50,30,20]`. `0x421365..0x42137a` lấy giá trị theo position, nhân `(levelIndex+1)` rồi cộng cash trong nhánh đủ điều kiện mode2. **Không khẳng định mọi vị trí đều được award chỉ vì có bảng**: caller và điều kiện hiển thị/qualification còn cần mô tả đầy đủ. Top-3 qualification cần đối chiếu video và nhánh race-end, chưa được coi là đã chứng minh toàn bộ từ hàm thưởng này.

## Combat: công thức và điều kiện có địa chỉ

Các vùng `0x409510`, `0x4095d0`, `0x4096f0`, `0x409ad0`, `0x409c10` tạo cụm state animation → kiểm tra hit → transfer weapon hoặc damage → knockback/animation. Các tên ngữ nghĩa dưới đây có phần H; phép toán/offset là C.

### Hit range

Hàm `0x409c10..0x409c8f` nhận attacker, target, side flag, attack/weapon index. Với `A` và `B` là hai object:

```text
side = (B.field_28 > A.field_28)
if side != requestedSide: reject
if abs(A.field_1c - B.field_1c) >= 0x40: reject
range = 7 if weaponId == 1 else 8 if weaponId == 2 else 5
if abs(A.field_28 - B.field_28) >= (range << 12): reject
return abs(A.field_20 - B.field_20) < 0x3000
```

Ngưỡng là so sánh chặt `<`, không phải `<=`. Ba trục dùng scale khác nhau; **chưa gọi 0x40 là mét, pixel hoặc frame**. Gán field_1c longitudinal, field_28 lateral, field_20 vertical là H cần trace vị trí/render.

### Damage theo sức và loại attack

Tại `0x409ad0`, `stats = attacker.link_2fc.link_1e0`; lấy `base = stats[+0x30]`, denominator `stats[+0x34]`, numerator `stats[+0x38]`:

```text
ratioQ8 = truncTowardZero((stats_38 << 8) / stats_34)
effective = arithmeticShiftRight(ratioQ8 * base, 8)
effective = max(effective, truncTowardZero(base / 2))
weaponQ8 = [256,320,384,64][weaponId]  // VA 0x465a00
damage = truncTowardZero(effective * weaponQ8 / 256)
secondary = truncTowardZero(damage / 4) + 1 if weaponId == 3 else 0
applyDamage(target, damage, secondary, 5 if secondary >= 1 else 4)
```

Hệ số tương ứng **1×,1.25×,1.5×,0.25×**. Kết luận ID0=punch,1=club,2=chain,3=kick là **H mạnh**, phù hợp range và text hội thoại chain mạnh hơn club; không xem text là thay thế cho việc nối sprite/SFX enum. Do vậy API dữ liệu audit giữ numeric IDs.

Phép tính có 32-bit signed overflow và x86 truncation; pseudocode trên mô tả miền giá trị gameplay thông thường, không bảo đảm kết quả overflow/path dữ liệu hỏng.

### Hai pool chịu damage

`0x4050c0..0x4051d7` có ownership/authority guard trước nhánh apply. Trong nhánh được phép:

```text
stats_38 = max(stats_38 - 4*damage, truncTowardZero(stats_34 / 2))
stats_3c = max(stats_3c - 64*damage, 0)
return stats_3c
```

`0x4051e0..0x4052b1` có guard tương tự và thực hiện `object_2f0 = max(object_2f0 - secondary, 0)`.

Gọi pool đầu là endurance/health của rider và pool object_2f0 là condition xe là H từ chuỗi callers; phép trừ/clamp là C. Wrapper `0x4052c0` gọi cả hai, khi một pool hết gọi `0x403d60` với thông số fall; chưa reverse đầy đủ hàm fall/recovery. Damage type2 nhân7/4, type3 chia8, type4/5 giữ nguyên; dispatch table `0x40544c`. Không tự áp dụng modifier type2/3 cho punch nếu caller không truyền các type đó.

### Lấy vũ khí và cooldown

Nhánh `0x4097c0..0x4098f1` kiểm tra timestamp, target animation, attacker current attack0, target current attack khác0 và3, target đang trong attack-state; gate `(randomValue & 3) == 3`. Nếu thỏa:

- Copy target `link_2fc[+0x1c8]` sang attacker `+0x1c8` và `+0x1d4`.
- Set target cả hai fields về0.
- Attacker `+0x1cc = globalClock + 300`.
- Gọi network event và animation transitions.

**Không gọi đây là 300ms hoặc 5giây** vì clock đơn vị chưa xác minh. Cũng không khẳng định xác suất độc lập25% mỗi hit: branch phụ thuộc nhiều gates và PRNG.

Nhánh hit thường kiểm tra target `+0x1d0 < globalClock`, rồi đặt next-hit timestamp `globalClock + 6*(5-levelIndex)` (`0x40997c..0x40999c`). Điều này cho thấy cooldown rút ngắn theo level, nhưng duration thực tế còn phụ thuộc clock tick.

Knockback cập nhật object field `+0x288` của attacker/target, thêm ±3000 và ∓1000 theo side, attackId3 thêm ±8000 cho target; clamp theo ±field`+0x29c`. Chưa ánh xạ field này sang lực/tốc độ/lean với đơn vị Unity.

## Physics và AI: cái đã biết, cái còn thiếu

**C:** SPEC application `0x405ea0..0x406070` đọc các fields +0,+4,+8,+0xc,+0x10,+0x14,+0x18; copy 76 dword từ SPEC+0x1c vào object+0x1c4. Nó nhân/chia integer với hằng75, shift8, đặt object+0x29c=0x2e00, +0x2c4=20, +0x248/+0x2dc=0x2000, clamp một số divisor tối đa15. Đây là fixed-point parameter preparation thực tế; chưa đủ bằng chứng gán 89 fields thành horsepower, mass, grip, gear ratios.

**C:** SPEC cuối records của 4 xe Nitro khác0 trong dải fields83..88; các xe khác có zero. **H:** dải đó là thông số Nitro; chưa khôi phục duration/charge/recharge/runtime trigger.

**C:** `0x409460` AI attack candidate dùng modulo theo byte parameter ở character-data+0x1d0 và+0x1d1, chọn attack type3 hoặc equipped type; `0x4096f0` điều chỉnh response theo level. Nhãn AI dựa trên non-player caller assignment và flow, chưa chứng minh mọi trạng thái AI/police.

**C:** `0x441750` trả global `0x49bce8` ở mode3; các mode khác tail-call `0x455eb0`. Hàm thứ hai cập nhật seed theo LCG `state = 214013*state + 2531011 (mod 2^32)`, trả `(state>>16)&0x7fff`. Đây là điều cần bảo toàn nếu làm replay deterministic. Chưa chứng minh network truyền seed/counter ở packet nào.

**U:** integrator timestep, input-to-steer, gear shift thresholds hoàn chỉnh, grip/braking, road-height/curve sampling, jump/gravity, rigid-body response, bike-vs-traffic, AI overtake/rubberband, police pursuit, pedestrian behavior, fall/recovery/respawn, complete weapon-frame windows, camera smoothing và race finish ordering. Muốn parity cao phải làm dataflow + trace thực tế các vùng này; không dùng PhysX mặc định rồi tuyên bố giống100%.

## Save: layout và kiểm tra toàn bộ mẫu

Hàm write `0x42f000..0x42f103` xóa buffer160bytes tại `0x497090`, copy32bytes từ state`0x4b8a10`, copy10records×12bytes từ bảng quan hệ/progress stride0x204, ghi magic/checksum, WriteFile160bytes. Read `0x42f110` kiểm tra magic, checksum rồi copy ngược. Không có bằng chứng mã hóa.

| File offset | Kiểu / length | Nghĩa |
|---|---|---|
| 0x00 | uint32 | checksum |
| 0x04 | uint32 | magic0xcafedead |
| 0x08 | u8 | player slot (H về tên; state offset0) |
| 0x09 | u8 | character selection; map qua0x415fc0 |
| 0x0a | u8 | level index0..4 |
| 0x0b | u8 | 5-bit qualification mask |
| 0x0c | u8 | current bike index0..14 |
| 0x0d | u8 | course selection |
| 0x0e | u8 | finish-position index (H từ reward caller) |
| 0x0f | u8 | unknown |
| 0x10 | uint32 | cash |
| 0x14 | 20bytes | player name, null-terminated trong các mẫu |
| 0x28 | 10×3int32 | record data; semantics từng field chưa đóng nhãn |

Checksum `0x42efc0..0x42effb` chạy trên156bytes từ offset4. Với remaining n giảm156..1, accumulate `sum += byte`, `weighted += n*byte`, `alternating += byte` nếu n lẻ, ngược lại trừ. Kết quả uint32: `((alternating<<16) | (sum&65535)) XOR weighted`.

**V:** 14/14 `.RRS` trong SAVES có magic và checksum đúng chính xác theo công thức phục hồi. 4file160bytes không đuôi ở root (`hem`, `heman`, `JO`, `sri`) đều toàn0, không phải save hợp lệ. Bằng chứng và fields đã decode ở `saves_decoded.json`; raw ở `saves_raw.json`. Không sửa save.

## Networking cũ: kết quả và khoảng trống

**C:** WinSock imports và callsites xác nhận cả datagram `socket/bind/sendto/recvfrom` lẫn stream `connect/send/recv`, cùng IPX, serial và TAPI. Native multiplayer đã có; không cần suy từ chữ Multiplayer trên UI.

- `0x441c90` dựng sockaddr IPv4 family2, protocol0, length16.
- `0x441cd0` dựng IPX family6, protocol1000, length14.
- `0x441b6a` truyền7000 (`0x1b54`) qua htons trong nhánh TCP/IP resource selector389; nhánh IPX truyền socket`0x4242`. Datagam path dùng socket type2.
- `0x4428a0` có stream-send loop; lỗi10035 (`0x2733`) dẫn Sleep(0)/retry. Không thấy partial-send recovery trong riêng đoạn này; không kết luận toàn stack không xử lý partial vì caller chưa audit đủ.
- `0x43c7e0..0x43c957` đóng gói record stride24bytes, byte0 là low-nibble player slot và high-nibble message type1/2; +1 uint32globalClock; +5/+6 lấy signed objectfields+0x5c/+0x60 >>16 (có saturation nhánh trên); +7 flagbit0; +8/+0xc/+0x14 copy objectfields+0x28/+0x1c/+0x20; +0x10 gói24-bit field với8-bit segment/resource index. Không tự đặt world units.
- Guard ở damage routines kiểm tra ownership table`0x4c4fb0` cùng local player trước mutation/network-send; **không chứng minh dedicated authoritative server**.

**U:** complete packet catalog/lengths, handshake/version negotiation, max-player gameplay limit, reliability model, resend, authority switching, desync recovery, NAT traversal, authentication, cryptography, cheating defenses. Không có bằng chứng backend tài khoản/database/lobby internet hiện đại trong bộ file này.

Game Unity Web cần transport/protocol/backend mới. Yêu cầu LAN hoàn toàn offline phải có host/local server + assets/client/auth-profile khả dụng trong LAN, không phụ thuộc CDN/OCI/OAuth/DNS công cộng lúc chơi. Đây là ràng buộc sản phẩm mới, không phải capability đã chứng minh của binary. Internet global phải có server authority và triển khai phù hợp RTT; không thể biến protocol WinSock/IPX này thành browser API bằng cách đổi endpoint.

## Localization và asset-loader evidence

**V:** giải mã6,832 RT_STRING entries từ5locale DLLs; ENU1,364 entries. `localization_strings.json` giữ file/languageID/stringID, có thể dùng checklist UI/game behavior. Không đếm chúng là6,832 tính năng.

**C/V:** DAT biker loader`0x4436a0` ưu tiên Hi nếu flag bật, fallback Lo; reads width/height uint8 rồi width×height palette bytes, descriptor stride8. Caller`0x443610` yêu cầu Bob/Shadow326slots và Cop/ShadoC45slots. Slot khác0 không bằng tổng slot; xem asset inventory để biết populated frames.

**C:** loader `Data/Bikers/Template.MIP` ở0x432f90 và representation PDAT dùng magic12345678, header runtime28bytes, content+0x0c count, offsetrecords content+0x1c stride12; loader/relocator cộng contentbase vào offset đầu mỗi record. Decoder asset có kiểm tra container riêng; audit này không thay thế visual QA. Các `.BOB` raw trong IMAGES là định dạng khác: horizon loader0x44c440 có scanline width720High/360Low, storage320/160rows theo length; runtime có branch crop297rows. Dash0x44c710 dùng640High/320Low, actualheight = bytesRead/width. Meter0x44c5d0 dùng190×64High/95×32Low. Không được coi đuôi file giống nhau là cùng schema.

## Ma trận phần chưa đạt100%

| Miền | Tình trạng hiện tại | Bằng chứng cần để đóng |
|---|---|---|
| Save | Decode+checksum14/14; tail chưa biết đủ nghĩa | controlled save-diff khi thay từng trạng thái |
| Economy | Bảng giá, trade, repair/fine, reward formula | complete reward/qualification eligibility + edge cases |
| Campaign | 5bits/5levels có code | trigger hoàn thành và map toàn course variant |
| Combat | damage/range/transfer/cooldown có code | map enum, clock units, full animation hit windows |
| Physics | SPEC raw + parameter preparation | integrator,input,collision,road sampling+matched traces |
| AI/police | candidates+PRNG+attack logic | FSM đầy đủ, parameter meanings, difficulty curves |
| Network | native transports+24byte state packer | full catalog, ownership protocol, loss/desync tests |
| UI/audio/cutscene | locale strings+loader evidence | screen transitions, triggers+video observation |
| Entire program | PE sections/imports/strings/disassembly retained | recursive CFG, all entrypoints/indirect calls+runtime coverage |

Đạt100% logic cần một định nghĩa kiểm chứng được: danh mục behavior hữu hạn, evidence cho từng rule, regression traces/fixtures và differential tests với original. Quét hết bytes thành assembly là inventory, không phải hiểu hết chương trình; không có source symbols thì reconstruction vẫn có uncertainty về tên/type/ý định.

## Tệp chứng cứ và tái chạy

- `pe_inventory.json`: PE, sections, imports, exports, resources, hashes.
- `RacingBois.exe.strings.json` và `RacingBois.xrefs.json`: offsets/VA và direct string/import references.
- `RacingBois.disassembly.tsv`: linear sweep của executable section; **có thể disassemble jump-table/data thành instruction giả**. Không dùng từng dòng ngoài vùng xác minh làm code truth.
- `function_index.json`, `functions/*.tsv`:39slices targeted, code hash và file offset. Một số slice chỉ là vùng liên quan, không bảo đảm phủ trọn hàm.
- `economy_tables.json`, `saves_decoded.json`, `localization_strings.json`: data phục hồi có nguồn.
- `tools/reverse-engineering/logic/README.md`: dependencies và lệnh tái lập.

Các analysis scripts chỉ đọc folder nguồn và ghi evidence vào workspace. Không có game implementation, cloud deployment hoặc Unity scene mutation trong phạm vi audit này.
