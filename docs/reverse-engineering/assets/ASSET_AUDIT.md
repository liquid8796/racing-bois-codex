# Racing Bois — kiểm kê và reverse-engineering assets

Snapshot: 21/09/2026. Nguồn chỉ đọc: `C:\Users\Liquid\Downloads\Unity\racing_bois_mod`.

**Kết luận:** đã kiểm kê toàn bộ 374 file và khôi phục có kiểm tra toàn bộ bảng tài nguyên CRSR, 269 payload FAM, các bảng animation và toàn bộ sprite DAT. Chưa thể tuyên bố hiểu 100% ngữ nghĩa assets hoặc logic game. Không có căn cứ cho rằng đã lấy được mesh/rig 3D production từ bản gốc.

**Yêu cầu mới của người dùng là nguồn quyết định:** chỉ dùng bản gốc làm tham khảo để tạo assets mới từ đầu. Tất cả ảnh/sprite/payload giải mã trong thư mục này là tư liệu nghiên cứu, nằm ngoài Unity `Assets/`. Không đưa ảnh, audio, video, font hoặc sprite trích xuất vào sản phẩm phát hành.

## 1. Baseline dung lượng và tính toàn vẹn

| Nhóm thư mục | File | Byte |
|---|---:|---:|
| AUDIO | 104 | 157,289,554 |
| DATA | 22 | 17,043,230 |
| IMAGES | 146 | 7,876,082 |
| VIDEO | 61 | 318,223,916 |
| TEXT | 9 | 879,032 |
| SAVES | 14 | 2,240 |
| Root | 18 | 1,767,427 |
| **Tổng** | **374** | **503,081,481** |

Khoảng 479.78 MiB. Có 365 SHA256 khác nhau, 7 nhóm trùng byte với tổng 9 bản dư. AVI và audio chiếm phần lớn dung lượng; dung lượng này không phải chỉ tiêu chất lượng 3D hoặc dung lượng tải web.

Các bản trùng đáng chú ý: `SG_KICKS.RRA` = `SG_KICKS.WAV`; `START.AVI` = `START4.AVI`; `WIN.AVI` = `WIN1.AVI`; `MANOMANO.RRI` = `CREDITS.RRI`. Bốn file save không đuôi ở root giống nhau. Danh sách đầy đủ: [duplicates.json](duplicates.json).

[source_manifest.csv](source_manifest.csv) và [source_manifest.json](source_manifest.json) ghi mọi đường dẫn tương đối, byte, đuôi file, magic hex, định dạng nhận diện và SHA256. Bài kiểm tra cuối xác nhận cả tập đường dẫn lẫn SHA256 của 374 file nguồn không đổi. Không chạy chương trình nguồn.

## 2. Kết quả phục hồi theo lớp dữ liệu

