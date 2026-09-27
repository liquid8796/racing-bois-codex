# P08 — checkpoint 2026-09-27

P08 đang triển khai; chưa nghiệm thu toàn bộ content hoặc phát hành bản Windows. Client chính là **Windows 10/11 x64**, Web bổ sung sau. Backend online và dữ liệu đặt trên OCI; staging backend đã có receipt P09, nhưng nội dung P08 hoàn chỉnh và kết nối gameplay nhiều vùng chưa được nghiệm thu.

**Cập nhật sau khi khôi phục session `racing-bois-2`:** [receipt OCI f](p09/releases/f/deployment-after-soak.json) xác nhận multiplayer protocol 6; ghi nhận cũ về e/protocol 5 đã được thay thế. [Import Unity lúc 13:48 Bangkok](p08/golden/unity/import-6feb434df4ad455f82b3b81efc7ab3f8.json) PASS kỹ thuật cho Apex R4, Ash V6 và menu environment V1. Garage V7 có bake hai lightmap/60 renderer; [receipt](p08/golden/unity/garage-bake-latest.json) vẫn ghi `visualAccepted=false`. [Ash V7](p08/golden/ash/v7/delivery.json) là delivery staging, chưa import native; [Spark V1](p08/golden/spark/v1/DESIGN_REVIEW.md) đã có source assembled nhưng chưa hoàn tất export/descriptor. Các mẫu vẫn khác concept và masks giữ **1/1/1**.

36 ảnh Windows DX11 của Apex R2/Ash V3 được giữ như bằng chứng native lịch sử, không xác nhận các mẫu mới hoặc bản game phát hành. [Regression mới](p10/regression/20260927T105143Z/receipt.json) PASS 261 nhóm/17 suite và [soak socket tám giờ](p10/network/20260927T003037Z/run.json) PASS theo phạm vi; chúng không nghiệm thu art/UI, smoothness hoặc performance Unity player. Tiến độ hiện tại: [P08–P10](P08_P10_RUN.md), [bằng chứng Unity/native](p08/golden/unity/README.md).

**Review chất lượng mới ngày2026-09-26:** người dùng yêu cầu rà soát trước khi tiếp tục. [Báo cáo tổng hợp](p08/review-2026-09-26/REVIEW.md) kết luận concept cần sửa có chọn lọc, hero3D/UI chưa đạt chuẩn desktop; một số receipt cũ không còn khớp file hiện tại. Tạm dừng nhân rộng công thức art cũ, chốt một bộ mẫu đạt visual/technical gates trước khi thay roster. Các preflightPASS phía dưới chỉ có hiệu lực theo phạm vi ghi trong receipt, không phải nghiệm thu art/UI tổng thể.

## Baseline 2026-09-26 — bằng chứng lịch sử theo phạm vi

Các số kiểm tra và trạng thái build dưới đây thuộc checkpoint 2026-09-26. Dùng cập nhật phía trên và receipt mới cho trạng thái hiện tại; không suy tính mới từ một PASS lịch sử.

- Năm concept UI desktop đã được tạo/xem trước khi triển khai menu, garage, lobby, HUD và gallery. UI dùng controls tương tác và dữ liệu catalog/profile thật. Preflight xác minh 92 tên UXML, 94 typed bindings và ba nhánh managed Windows/Editor/Web; chưa thay thế review hình ảnh/player. Xem [UI implementation](p08/ui/DESKTOP_UI_IMPLEMENTATION.md).
- Native config, installed content, platform fences, audio streaming và preview actor thực đã được nối với bootstrap/UI. Chín kiểm tra config/content/music và năm kiểm tra native transport qua loopback đều PASS. Binary WebSocket frame được từ chối cho giao thức JSON text. Xem [native runtime audit](p08/desktop/native-runtime-audit.md).
- Build recipe Windows release Mono/DX11 có source fingerprint, full-file hash và receipt cho thao tác thật; 14 verifier tests PASS. Không có desktop manifest/player hoàn chỉnh tại checkpoint này. Xem [desktop handoff](p08/desktop/HANDOFF.md).
- Unity Editor đã chuyển target thật từ WebGL sang StandaloneWindows64. Sau reload không có error; có một cảnh báo CS0618 của package Unity MCP ngoài source game, không gắn nhãn console hoàn toàn sạch.
- Concept roster đã có 14 xe mới và 8 nhân vật, cùng manifest provenance; bike00 dùng thiết kế starter P06. Asset 3D/portraits đang được tác giả hóa qua Blender MCP, kiểm source hình học và review render trước khi import/accept.
- Media gốc mới gồm 72 SFX, 14 composition dài và 11 score ngắn; 59 định nghĩa cinematic realtime. Kiểm toán file/media không chứng minh toàn bộ playback, chất lượng sáng tạo hoặc trải nghiệm đã đạt.

## Các bước còn phải thực hiện

1. Hoàn thiện/refine/export và review roster xe, 8 rider, 24 portrait states; freeze publication rồi chạy P08ArtBuilder.Setup/Validate trong Unity.
2. Hoàn thành mapping semantic cho traffic/pedestrian/scenery còn thiếu theo reference ledger; không đếm LOD/file duplicate hoặc SKU như asset độc lập.
3. Chạy scene/prefab/rig/clip/cinematic QA trong Unity; cập nhật production masks chỉ sau nghiệm thu tương ứng, rồi kiểm campaign/content gameplay.
4. Build packs Editor và StandaloneWindows64; chuẩn bị/cố định source, build player Windows vào thư mục mới và audit installed distribution bằng hash thực.
5. Kiểm player thật: UI/framing/focus/input/display modes, offline practice, native audio, LAN/reconnect, memory/frame time và soak. LAN nhiều máy/WAN nhiều vùng vẫn cần thiết bị/kết nối thật; người dùng hiện có một PC.
6. Tiếp tục các gate P09 còn mở từ receipt staging f: game client nhiều vùng, nội dung P08 được duyệt và quyết định vận hành production. HTTPS/WSS, private DB và các drill đã chạy có bằng chứng riêng; không suy nghiệm thu toàn P09 từ một phòng synthetic.

ContentParityLedger vẫn có dòng partial/pending; chưa đạt full mapping. P01 reverse, P05 physical networking và P06 human/performance gates còn mở theo hồ sơ trước. Không tuyên bố đạt 100% logic/content hoặc chất lượng tối đa từ preflight.

## Checklist tiếp tục session

1. Sửa binding/restoration của build pose-envelope đang thất bại, rồi thu và xem ảnh native so sánh; chưa tích hợp smoothing staging vào production.
2. Publish Ash V7 vào đường dẫn review mới, kiểm 13 clip/bind rest/loop/contact/amber glass; xử lý các sai khác được ghi trong [review 17 pose](p08/golden/ash/v7/fullbody-visual-review.md).
3. Hoàn tất geometry/UV/export/FBX roundtrip của Spark V1; đối chiếu render với đúng concept/hash trước native review.
4. Tiếp tục khớp UI, hero và môi trường với reference; chỉ mở masks sau production QA tương ứng. Root giữ quyền thao tác Unity; agent chỉ dùng Blender instance được giao.
