# Racing Bois — Kết quả reverse-engineering và phạm vi đã xác minh

Ngày: 2026-09-21, Asia/Bangkok. Nguồn: `C:\Users\Liquid\Downloads\Unity\racing_bois_mod`. Tham chiếu gameplay: video local Road Rash PC dài 02:34:39.716.

## Kết luận

Đã thực hiện reverse tĩnh có bằng chứng ở mức **file/container/asset records, mã máy gameplay, save, localization và network**, đồng thời khảo sát video toàn timeline bằng sampling và các chuỗi hành vi dày hơn. Bộ công cụ, dữ liệu và kế hoạch đã lưu trong project.

**Chưa đạt 100% logic hoặc full asset-semantic decode.** Đã kiểm kê toàn bộ file và kiểm tra nhiều parser, nhưng các phần movement integrator, AI/police hoàn chỉnh, track semantics, palette/pixel codecs và timing còn cần reverse/trace. Danh sách cụ thể ở cuối báo cáo. Không gán một phần trăm parity chung từ các bộ đếm.

Theo cập nhật của người dùng: **assets gốc chỉ là tham chiếu; toàn bộ assets production của Racing Bois sẽ làm mới từ đầu**. Dữ liệu trích xuất ở `docs/reverse-engineering/` phục vụ nghiên cứu, không đưa vào Unity Assets hoặc build game. Mục tiêu khối lượng nội dung ít nhất ngang nguồn vẫn giữ nguyên, đo qua mapping sang assets mới.

## 1. Snapshot nguồn

| Nhóm | File | Bytes |
|---|---:|---:|
| AUDIO | 104 | 157,289,554 |
| DATA | 22 | 17,043,230 |
| IMAGES | 146 | 7,876,082 |
| SAVES | 14 | 2,240 |
| TEXT | 9 | 879,032 |
| VIDEO | 61 | 318,223,916 |
| Root | 18 | 1,767,427 |
| **Tổng** | **374** | **503,081,481** |

365 SHA-256 khác nhau, 7 nhóm duplicate. Tổng khoảng 479.78 MiB. Manifest giữ **tất cả 374 file**, không bỏ file trùng. Đây là kích thước bộ game được cung cấp, không phải chỉ số chất lượng hoặc ngân sách tải game web.

Executable chính là PE32 x86 native, 541,184 bytes, entry `0x4583c0`, SHA-256 `66ab853c5b7b73b82a7c22a0478f5ba5b1066ed27028ef96449f5fe36a6101c5`. Có DirectDraw/DirectSound/WinSock/TAPI; đây không phải Unity build và không có project C#/prefab/scene để khôi phục trực tiếp.

Bằng chứng: [source_manifest.csv](reverse-engineering/assets/source_manifest.csv), [summary.json](reverse-engineering/assets/summary.json), [PE inventory](reverse-engineering/logic/pe_inventory.json).

## 2. Assets và cấu trúc dữ liệu