| Lớp | Kết quả đã kiểm tra | Chưa được chứng minh |
|---|---|---|
| 119 `.RRI` | 119 JPEG/JFIF giải mã đầy đủ bằng Pillow; 118 file khác SHA256 | Không phải texture PBR/mesh |
| `IMAGE001.BMP` | Bitmap RGB 640×480 giải mã đầy đủ | Ngữ cảnh sử dụng runtime |
| 27 `.BOB` | 25 ảnh dựng được với dimensions từ native loader; 2 cloud còn chờ dimensions | Runtime crop/transparency/remap; cloud loader |
| 7 biker `.DAT` | 1,439 slot; 869 frame có pixel; 855 hash pixel khác nhau; parser đi đúng EOF cả 7 file | Nhãn action/timing và màu rider cuối sau remap |
| 13 `.RSC/.CAR/.CRS` | 429 entry, kiểm tra vùng dữ liệu và không chồng nhau | Ngữ nghĩa mọi field của SPEC/NOD/SGS/CANS/FORM |
| 269 `FAM` | 163 payload nén giải đúng kích thước, lượng byte input và CRC32; 106 payload rỗng không nén; cây offset hợp lệ 269/269 | Tất cả quan hệ object/biome/collision và giải mã render mọi leaf |
| 1,721 `RRAN` | Bảng RRFD/ANIM thống nhất, 7,632 frame record, 2,724 hash pixel chunk khác nhau | Chưa dựng toàn bộ frame RRPD/PDAT thành ảnh có palette đúng |
| 577 `CLGP` + TEMPLATE.MIP | 786 PDAT mip structures,4,750 mip level descriptor; TEMPLATE có8level, tất cả bounds/dimensions kiểm tra thành công | Chưa khẳng định orientation/filter/addressing runtime giống hệt |
| 87 WAVE | 72 effect + 15 file nhạc; RIFF hợp lệ, metadata codec PCM u8 | 15 file nhạc chỉ có 14 file khác byte; chưa gán mọi cue vào event |
| 61 AVI | Giải mã toàn bộ video và audio bằng ffmpeg, 61/61 không lỗi | Không đo chất lượng trải nghiệm hoặc lựa chọn clip runtime |
| 11 `.MID` | Thực chất RIFF/MIDS; tất cả block đi đúng EOF, 104,386 event record | Chưa render nhạc bằng đúng synth/sound bank của game |
| 6 `.SBK` | RIFF SoundFont 1.0; 32 sample record, 27 tên sample khác nhau | Không suy tên khác nhau thành sample âm thanh khác byte; chưa render bank |
| 4 font `.DLL` | TrueType, mỗi font 206 glyph; bảng offset và tên font đọc được | Font mới phải thay thế trong production |
| 5 language `.DLL` | Do audit logic xử lý: 6,832 string record, ENU 1,364 | Xem tài liệu logic cho ánh xạ string ID |

Tổng bytes FAM sau giải nén: **40,243,904**. Mọi phép đếm trên là lớp lưu trữ riêng, **không cộng chúng thành số model hoặc số assets độc lập**. Một animation có nhiều góc nhìn/frame; high/low resolution, shadow, mipmap và cùng nội dung lặp theo track không phải assets gameplay mới.

## 3. Định dạng đã reverse và bằng chứng byte

### CRSR / bảng tài nguyên

Magic ngoài `CRSR` là FourCC đảo byte của `RSRC`; bảng bắt đầu `LBTR` (`RTBL`). Header u32 little-endian tại `0x10` là offset bảng; tại `0x14` là kích thước vùng bảng. Bảng có số entry tại `table+8`, entry đầu ở `table+16`, stride 32 byte.

Entry: `fourcc[4], id:u32, offset:u32, size:u32, unknown[4]:u32`. Mọi `(offset,size)` phải nằm trong file, sau bảng và không chồng payload khác. Với snapshot hiện tại, BIKESPEC dùng version 1 / table offset 64, các archive còn lại version 2 / table offset 56.

| Resource type | Entry |
|---|---:|
| SPEC | 15 |
| FAM | 269 |
| ANIM | 58 |
| CANS | 34 |
| CEL | 42 |
| NOD | 5 |
| SGS | 5 |
| PAL | 1 |

[resource_entries.csv](resource_entries.csv) chứa mọi entry và hash payload. [bikespec_raw.json](bikespec_raw.json) giữ 15 SPEC × 89 signed dword = 356 byte/record, **không tự gán đơn vị vật lý** cho giá trị chưa truy loader. Loader native của SPEC đã được agent logic truy tại VA `0x405e30` và ứng dụng tại `0x405ea0`.

### FAM / PKWARE DCL

Header payload gồm bốn u32: `(raw_size, stored_size, crc32, compression_flag)`, sau đó `stored_size` byte. Flag 1 dùng PKWARE DCL. Flag 0 trong snapshot là payload rỗng 8 byte `[0,8]`; không diễn giải CRC zero của entry rỗng thành CRC chuẩn.

