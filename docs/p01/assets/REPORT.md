# P01 — Reverse assets, course data và media

Nguồn read-only: `C:\Users\Liquid\Downloads\Unity\racing_bois_mod`. Ngày thực hiện: 2026-09-21. Tất cả output ở thư mục nghiên cứu này; **không có asset gốc nào được đưa vào Unity Assets hoặc production build**. Racing Bois phải được tạo assets mới từ đầu.

## Kết quả có thể kiểm chứng

| Hạng mục | Kết quả P01 | Giới hạn |
|---|---:|---|
| Course | 5 CRS, 141 node graph, 109 segment, 859 typed chunk, 34.182 path sample | World units, branch geometry, collision semantics còn cần dynamic |
| Course → nội dung | 600 RRSM family-stream events nối đủ 163/163 FAM không rỗng với course sử dụng | FAM là tập hợp nhiều leaf/variant, không phải 163 model độc lập |
| Texture/sprite | 4.172 mip-buffer record views, 2.303 buffer khác hash; 13.804 mip levels được decode | Palette runtime/remap, filtering/crop chưa được so với dynamic render toàn bộ |
| Animation | 1.721 RRAN, 7.632 RRFD; 3.369 pixel record decode trực tiếp, 3.084 native LOD aliases xác định | 1.179 legacy records đã phân loại theo DAT/CANS/direct getter trong follow-up; không bịa pixel |
| CANS/action | 197 CANS, 2.340 sequence, 6.161 frame-reference links, 63 source animation names | Nominal 60Hz duration đã có native proof; action/hit windows/anchors không tự suy từ tên |
| Biker DAT | Toàn bộ 869 frame không rỗng có preview trong atlas | 7 file chứa quality/shadow variants; không cộng thành số character/clip |
| Atlas | 176 group, 186 contact pages; toàn bộ 163 FAM không rỗng có hình tham chiếu | Atlas là nghiên cứu, không phải assets production |
| MIDI | 11 MIDS → Standard MIDI; 104.386 events đối chiếu độc lập từng byte và tick bằng mido | Chưa render với đúng SoundFont 1.0/synth gốc |
| Audio | 87 WAVE/RRA giải mã toàn bộ; 77.685.730 PCM frames | Loop/mix/pitch và event branches còn mở |
| Video | 61 filmstrips × 3 timestamp, kèm metadata/source reference | Sampling phục vụ catalog; không nói đã xem liên tục toàn clip |
| Media references | 89/148 WAV/AVI có literal-name reference trong executable | Literal reference chưa chứng minh trigger gameplay |
| Integrity | 374/374 file nguồn có SHA-256 không đổi | PASS này không có nghĩa reverse toàn game đạt 100% |

Mở [atlas tương tác](atlas.html), [content reference ledger](content_reference_ledger.csv), [course summary](course_summary.json), [kết quả validation](validation.json). Đây là phần triển khai thực của P01, nhưng **gate full asset-semantic/100% logic vẫn OPEN** với các vấn đề đo được ở cuối tài liệu.

## Course graph và stream content

Loader `0x441940` liên kết resource SGS vào global `0x475330`, NOD vào `0x475334`, rồi gọi `0x448030`. Parser mới đọc hết 5 file, kiểm EOF, pointer bounds, count, không có byte payload SGS bị bỏ qua, và tất cả node đều reachable từ root. Mỗi file có JSON đầy đủ và graph DOT trong [courses/](courses/).

**RNOD:** header 20 byte (`tag,size,count,flags,rootOffset`). Node type 0/1/2 dài 32 byte; type 3/4 dài 8 byte. Type 0 có `next/previous` tại +8/+12, segment index tại +16, length raw tại +20. Type 1/2 có ba link +8/+12/+16; chưa gán chúng thành hướng trái/phải nếu chưa có dynamic proof. Loader native tại `0x447b80` relocate graph; `0x447db0` gắn segment index qua stride 52. `0x452e10` so sánh vị trí với `node.length << 8`, nối node type 0, chuyển xử lý khi gặp type 1/2 và trả trạng thái terminal cho type còn lại.