| Miền | Kết quả đã kiểm chứng | Không được suy ra từ con số |
|---|---|---|
| CRSR | 13 archives, 429 entries; offset/size không chồng và trong biên | Không đồng nghĩa 429 asset production độc lập |
| FAM | 269 entries; 163 compressed giải nén đúng length/CRC32, 106 raw empty; cây entry đọc được | Nội dung leaf/pixel/anchor chưa được hiểu đầy đủ |
| CLGP/mips | 577 CLGP đọc được thành 786 PDAT mip structures, 4,750 level descriptors có kiểm tra biên; TEMPLATE.MIP có 8 levels | Cấu trúc hợp lệ chưa chứng minh toàn bộ pixel orientation/palette đúng runtime |
| Animation tables | 1,721 records, 7,632 RRFD frame records, 2,724 pixel-chunk hashes khác nhau | Không phải 2,724 model 3D hoặc clip độc lập |
| Biker DAT | 1,439 slots, 869 không rỗng, 855 hashes pixel khác nhau; width/height/pixel stream đi hết file | Hi/Lo/Shadow và pose lặp không được cộng thành nhân vật riêng |
| Ảnh tiêu chuẩn | 119 `.RRI` là JPEG và 1 BMP, 120 ảnh decode đầy đủ | Không chứng minh ảnh headerless BOB đều đúng màu/alpha |
| BOB | 25/27 ảnh dựng được với dimensions đối chiếu native loader | 2 cloud còn thiếu dimensions; crop/transparency/remap vẫn cần trace |
| Video trong mod | 61 AVI, 25,469 frames theo metadata khớp RIFF video-chunk count độc lập, ~1,697.93 giây; toàn bộ streams decode bằng ffmpeg thành công | Chưa phân loại hết trigger/nội dung cinematic |
| WAV/RRA | 87 RIFF/WAVE, ~3,537.73 giây tổng duration | Duration không tự chứng minh mix/loop/triggers đúng |
| MIDI/SoundFont | 11 RIFF/MIDS, 104,386 event records; 6 banks, 32 sample records/27 tên khác nhau | Chưa tái tạo toàn bộ playback/patch mapping |
| Font | 4 file mang đuôi DLL thực ra TrueType | Không đưa font gốc vào production |

Nguồn có 5 course files, bảng 15 bike SPEC và 8 bộ portrait nhân vật. Đây là baseline nội dung để làm lại; số lượng model/rig/từng props mới được chốt qua semantic catalog. Các horizon BOB có stride Hi 720/Lo 360 được đối chiếu với loader code; output nghiên cứu dùng palette mẫu chưa phải bằng chứng color-remapping hoàn chỉnh.

Chi tiết parser/layout/offset và các giới hạn: [ASSET_AUDIT.md](reverse-engineering/assets/ASSET_AUDIT.md), [resource entries](reverse-engineering/assets/resource_entries.csv), [internal counters](reverse-engineering/assets/internals_summary.json), [parser/media validation](reverse-engineering/assets/validation.json).

## 3. Logic có bằng chứng mã máy

**39 vùng mã** được tách kèm VA, file offset và hash. Tên hàm do người phân tích đặt; có vùng chỉ là slice, không khẳng định đã phục hồi hết toàn hàm/callers. Full linear disassembly được giữ để nghiên cứu, nhưng jump table/data có thể bị hiểu thành instruction; kết luận dưới đây dùng vùng đã kiểm tra.

| Hệ thống | Kết quả | Evidence |
|---|---|---|
| Load xe | SPEC IDs 1..15, record 356 bytes | `0x405e30`, container BIKESPEC.RSC |
| Giá/đổi xe | Trade-in = floor(giá xe đang có/2); cash mới = cash + trade − giá xe mua; kiểm đủ tiền | Bảng `0x468fc0`, routine `0x42161c..0x421694` |
| Repair/fine | Repair floor(giá/10); nhánh fine 400×(levelIndex+1) | `0x4214e0..0x421595`; còn điều kiện caller/event |
| Campaign | Qualification mask `0x1f`, level index 0..4; qualify bits theo course | `0x41f6d0..0x41f70a`, `0x449186` |
| Reward | Bảng 14 vị trí bắt đầu 1000/750/500…, nhân(level+1) trong nhánh nhận thưởng | `0x46ab48`, `0x421365`; chưa đóng toàn bộ eligibility |
| Combat reach | Kiểm đúng phía và 3 delta vị trí; phạm vi thay theo weapon ID, so sánh `<` | `0x409c10`; đơn vị/axis semantic chưa khóa |
| Damage | Q8 strength ratio, clamp nửa base; multipliers `[256,320,384,64]`; các pool trừ/clamp riêng | `0x409ad0`, `0x4050c0`, `0x4051e0` |
| Lấy vũ khí | Nhánh transfer từ target sang attacker, zero target, timestamp và random gate | `0x4097c0`; chưa xác định đơn vị clock |
| Random/AI | LCG 214013×state+2531011, một số gate attack theo character/level | `0x455eb0`, `0x409460`; chưa có toàn AI FSM |
| Save | 160 bytes, magic 0xcafedead, checksum phục hồi và kiểm đúng 14/14 RRS | `0x42efc0`, `0x42f000`, `0x42f110` |
| Network cũ | Native datagram/stream/IPX/TAPI; pack state 24 bytes có player/type/tick/fields | `0x43c7e0`, `0x441c90`, `0x4428a0` |
| UI/text | 6,832 RT_STRING entries trong 5 locale DLLs; English 1,364 | Resource parser với ID/ngôn ngữ cụ thể |

