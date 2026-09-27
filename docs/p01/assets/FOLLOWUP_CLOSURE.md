# P01 follow-up — RPTH seeds, legacy RRFD reachability và animation clock

Ngày: 2026-09-21. Thực hiện thêm trong khi P02 Unity Web build chạy. Nguồn giữ nguyên; không chạy executable trực tiếp trong phần asset follow-up này.

## 13 RPTH endpoint differences đã được giải thích ở mức native behavior

Đã thực thi **nguyên mã máy** `0x451970`, `0x4519f0`, `0x451a40` bằng Unicorn trên toàn **109 RPTH / 34.182 samples**, cả chiều thuận và nghịch. Không hook/thay thế external service nào. Có 171.466 kiểm tra scalar, 3.014.338 instruction đã thực thi trong hai direction traces; mọi sample pair và accumulator đều khớp reference equation.

Kết quả: `header.end == header.start + sum(secondByte)` **không phải invariant được native loader hoặc updater bắt buộc**. Header +12 và +14 là hai seed độc lập. Với sample index `k`:

```text
forward(k) = signed16(header+12) + sum(delta[0:k])
reverse(k) = signed16(header+14) - sum(delta[k:count])
reverse(k) - forward(k) = endSeed - startSeed - sum(delta)
```

Vì vậy 13 source paths có chênh lệch constant giữa hai hướng ở **mọi** sample, không phải decoder bỏ sót prefix/suffix. Đã kiểm các type0 NOD sử dụng những path này: `node.length == RPTH.count` ở cả 13 trường hợp. Không có căn cứ nói chúng được trim để khớp seed.

| Course | SGS chunk offset | Reverse − forward, raw units |
|---|---:|---:|
| CANYN | 17900 | +283 |
| CANYN | 22824 | −33 |
| CANYN | 31992 | −211 |
| CANYN | 36032 | +852 |
| HIWAY | 11064 | −207 |
| HIWAY | 75572 | +63 |
| MEDLY | 1836 | −56 |
| MEDLY | 19312 | +118 |
| MEDLY | 37344 | +93 |
| MEDLY | 43932 | −458 |
| MEDLY | 55840 | −62 |
| MEDLY | 61612 | −228 |
| MEDLY | 70672 | −616 |

Counterfactual trong **emulated memory** đổi riêng reverse seed MEDLY +777: forward initialization không đổi, reverse initialization tăng đúng777. File nguồn không thay đổi. Đây là bằng chứng dataflow, không phải chỉ thống kê tương quan.

Native caller ordering cũng đã thực thi qua `0x452cb0` và `0x452e10` với hai node type0 đúng layout, optional resources null, không hook. Node A có10 samples `(0,1)`, seeds0/99; node B seeds123/133. Khi A đi qua boundary sang B, native trả result1, position0, accumulator123 của B; nó không sửa seed B hoặc kiểm endpoint của A. Đi ngược B→A ở half sample trả accumulator98, lấy reverse seed99 rồi trừ delta1. **Node transition khởi tạo lại accumulator trước khi updater xử lý residual movement.**

Ngoài ra updater chỉ áp **một** sample delta cho một call vượt boundary, kể cả delta position lớn hơn256. Fixture0/127/128/255/256/512/768 và chiều nghịch đã kiểm. Không thay native rule bằng một integrator tự động cộng mọi sample bị nhảy qua rồi gọi nó tương đương.

[rpth_native_execution.json](rpth_native_execution.json) lưu source binary hash, payload hash, forward/reverse trace hash, native assertions, seed counterfactual và caller fixture. Harness x86 chỉ điều khiển vòng lặp và lưu kết quả; nằm trong scratch region của bản sao emulated image. Byte ranges của các hàm được kiểm không sửa, file nguồn không ghi. Đây là **component execution**, chưa phải gameplay run xuyên đủ 13 đoạn.

**Đóng được:** format, exact updater math, independent seeds, constant discrepancy và node-boundary reset behavior. **Chưa được chứng minh:** ý định của tác giả dữ liệu; đây là sửa đổi mod hay có sẵn trong bản vanilla; ảnh hưởng trực quan của từng discrepancy ở mọi route/branch. Vì thế không gọi nó “intentional design” hoặc tự sửa seed để ép khớp.