**RSGS:** header 16 byte; `count` tại +8; array bắt đầu +16, stride 52. Native `0x447e50` relocate 12 pointer slots và ghi runtime length/segment ID vào slot 0/12. Bảng không phải danh sách XYZ vertices.

| Slot của segment | Tag corpus | Layout khôi phục |
|---|---|---|
| +4 | RPTH | Header 16; signed16 seed forward/reverse tại +12/+14; count × (signed8,signed8); padding 4-byte |
| +8 | RROB | Header 20; count × packed32 object records; native bitfield extractor `0x451a90` |
| +12 | RRSM | Header 24; count × 12-byte family-stream events |
| +16 | RBLD/RHIL/RMTN | RBLD header16 + sample pairs; RHIL header20 + 76-byte records; RMTN header24 + hai bank16-byte records + sample pairs |
| +20 | RSLD | Header16 + 36-byte records |
| +24 | RLAN | Header16 + 20-byte records |
| +28 | RHZD | Header16 + 8-byte records |
| +36 | RSEC | Header20 + 12-byte records |

Các tag RLAN/RHZD/RSLD không được tự gán hết field meanings chỉ dựa trên chữ viết tắt. JSON giữ toàn bộ byte gốc, record boundaries và fields chưa chắc nghĩa dưới tên `raw`.

**RPTH có bằng chứng xử lý thật:** `0x451970` chọn seed signed16 đầu/cuối; `0x4519f0` cộng/trừ byte thứ hai của sample khi vượt mỗi ranh giới 256 longitudinal units; `0x451a40` trả cả hai signed byte. 96/109 path có seed đầu + tổng byte thứ hai bằng seed cuối; 13 path khác nhau được ghi nguyên trạng ở [path_endpoint_differences.json](path_endpoint_differences.json). Không sửa nguồn để ép chúng khớp. Follow-up đã thực thi nguyên native code ở cả hai chiều: seeds độc lập tạo constant directional bias; node boundary reset trước khi updater xử lý residual. Không có invariant ép seed cuối bằng tổng. Đây chưa phải bằng chứng meters, radians hay cao độ tuyệt đối. Xem [FOLLOWUP_CLOSURE.md](FOLLOWUP_CLOSURE.md).

**RRSM nối đúng assets vào course:** mỗi record có longitudinal sample index tại +0, operation/state byte +4, family slot byte +5, resource word +8. State 1 dùng FAM ID low16. `0x44b170` dùng +8 gọi `0x415ad0`, hàm này nạp FourCC FAM; `0x452310` xử lý vị trí và chuyển state 1↔3 khi stream/preload. Không suy liên kết bằng tên file.

| Course | Node | Segment | Path samples | FAM khác ID được tham chiếu |
|---|---:|---:|---:|---:|
| CANYN | 24 | 18 | 6.043 | 36 |
| CITY | 19 | 15 | 5.886 | 51 |
| HIWAY | 32 | 26 | 7.060 | 21 |
| MEDLY | 43 | 35 | 7.244 | 38 |
| NAPA | 23 | 15 | 7.949 | 23 |

Có chia sẻ FAM giữa các course. Union đúng 163 FAM không rỗng; không cộng tổng cột cuối để tăng số nội dung. [course_family_references.json](course_family_references.json) giữ 600 event với offset và field; [content_reference_ledger.csv](content_reference_ledger.csv) nối tới atlas và source names để thiết kế replacement mới.

## Pixel, LOD, animation và metadata

Parser giải mã toàn CLGP và các full PC pixel chunks trong RRAN/CEL. Pixel marker `12345678` được native nhận tại `0x40b7b0`; mip body bắt đầu +36 tính từ chunk, relative pixel pointers được relocate từ đầu body. Mọi mip có dimensions, offset, mask, negative-double-stride và pixel hash; decoder đọc cả level nhỏ nhất, xuất ảnh base để không làm catalog phình bằng mip lặp.

