# P01 — HUD speed/distance và course length theo level

Nguồn: executable và ENU.DLL của bản mod được cung cấp. **Đã khóa arithmetic hiển thị bằng1.086 native-byte fixtures:**936 speed cases,100 distance cases,50 course-menu cases. [JSON kết quả](display_units.json), [fixtures đầy đủ](display_unit_fixtures.json), [native evidence slices](display_evidence/).

Đây là contract từ raw values sang số hiển thị. Chưa gọi raw world units là mét hoặc dùng menu length làm chứng minh quãng đường thật qua mọi nhánh.

## 1. Chọn hệ đơn vị

`0x42f340` gọi imported `GetThreadLocale` rồi `GetLocaleInfoA(locale, 0x0d, buffer=0x497248, 7)`. Hàm `0x42f490` trả metric nếu byte đầu buffer khác ASCII `'1'`. `0x0d` là LOCALE_IMEASURE:0 cho metric,1 cho US measurement system. Nguồn đối chiếu: [Microsoft LOCALE_IMEASURE](https://learn.microsoft.com/en-us/windows/win32/intl/locale-imeasure).

Native còn đọc decimal separator với locale type0x0e vào `0x497240`. Do đó phần formatter dùng ký tự locale, không cố định dấu chấm. Các ví dụ dưới dùng dấu chấm để dễ đối chiếu bảng.

## 2. Digital speed — chính xác bit shift/truncation

Input `v = signed32([player + 0xec])`; player pointer global `0x4642d8`. Hàm `0x4468e0` ghi output vào `0x49e10c`. Khi HUD mode byte `0x467a98` khác0, nhánh digital chạy. Các công thức sau giữ đúng arithmetic signed32 của nguồn; `sar` là arithmetic right shift, `trunc` chia về0:

```text
US / mph branch at 0x44697c:
    shown = max(0, (v sar 12) + (v sar 7) + (v sar 9))

Metric / km/h branch at 0x446950:
    a = signed32(v & 0xffffff87) sar 3
    b = signed32(v & 0xfffffe1f) sar 5
    c = signed32(v & 0xfffff0ff) sar 8
    shown = max(0, trunc((a + b + c) / 10))
```

`0x446991..0x4469a4` clamp digital negatives về0. Không được thay mph bằng `round(v/100)`, vì shift từng term gây bias/quantization khác. Hệ số liên tục của nhánh mph xấp xỉ `41/4096`, nhưng công thức bit-level mới là contract chính xác.

| Raw v | mph hiển thị | km/h hiển thị |
|---:|---:|---:|
| 0 | 0 | 0 |
| 1.000 | 8 | 12 |
| 4.000 | 38 | 60 |
| 8.000 | 78 | 124 |
| 10.000 | 99 | 158 |
| 12.000 | 118 | 188 |
| 16.000 | 159 | 254 |
| 20.000 | 199 | 318 |

Renderer `0x44706f..0x4470f5` đưa `0x49e10c` vào formatter `%d` rồi draw text. Đây là đường nối calculation→HUD number, không chỉ một phép toán giống speed. Debug option có thể hiển thị thêm giá trị chuyển đổi từ player+0x108; nó không thay input chính +0xec.

936 native fixtures thực thi toàn hàm `0x4468e0` không hook, ở mode0/1/2, cả metric/US, với negative values và hai phía của shift boundaries. Trường hợp mode0 trả needle phase chứ không phải số mph: xem dưới.

## 3. Analog needle branch

Nếu mode byte bằng0, `0x4468ea..0x446939` không đọc metric selector để đổi số. Nó tạo phase cho needle:

```text
t = signed32(
      signed32((v & 0xffffff80) << 4)
    + signed32((v & 0xfffffe00) * 4)
    + (signed32(v & 0xfffff001) sar 1))
phase = trunc(t / 200) - 1024
if phase < 0: phase += 4096
```

`0x447112..` đưa phase tới `0x44f510` khi dựng needle. Không coi phase là mph hoặc degrees. Dashboard image loader `0x416310..0x416358` chọn file `mHiDash/kHiDash` hoặc `mLoDash/kLoDash` theo cùng metric selector; ảnh dial đổi nhãn, phase arithmetic giữ nguyên. P03 nên tách digital-number adapter và needle-phase adapter nếu muốn đo đối chiếu HUD gốc.

Đã đối chiếu hình source SPORT: [mHiDash MPH](../../reverse-engineering/assets/samples/IMAGES_BIKES_SPORT_MHIDASH.BOB.png) có marks0/50/100/150/200; [kHiDash km/h](../../reverse-engineering/assets/samples/IMAGES_BIKES_SPORT_KHIDASH.BOB.png) có0/80/160/240/320. Đây là bằng chứng nhãn đơn vị và dial scale1.6 trong chính assets nguồn; ảnh nghiên cứu không đưa vào production.

## 4. Odometer/progress counter

`0x446a40` đọc `p = signed32([player + 0x44])`. Đây là **snapshot** của longitudinal position +0x1c: `0x438513..0x43851e` copy5 dword từ +0x1c sang +0x44 trong render preparation. Vì thế HUD có thể phản ánh snapshot gần nhất, không bắt buộc cùng thời điểm với state vừa integrate.

```text
US:
    signedTenths = trunc(((p sar 8) - 50) / 33)
Metric:
    signedTenths = trunc(((p sar 5) - 400) / 165)
storedCounter = signedTenths & 255
```

Output là byte global `0x49e115`. Renderer `0x446d90..0x446db1` đưa byte đó vào `0x42f450` với divisor10 và format `%02d%c%d`; ví dụ53 trở thành `05.3` với decimal separator locale.

Khác với speed, counter **không clamp**. Native IDIV trunc về0 rồi lưu AL; raw values ngoài phạm vi bình thường có thể wrap8bit. Đây là hành vi nguồn được test, không phải khuyến nghị để lặp bug này trong UI sản phẩm mới.

Threshold fixtures có đủ hai phía của offset50 samples và các bước0.1:

| p raw | Diễn giải | US tenths byte |
|---:|---|---:|
| 12.799 | Ngay trước50×256 | 0 |
| 12.800 | Offset bắt đầu50 samples | 0 |
| 21.247 | Ngay trước83×256 | 0 |
| 21.248 |50+33 samples | 1 |
| 29.695 | Ngay trước116×256 | 1 |
| 29.696 |50+66 samples | 2 |
| 4.096 |16 samples, numerator−34 → trunc−1 → AL |255 |

Nhánh metric tăng tenths đầu tiên ở raw18.080 (`(400+165)×32`).100 distance fixtures chạy nguyên hàm, không hook; includes negative values và byte-wrap boundaries.

**Display-calibrated inference:** phía US tương ứng33 RPTH samples cho0.1 mile,330 samples cho1 mile và84.480 raw Q8 position units cho1 displayed mile, sau offset50 samples. Đây là calibration theo **HUD**. Nếu sau này suy mét/sample từ quan hệ này, phải ghi là inference từ nhãn hiển thị, không phải bằng chứng engine dùng physical meters hoặc mọi axis cùng scale.

HUD metric/US có tỷ lệ nominal1.6, trong khi course menu dùng1.609. Không ép cả hai về một hệ số conversion hiện đại rồi tuyên bố pixel/numeric parity. Physical integrator/projection và quãng đường branch vẫn phải kiểm riêng.

## 5. Course display names và25 length values

Mapping được nối bằng byte/code, không đoán từ tên file:

1. Năm menu records ở `0x4691a0`, stride56 có selection IDs1..5 và title string IDs16..20, cùng callback `0x4213c0`.
2. Callback đọc selection ở+4. `0x4160c0` ghi selection1..5 vào `0x4b8a15`, trừ1 vào loader index `0x467a6d`.
3. Loader `0x441946..0x44195b` tra filename pointers tại `0x46df58` và thêm `.CRS`.
4. Menu calculator `0x420823..0x420834` index bảng `0x468f58` theo `5*(titleStringID-16)+levelIndex`, với levelIndex0..4 lấy ở `0x4b8a12`.

| Selection | File source | ENU title | Level1, miles | Level2 | Level3 | Level4 | Level5 |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | CITY.CRS | The City |5.3|8.4|11.5|13.5|16.3|
| 2 | HIWAY.CRS | Sierra Nevada |5.3|7.9|9.8|12.9|17.1|
| 3 | MEDLY.CRS | The Peninsula |5.3|8.0|11.0|15.0|16.8|
| 4 | NAPA.CRS | Napa Valley |5.0|7.6|10.6|12.8|18.5|
| 5 | CANYN.CRS | Pacific Highway |5.5|8.1|11.0|12.6|16.1|

Đặc biệt `HIWAY` là **Sierra Nevada** và `CANYN` là **Pacific Highway** trong bản được cung cấp. Không dùng tên nội bộ để đổi chỗ course.

Bảng lưu integer tenths. US chọn ENU27=`miles`; metric chọn ENU28=`kilometers`. Native metric menu branch ở `0x420848..0x420863` nhân double **1.609** tại `0x462008`, qua native float-to-int truncation, rồi format một decimal. Ví dụ tenths53→85, hiển thị8.5km.25 metric values đầy đủ nằm trong [display_units.json](display_units.json).

50 fixtures thực thi original menu function từ `0x420810` qua selection/math/FPU conversion, dừng tại `0x420869` **trước** localization/API output. Không thay kết quả math bằng hook: observation stop chỉ đọc EBX và unit-string ID. Như vậy kiểm được cả25 combinations ×2 unit systems mà không dùng native Windows UI hoặc game process.

Đây là **declared menu length**, không phải measured route length cho mọi split hoặc tọa độ finish thực theo level. Không thể lấy53×33 samples rồi tự đặt finish và coi đã reverse finish predicate. P03 có thể dùng bảng làm acceptance target hiển thị; P01 logic/track work còn phải nối level-dependent finish conditions.

## Phạm vi sử dụng cho P03

- Dùng các hàm pure trong `unit_display.py` làm reference cho numeric HUD acceptance; preserve signed shifts, truncation, snapshot và unit mode trong tests.
- Tách conversion hiển thị khỏi simulation units. Lựa chọn meters cho Unity là quyết định mới cần calibration, không tự gán từ `v/100`.
- Dùng mapping selector→file→display name và25 menu lengths để tránh nhầm course/level, nhưng không coi chúng là đủ track geometry/spawn/finish.
- Parent phase đã có actual native60Hz traces; các công thức ở đây bổ sung numeric display contract, chưa thay thế measurement của cả race.