## Toàn bộ 1.179 legacy 12-byte RRFD đã phân loại theo use path

| Nhóm | Records | Bằng chứng và phạm vi |
|---|---:|---|
| GLOBAL + DAT storage | 742 |326 rider +45 cop +326 shadow +45 cop shadow; loader `0x443610/0x4436a0` nạp bank DAT riêng. Empty DAT slots vẫn là empty, không tạo pixel giả. |
| Không được sequence CANS nào tham chiếu | 176 |Đã duyệt đầy đủ 2.340 sequences /6.161 frame refs. Không frame legacy nào trong nhóm này xuất hiện trong bất kỳ CANS sequence tương ứng. |
| root/4/*/1 không được PC getter path đã tìm thấy chọn | 255 |Renderer `0x44b71d` push0; `0x44b724` EDX=4; `0x44b729` gọi selector `0x44acd0`. Primary sibling root/4/*/0 có đủ pixel/LOD data. |
| family196/root/7/{0,1}/1 | 6 |Không tìm thấy direct getter chọn root7 trong callsites đã enumerate. Primary sibling có pixel. Vẫn ghi phạm vi chưa chứng minh với indirect/computed access. |

**Không có non-DAT legacy missing-pixel record nào được CANS sequence tham chiếu.** Đây là kết luận hữu ích cho animation replacement coverage. Nó không tự chứng minh global dead-code/unreachability của toàn chương trình; game có thể chọn frame trực tiếp ngoài CANS hoặc dùng access chưa được khảo sát động.

[legacy_rrfd_classification.json](legacy_rrfd_classification.json) giữ đủ1.179 rows, CANS references, sibling primary, native callsites và caveat từng nhóm. Toàn bộ direct calls nhận diện được tới ba family getters `0x44ac00`, `0x44acd0`, `0x44ada0` đã xuất kèm instruction windows; không dùng “không thấy hình trong atlas” để kết luận asset không cần. Giữ nguyên legacy slots trong research catalog; không xóa hoặc đếm chúng thành assets độc lập cần copy.

## Nominal animation duration đã khóa với logic agent

Native loader `0x40b567` chia CANS sequence rate cho20, ghi byte runtime +0xc. Native updater `0x43aecb..0x43aecf` đọc byte đó dạng signed rồi cộng vào clock60Hz. Với corpus hiện tại, 2.340 sequences có duration1..120 ticks, tức1/60..2 giây/frame; parser đã xuất `runtime_duration_signed_byte` và `nominal_duration_seconds_60hz`.

Logic agent đã thực thi28 exact-byte animation fixtures trong [parity-fixtures.json](../logic/parity-fixtures.json), gồm equality deadline, advance, loop và catch-up. Updater chỉ advance nhiều nhất **một frame/call**, kế tiếp cộng duration vào deadline cũ. Vì vậy nominal duration không đảm bảo rendered wall time khi game bị lag hoặc updater gọi thiếu; không gọi số đó là FPS playback bắt buộc.

Hit windows, attachment/anchor semantics và interaction với toàn bộ animation gameplay states vẫn cần mapping riêng. Xem [logic report](../logic/LOGIC_P01.md) cho actual game traces và giới hạn runtime coverage.

## Gate sau follow-up

- RPTH endpoint mismatch không còn là “chưa hiểu decoder”: exact source behavior đã có native fixture. Physical units/full branch geometry vẫn mở.
- Legacy pixel inventory đã có use-path classification đầy đủ; CANS animation coverage không thiếu pixel do176 unused slots. Sáu root7 slots và proof ngoài direct getter vẫn giữ scoped gap.
- Nominal CANS clock/duration đã đóng; không đóng hit-window/anchor/render-quality gates theo suy luận.
- Full source-game parity vẫn chưa được tuyên bố100%; không dùng scope closure của ba mục này để thay thế dynamic full-game coverage.