`0x44a200..0x44a348` cho thấy nhiều RRFD record 12-byte **không chứa ảnh**: ở native branch cụ thể, ba LOD dùng chung pixel mip buffer. Parser chỉ nối alias khi điều kiện marker/flags/count khớp mã loader; đã giải quyết 3.084 alias. 1.179 record còn lại giữ trạng thái riêng, không đánh dấu giải mã thành công. Trong đó có 742 slot thuộc 4 GLOBAL animations (326 rider +45 cop +326 shadow +45 cop shadow), còn biker PC được nạp từ DAT qua `0x443610/0x4436a0`. [dat_rrfd_reconciliation.json](dat_rrfd_reconciliation.json) đối chiếu và giữ hai ngoại lệ dimensions: LOBOB slot23 và LOSHADOW slot176; không ép sửa chúng.

**Đính chính diễn giải P00:** RRFD +12 từng được đặt tên `x_raw`; loader cộng base vào slot này như một giá trị tương đối, nhưng corpus cũng có giá trị ngoài phạm vi/signed. Vì thế P01 giữ `auxiliary_pointer_offset` như tên slot theo hành vi loader và raw value, không khẳng định nó là coordinate X hoặc valid dereference. +16 cũng chưa được đặt tên anchor Y. Width/height +20/+24 được native mask xuống low16 tại `0x40b7e0`.

**CANS không phải một blob opaque:** leaf thực ra là chuỗi chunk CANS/SRCN/ATTR/ATTD/ACTN/HOLE/XTRA. Đã đi đúng EOF mọi 197 record. CANS versions trong corpus được phân nhánh, mỗi sequence header16 + frameCount×28, khớp `0x40b5a0`. Frame +2 là signed16 index 1-based được native trừ 1 để tìm RRFD (`0x40b717`). Toàn bộ 6.161 links của 2.340 sequences nằm trong RRAN sibling tương ứng. SRCN cho 63 tên file authoring, như Skater2, Cow, FlagGirl, Camaro, Police_C; đây là tên nguồn để tham chiếu, không phải đặt tên nhân vật/sản phẩm mới.

Native `0x40b567` chia sequence +8 cho20 rồi lưu runtime byte. Logic follow-up đã khóa updater `0x43ae90` đọc duration signed byte theo clock60Hz bằng28 native fixtures. Parser xuất cả nominal seconds: toàn2.340 sequences nằm1..120ticks. Không coi nominal duration là guarantee frame cadence khi runtime lag. ACTN có stride12 hoặc16 tùy corpus; ATTR lists và ATTD labels đã tách hết. FORM gồm112 leaf12byte: giữ cả LE/BE interpretations, không tự kết luận trường cuối là ID vì chỉ nhìn giá trị đẹp.

Atlas dùng palette source RGBX và cho index0 trong suốt để quan sát silhouette. Đây là chế độ preview có ghi nhãn, không phải xác nhận alpha của mọi shader, palette remap rider, lighting, crop và sampling của runtime. Đã kiểm trực quan sheet family001, external CITY và cloud candidate: textures, skateboarder và xe nhìn được đúng hình dạng. Chưa tự nhận đã review từng pixel của 186 sheet.

Hai BOB cloud đã có candidate 512×256 và 256×128, nhìn được atlas cloud và các ô test color. Không tìm thấy literal filename loader reference. Vì vậy dimensions vẫn ghi **INFERRED_DIMENSIONS_NOT_LOADER_VERIFIED**, cần dataflow/dynamic để đóng R03.

## Media và trigger references

11 RIFF/MIDS được chuyển thành SMF format0 với event delta nguyên gốc; tempo event trở thành meta tempo, channel events giữ packed bytes. Corpus có stream ID `0xffffffff` cho tempo events và 0 cho channel events; converter kiểm riêng điều kiện này, không giả vờ mọi stream ID đều zero. [MIDIEVENT của Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/mmeapi/ns-mmeapi-midievent) là nguồn định nghĩa delta tick và event payload. Independent mido 1.3.3 reparse đủ 104.386 events, so từng event/delta/tổng ticks và duration; tất cả PASS. Đây là conversion playback-ready bằng MIDI player có synth thích hợp, chưa phải render âm sắc SoundFont1 đúng gốc.