Combat multiplier số đã rõ không đồng nghĩa mọi tên punch/club/chain/kick đã map chắc chắn. 300 clock units chưa được gọi là 300 ms hay 5 giây. SPEC 89 int32 chưa được tự gán thành horsepower/grip/gear ratios. Toàn bộ phần không chắc chắn đã được đánh dấu trong [LOGIC_AUDIT.md](reverse-engineering/logic/LOGIC_AUDIT.md).

Native multiplayer của nguồn **có thật**, nhưng không chứng minh có authoritative backend/account/lobby cloud phù hợp web. Unity Web cần thiết kế transport và backend mới. Không tái sử dụng giao thức native rồi coi như giải quyết Internet toàn cầu.

## 4. Gameplay video đã khảo sát

Video 640×480/30 fps, 974,063,206 bytes, duration 9,279.716 giây. Đã xem 312 ảnh ở 301 timestamp khác nhau, 27 contact sheets: lấy mẫu toàn timeline, rồi xem chuỗi dày cho menu/shop/combat/crash/finish/level-up. Chưa nghe/đánh giá audio và chưa xem liên tục từng frame.

- **30:59–31:09:** người/xe tách khi ngã, tumble, đứng dậy, chạy về xe, lên xe; vị trí đua tụt từ 8 xuống 10. Recovery là gameplay có chi phí thời gian/quãng đường.
- **35:00–35:02:** đánh cận chiến khi chạy cạnh nhau; lái và combat diễn ra đồng thời.
- **19:45:** thông báo qualify các track để lên level; khớp mask/level logic trong binary.
- **04:24:** top 3 hiển thị 1000/750/500; cash người chơi tăng 400→1400.
- **59:40–01:00:05:** cash+trade 19527 trừ xe 18999 còn 528; khớp nguyên tắc giao dịch.
- Thấy 5 vùng đua, menu 5 levels, 8 nhân vật và 3 nhóm xe×5 lựa chọn. Đây là observed content, không phải counts mesh/rig.

Chi tiết 19 evidence IDs, timestamps và hạn chế: [GAMEPLAY_REFERENCE.md](reverse-engineering/video/GAMEPLAY_REFERENCE.md). Ví dụ trực quan: [chuỗi crash/recovery](reverse-engineering/video/focused/contact_06.jpg), [combat](reverse-engineering/video/focused/contact_07.jpg).

## 5. Toolchain và yêu cầu mới

Unity MCP đã phản hồi đúng instance của project Unity 6000.5.7f1. Project hiện có camera/đèn mặc định, chưa có game. Blender 5.2 có trên máy nhưng chưa có Blender MCP callable/connection được xác minh. Không tạo assets hoặc sửa scene trong đợt này. [Chi tiết môi trường](reverse-engineering/ENVIRONMENT_AUDIT.md)

Đã ghi rõ các quyết định của người dùng:

- PC/laptop browser trước.
- LAN tự chơi khi mất Internet: host package tự chứa runtime + client + assets + local data.
- Dữ liệu online trên OCI; dữ liệu LAN offline riêng, không tự nhập currency vào online economy.
- Toàn bộ assets làm mới từ đầu dựa trên tham chiếu.
- UI/UX đẹp, mượt, chuyên nghiệp, thân thiện và dễ sử dụng.
- Code có kiến trúc/pattern phù hợp, dễ đọc, bảo trì và mở rộng.