Ví dụ FAM ID 1 tại offset 8,688 của `FAMILIES.RSC`: stored 82,544 byte → raw 210,144 byte, CRC32 `1702d2dc` khớp. Bộ giải nén Python có giới hạn output, phát hiện input bị cắt hoặc back-reference sai. Thuật toán tham chiếu [Mark Adler blast trong zlib v1.3.1](https://github.com/madler/zlib/tree/v1.3.1/contrib/blast); source và license giữ tại thư mục tool.

Payload giải nén chứa cây `(count, relative_offsets[count])`; node rỗng 8 byte và các leaf có FourCC. Tất cả offset tăng, nằm đúng vùng cha. Đếm leaf: **577 CLGP, 1,663 RRAN, 163 CANS, 112 FORM, 420 EMPTY**. Đây là record có thể chứa biến thể/dùng lại, chưa phải 577 vật thể 3D hoặc 1,663 animation clip duy nhất. Bằng chứng từng ID: [families.json](families.json).

### RRAN / RRFD / pixel chunk

RRAN bắt đầu `NARR`, bốn offset ở +4 chỉ RRFD, ANIM, CCB, PLUT. RRFD bắt đầu `DFRR`; kích thước `8 + 28×n`. ANIM lưu cùng `n` tại +16. Mỗi frame có 7 u32 gồm vị trí descriptor, pixel chunk, map, hai field tọa độ thô và width/height. Pixel chunk được xác nhận có `RRPD` hoặc `PDAT`, size nằm trọn trong record.

Tất cả **1,721 RRAN / 7,632 frame record** qua được kiểm tra độc lập `n` giữa hai bảng và bounds. 1,663 RRAN nằm trong FAM; 58 nằm trong archive ngoài. [animations.json](animations.json) giữ tọa độ byte, width/height, hash pixel chunk của từng frame. Chưa gọi đây là ảnh đã render đúng màu.

PDAT mang marker `12345678` (`0x00bc614e`) của cấu trúc ảnh runtime. Toàn bộ577CLGP đã kiểm tra tới786PDAT có4,750mip descriptor; TEMPLATE.MIP thêm8level. Mỗi body khai báo width,height,count, bảng12byte/level, width mask và negative double stride. Width/height giảm theo level, tối thiểu1; offset và vùng pixel ứng viên đều nằm trong body. CLGP có cả nhánh bảng offset và nhánh offset PDAT trực tiếp; parser xử lý cả hai. [mip_structures.json](mip_structures.json) và [mip_summary.json](mip_summary.json) giữ kết quả không lỗi.

Thử nghiệm local dựng một mip từ FAM1 có ảnh nhìn thấy được, nhưng chưa chứng minh orientation/palette/sampling đúng cho toàn corpus. File `samples/family1_mip0_candidate.png` là **candidate nghiên cứu**, không phải kết quả production hoặc tiêu chí pass về fidelity.4,750mip không được tính là4,750texture khác nội dung.

### Biker DAT

Mỗi record: `width:u8, height:u8, pixel_indices[width×height]`. `(0,0)` là slot rỗng, vẫn tiêu thụ 2 byte. Parser độc lập đi đúng EOF; loader native tại VA `0x4436a0..0x44379c` đọc cùng cấu trúc, xác nhận thêm ngoài kiểm tra đoán format.

| File | Slot | Frame không rỗng |
|---|---:|---:|
| HIBOB.DAT | 326 | 186 |
| LOBOB.DAT | 326 | 186 |
| HISHADOW.DAT | 326 | 199 |
| LOSHADOW.DAT | 326 | 199 |
| LOCOP.DAT | 45 | 33 |
| HISHADOC.DAT | 45 | 33 |
| LOSHADOC.DAT | 45 | 33 |

[biker_frames.csv](biker_frames.csv) giữ toàn bộ slot. [Contact sheet](samples/biker_contact_sheet.png) chỉ minh họa 8 frame đầu không rỗng mỗi file, dùng `PALETTE.RAW` dạng RGBX. Nền xanh dương là palette index 0 đang hiển thị trong mẫu. Rider còn cần cơ chế thay màu/runtime remap; cop nhìn rõ nhưng không dùng làm chứng cứ rằng toàn bộ palette đã đúng.

### BOB / panorama / dashboard

Dimensions được truy từ loader native và đối chiếu hình đã dựng: horizon width 720 high / 360 low tại `0x44c440,0x44c453`; chiều cao lưu trữ bằng byte/width là 320/160. Runtime có thể crop height 297 ở nhánh high. Dashboard loader `0x44c710` gọi `0x44c5f0` với width640/320, maxheight122/61; chiều cao file RAT/SUPER119/60, SPORT121/61. Meter `0x44c5d0` là190×64 và95×32. Matte `0x44c87d` là640×480.

25/27 BOB đã dựng với width được xác nhận; [bob_images.json](bob_images.json) và [panorama contact sheet](samples/horizon_contact_sheet.png) giữ bằng chứng. BIGCLOUD/LILCLOUD vẫn chưa khóa dimensions từ loader.

Thứ tự **RGBX đã xác nhận bằng native code**: loader `0x448fe5` đọc1,024byte vào`0x4b8490`; screenshot writer `0x41e7c3..0x41e7f3` đổi rawbyte0→BMPbyte2, raw1→BMPbyte1, raw2→BMPbyte0. Runtime còn đặt RGB của palette index0 thành0 tại`0x448ff9..0x449005` và tạo palette nửa độ sáng tại`0x44900b..0x44904a`. Ảnh nghiên cứu giữ palettefile gốc nên index0 vẫn xanh; runtime black/transparency và rider remap cần áp riêng. Đây là lý do không coi ảnh xem tĩnh là bằng chứng hoàn thiện rendering.

### Media và font

61 AVI chứa **25,469 frame được khai báo**, tổng 1,697.933 giây; 46 clip 320×192, 15 bike showcase 320×172. Video codec Cinepak; 46 clip có IMA ADPCM theo metadata chi tiết. 61 file được giải mã hết cả video/audio không lỗi: [video_decode_validation.json](video_decode_validation.json). Có 59 file AVI khác SHA256. Header/ffprobe ghi25,469 frame; đếm độc lập RIFF `movi/00dc` cũng25,469 chunk video (24,235 chunk audio `01wb`), không chỉ dựa vào số file.

87 WAVE dài 3,537.733 giây tính cả bản SG_KICKS trùng; 72 effect PCM u8 11,025 Hz và 15 file nhạc PCM u8 22,050 Hz. Nhạc `.RRA` là WAVE tiêu chuẩn đổi đuôi, không phải mã hóa đặc biệt. [media_metadata.json](media_metadata.json) giữ stream metadata; [riff_chunks.json](riff_chunks.json) giữ đầy đủ cây chunk với offset/size.

MIDS là các block thời gian+buffer MIDI, không phải Standard MIDI `MThd`. [midi_streams.json](midi_streams.json) giữ division, flags và block; [sound_banks.json](sound_banks.json) giữ SoundFont 1.0 và sample names. Không dùng decoder SoundFont2 với giả định record 46 byte cho `shdr` v1 (snapshot này record 16 byte, sample names nằm trong `snam`).

Font bị đổi đuôi: Badloc Regular, Futura Condensed Bold, Futura Condensed Demi Regular, Futura Condensed Regular. [fonts.json](fonts.json) giữ bảng và metadata glyph.

## 4. Baseline nội dung để remake, không sao chép

| Đơn vị chức năng | Baseline nguồn | Điều kiện nội dung mới |
|---|---|---|
| Khu vực/course | 5 CRS: CANYN, CITY, HIWAY, MEDLY, NAPA; 5 CAR tương ứng | Ít nhất 5 bộ môi trường/track hoàn chỉnh; mapping tên hiển thị, cấp độ, độ dài và event phải chốt từ audit logic |
| Bike SKU | 15 SPEC, 3 nhóm RAT/SPORT/SUPER; mỗi nhóm 5 ảnh xe và 5 showcase clip | 15 thiết kế bike mới phân biệt được, đủ giá trị điều khiển/shop; ghi rõ phần nào chia chassis, phần nào khác silhoutte/material |
| Rider portraits | 8 tên × 3 trạng thái N/H/F = 24 ảnh; MANOMANO là bản trùng credits | 8 nhân vật mới, ít nhất 3 trạng thái biểu cảm/chân dung tương ứng mỗi nhân vật; không tính credits trùng thành nhân vật thứ 9 |
| Rider/cảnh sát chuyển động | 186 rider slot không rỗng ở mỗi Hi/Lo; 33 cop slot; shadow tương ứng | Rig và animation mới phủ toàn bộ **hành động/góc nhìn có nghĩa** sau mapping; không cần tạo 186 mesh hoặc 186 clip nếu một rig/clip phủ đúng |
| Cảnh quan/traffic/props | 163 FAM không rỗng, 577 CLGP và RRAN dùng lại; số concept duy nhất chưa chốt | Phải lập catalog nhìn được, nhóm concept và source→new mapping trước khi khóa số lượng prefab; không coi 163 FAM là 163 model |
| Horizon và HUD | 27 BOB gồm 10 horizon Hi/Lo, 12 dashboard trong 3 nhóm, 5 file root;25 ảnh đã dựng | 5 bộ cảnh xa mới, HUD/dashboard mới phủ cấu hình tương ứng; Hi/Lo là chất lượng cùng nội dung |
| Scene UI 2D | 119 JPEG (118 unique), 1 BMP; gồm 29 results, 15 postcards, 18 showroom, 6 restroom, 3 street và ảnh khác | UI/art mới phủ từng mục đích và trạng thái; giữ bảng mapping có lý do gộp/thay thế, không copy/re-encode ảnh gốc |
| Audio effect | 72 file effect không trùng byte | 72 event/cue mục tiêu cần mapping; âm thanh mới thu/tổng hợp/sản xuất, có biến thể để tránh lặp |
| Music | 14 bản PCM khác byte; 11 MIDS có cặp nhạc/arrangement | Chốt danh sách composition khác nhau; nhạc mới cùng vai trò/nhịp cảm xúc, không dùng melody/master gốc |
| Cinematic/showcase | 59 AVI khác byte: 15 showcase, còn lại event/story/end state | Nội dung diễn hoạt/render mới phủ event và showcase; không dùng đoạn quay gốc làm video release |
| Typography/localization | 4 font và 5 language bundles | Font có nguồn production hợp lệ và hệ typography mới; viết lại copy theo hệ thế giới Racing Bois |

Danh mục máy đọc để phase tiếp theo gán chủ sở hữu: [replacement_baseline.csv](replacement_baseline.csv). Đối với FAM, [family_replacement_register.csv](family_replacement_register.csv) là 163 hàng đầu việc phân loại concept, **không phải yêu cầu 163 model**.

Để đạt “khối lượng assets ít nhất bằng game gốc”, acceptance nên yêu cầu phủ 100% đơn vị nội dung có nghĩa và các trạng thái đã xác minh, có chất lượng/tính đa dạng tương đương hoặc cao hơn. Không tăng dung lượng bằng file trùng, texture phóng lớn, nhiều LOD hoặc mip để đạt 503 MB. Nếu muốn giữ 503 MB như điều kiện phụ, chỉ áp cho tổng thư viện nguồn production do nhóm tạo mới; lượng tải web vẫn chia theo track/chế độ.

Mỗi asset mới cần `asset_id`, reference IDs, mô tả thiết kế mới, file nguồn `.blend`/texture source/audio project, tác giả/tool, material set, prefab GUID, thông số chất lượng và ảnh kiểm duyệt. Gate SHA256 phát hiện copy nguyên byte là hữu ích nhưng **hash khác không chứng minh tạo mới**: crop, recolor, resize, re-encode nguồn vẫn không đạt yêu cầu. Cần lịch sử file nguồn và kiểm duyệt thiết kế/mapping. Không đặt file trích xuất trong production source hoặc Unity `Assets/`.

## 5. Phần còn thiếu và gate trước phase sản xuất

1. **Semantic catalog:** render contact sheet cho toàn CLGP/RRPD/PDAT/FORM và ánh xạ FAM IDs sang prop/traffic/biome. Hiện mới khôi phục byte/container/frame table, chưa chốt số concept mới cần xây.
2. **BOB/mipmap/palette:** còn2cloud dimensions, transparencies, rider recolor, mip stride và orientation; render so sánh với footage.25BOB đã xác nhận dimensions không có nghĩa đã khôi phục đầy đủ crop/remap runtime; DAT frame hình dạng đúng không đồng nghĩa màu đúng.
3. **Animation state coverage:** nối SPEC/action/state/weapon/contact sang DAT/RRAN frame IDs, timing, left/right và hit windows. Không suy danh sách clip từ số sprite slot.
4. **Course geometry/data:** NOD/SGS/FORM/CANS còn cần field schema và mapping với track/event/collision/LOD. Không tạo cảnh đường đơn giản rồi tuyên bố đủ 5 course gốc.
5. **Audio event mapping:** nối từng cue vào engine state, khoảng cách, mix, loop và pitch; MIDS/SBK render reference nếu cần so sánh nhịp.
6. **Visual fidelity:** hiện chưa đánh giá render Unity, Blender asset, shader, memory/FPS hoặc performance WebGL. Không có prefab/game build nào đạt checklist production chỉ vì giải mã nguồn thành công.

## 6. Đầu vào pipeline Blender → Unity cho assets mới

- Dùng mét; quy ước pivot theo chức năng. Root prefab `(0,0,0)`, scale `(1,1,1)`, trục forward thống nhất; export/import phải có kiểm tra thực tế.
- Mesh mới có naming, normals/tangents đúng, không mặt ngược/vertex thừa; UV có overlap được ghi chủ đích. LOD và budget phụ thuộc độ xuất hiện/gameplay distance, không lấy polycount bằng cảm tính.
- Material đúng pipeline dự án sẽ chọn; BaseColor/Normal/metallic-roughness hoặc mask theo shader. Reuse material hợp lý, không duplicate không cần thiết. Compression và kích thước texture theo profile Web.
- Collider ưu tiên primitive, chỉ dùng mesh khi có lý do; không collider thừa/chồng không chủ đích. Tĩnh thì static flags; baked lighting cần UV2 hợp lệ và visual QA.
- Rig/animation mới cho rider, combat, ragdoll/recovery và bike; loop/root motion rõ, avatar mapping đúng. Bản gốc chứa sprite không cung cấp miễn phí rig/animation 3D tương đương.
- Prefab không missing script/reference; drag vào scene chạy được, console sạch lỗi/cảnh báo liên quan asset, nhìn đúng khoảng cách gameplay. Đo FPS, memory, batch/draw call và tải resource trên máy/browser target trước acceptance.
- Checklist đầy đủ cấp dự án được lưu ở tài liệu yêu cầu do agent chính quản lý; các gợi ý ở đây không thay thế checklist người dùng.

## 7. Cách tái lập và phạm vi PASS

Từ root dự án:

```powershell
python tools/reverse-engineering/assets/audit_assets.py
python tools/reverse-engineering/assets/inspect_internals.py
python tools/reverse-engineering/assets/decode_bob.py
python tools/reverse-engineering/assets/inspect_mips.py
python tools/reverse-engineering/assets/validate_decoders.py
```

Kết quả: [summary.json](summary.json), [internals_summary.json](internals_summary.json), [validation.json](validation.json). Không lỗi parser trên snapshot. Bộ DCL qua vector chuẩn upstream, 8 prefix cắt ngắn bị từ chối, giới hạn output hoạt động; CRSR/DAT lỗi bounds bị từ chối. 61 AVI giải mã hết và 374 SHA256 nguồn giữ nguyên.

**PASS này chỉ cho kiểm kê/format/recovery nêu trên; không phải PASS cho logic game 100%, parity gameplay, asset remake hoàn thành hoặc chất lượng Unity production.**