87 WAV/RRA đã được ffmpeg decode hết audio stream và wave module đọc đủ PCM frames, kèm hash PCM. 61 AVI đã có filmstrip ba thời điểm trên mỗi clip; P00 đã decode video toàn stream, P01 dùng thêm catalog nhìn được. File [trigger_references.json](media/trigger_references.json) lưu exact filename/stem literal, string VA, code references và raw pointer locations. 89/148 file có literal match; các template `%d`, caller state, random clip selection và audio mixing vẫn cần reverse riêng. Không gắn tên file `Wreck` thành chứng minh chính xác điều kiện trigger.

## Parity matrix và gate còn mở

| ID | Input/output kiểm chứng | Bằng chứng / test | Trạng thái |
|---|---|---|---|
| P01A-01 | RNOD bytes → mọi node/link reachable, count/EOF đúng | `nod_relocate`, `nod_segment_binding`; 10 course parser checks + corrupt/truncated fixtures | CLOSED cho structural graph |
| P01A-02 | RSGS → 859 typed chunks, không byte gap/overlap | `sgs_relocate`; 5 course JSON | CLOSED cho layout; OPEN world semantics |
| P01A-03 | RRSM event → FAM resource ID + course | `course_family_preload`, `family_resource_lookup`, `course_family_stream`; 600 refs,163-ID union | CLOSED cho source content association |
| P01A-04 | PC mip → indexed pixels mọi level | native marker/relocation;2.303 PNG roundtrip hashes,13.804 levels | CLOSED storage; OPEN runtime visual fidelity |
| P01A-05 | RRFD legacy12-byte → native LOD sharing | `rran_loader`;3.084 aliases | Storage/use-path classified; global indirect/dynamic reachability vẫn OPEN |
| P01A-06 | CANS → sequences/actions/one-based RRAN frame refs | `cans_sequence_lookup`, `cans_frame_lookup`;6.161 valid refs | CLOSED layout/link/nominal60Hz clock; OPEN hit/anchors |
| P01A-07 | MIDS → SMF event-equivalent | mido independent check11 files/104.386 events | CLOSED conversion; OPEN original synth output |
| P01A-08 | WAVE → complete PCM | ffmpeg and wave87 streams/77.685.730 frames | CLOSED decode; OPEN triggers/mix |
| P01A-09 | Media file → literal/data/code refs |89 exact references,61 filmstrips | PARTIAL; no branch-event equivalence claim |
| P01A-10 | Cloud BOB bytes → image dimensions |2 plausible preview sizes | OPEN native loader proof |
| P01A-11 | Source hash before/after |374 SHA-256 against P00 manifest | PASS unchanged |

Tiếp theo để đóng gate: trace original runtime trên bản sao, nối path sample coefficients tới road builder/physical units; đánh giá gameplay impact của13 independent-seed cases; verify indirect/dynamic use của legacy slots; map animation anchor/hit windows; dựng playback SoundFont1 và map media event branches. Những việc này không được thay bằng thêm counts hoặc screenshot tĩnh.

## Tái lập

Xem [tools README](../../../tools/p01/assets/README.md). Full pipeline đọc nguồn, lưu cache theo hash payload trong `.cache/` (bị gitignore), xác minh CRC khi đọc lại; mọi output nghiên cứu ở đây. Chạy `tools\p01\assets\run-all.bat`. Không gọi launcher/executable game, không ghi registry, không thay settings Blender/Unity.

Evidence slices là static x86 disassembly có VA, không phải original symbols/source C. Jump table bytes trong linear disassembly có thể hiện thành instruction; kết luận layout dùng các nhánh code và corpus consistency đã nêu. Tài liệu này không đóng gate 100% logic toàn chương trình.

Bổ sung đã thực hiện: [RPTH native closure, legacy use-path classification và animation clock](FOLLOWUP_CLOSURE.md). Full pipeline gồm closure fixtures đã được chạy lại; xem validation.json hiện tại.

Bổ sung calibration cho P03: [HUD mph/kmh, odometer, course display-name mapping và25 level length values](DISPLAY_UNITS.md), đã kiểm1.086 native fixtures. Quan hệ pathunits→displayed miles được ghi rõ là display calibration, chưa gọi là physical meters.