## 6. Gap register — công việc còn lại để tiến tới đầy đủ

| ID | Gap | Ảnh hưởng | Cách đóng / phase |
|---|---|---|---|
| R01 | Movement timestep, steering/grip/gear/brake, gravity/collision chưa đầy đủ | Chưa thể chứng nhận cảm giác lái giống nguồn | Dataflow + dynamic input/state traces, P01/P03 |
| R02 | Track geometry/placement semantic, scale và units còn thiếu | Chưa thể tái dựng course behavior chính xác | Complete CRS/CAR mapping + sample reconstruction, P01 |
| R03 | Sprite codecs/palette remapping/alpha/timing/anchors chưa toàn bộ | Chưa có đủ thông tin animation/VFX reference | Decode/visual compare mọi loại record cần thiết, P01 |
| R04 | Combat ID/clock/animation hit windows, fall/recovery chưa đóng | Damage math có nhưng toàn gameplay chưa parity | Trace controlled hits/crashes + state matrix, P01/P04 |
| R05 | AI/police/traffic/pedestrian/difficulty FSM còn thiếu | Thiếu full race behavior | Call graph + tình huống đo có kiểm soát, P01/P04 |
| R06 | Reward eligibility/qualification/full save-tail meanings | Nguy cơ sai tiến trình và save | Controlled save diffs + result branches, P01/P07 |
| R07 | Toàn protocol cũ và authority chưa reverse hết | Không coi network native là web backend sẵn có | Archive nghiên cứu, protocol mới kiểm chứng độc lập P02/P05 |
| R08 | Audio mix/trigger/MIDI instrument mapping, media trigger catalog | Thiếu baseline nội dung nghe/transition | Playback/trigger catalogue tham chiếu, rồi làm mới P01/P06/P08 |
| R09 | Không có original source symbols/recursive CFG đầy đủ/dynamic coverage | Không được tuyên bố 100% chương trình | Disassembler project + coverage/evidence registry, P01 |
| R10 | Chưa có binary bản PC chưa mod để so sánh trực tiếp | Không biết mọi khác biệt mod ↔ game PC trong video | Ghi difference ledger giữa nguồn cung cấp và video; chỉ dùng binary reference nếu có nguồn hợp lệ, P01 |
| T01 | Blender MCP chưa xác minh | Chưa đạt pipeline người dùng yêu cầu | Connect và asset round-trip, P02 |
| T02 | OCI target/capacity/region/domain chưa xác định | Chưa có deployment/capacity thực | Preflight chính xác, P02/P09 |
| Q01 | Chưa có Unity gameplay build/art/UX production | Chưa có FPS/quality hoặc online product thực | P03–P10 có demo và gate mỗi phase |

## 7. Thứ tự triển khai

Kế hoạch đầy đủ tại [PHASE_PLAN.md](PHASE_PLAN.md): P00 audit → P01 khép reverse gaps → P02 foundation/MCP/transport spike → P03 driving → P04 combat/AI → P05 online+LAN → P06 polished vertical slice → P07 economy/persistence → P08 full content → P09 OCI/global validation → P10 release QA.

Yêu cầu/checklist asset: [REQUIREMENTS.md](REQUIREMENTS.md). Kiến trúc: [TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md). UI/UX: [UI_UX_DIRECTION.md](UI_UX_DIRECTION.md). Chuẩn code: [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md).

Bộ kiểm tra tổng hợp chạy bằng `tools\reverse-engineering\verify-audit.bat`, ghi [verification-summary.json](reverse-engineering/verification-summary.json). PASS của kiểm tra hồ sơ chỉ chứng minh integrity và consistency của evidence đã liệt kê, không chứng minh game mới đã chạy hay reverse đạt 100%.
