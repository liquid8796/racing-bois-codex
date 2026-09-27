# Racing Bois — Review concept, UI và assets 3D

Ngày review: 2026-09-26. Target: Windows 10/11 desktop, Web về sau.

## Kết luận

**Chưa đạt chuẩn chất lượng sản phẩm mà người dùng yêu cầu.** Concept có nhiều hướng thiết kế hữu ích, nhưng model 3D và UI hiện tại chưa thực hiện được chất lượng đó. Những lần PASS trước chủ yếu xác nhận một phần geometry, mã hoặc cấu trúc; không thể dùng chúng để kết luận hình ảnh đã đẹp, bám concept hay toàn bộ asset đã production-ready. Một số receipt còn không khớp revision file hiện tại.

Đây là review trước khi thay thế. Trong lượt này không xóa, tạo lại hoặc sửa production art/UI. Unity chỉ được chạy để quan sát presentation rồi đã dừng. Dữ liệu tài khoản/backend không bị thay đổi. Source Club có thay đổi riêng của người dùng được bảo toàn.

## Phạm vi bằng chứng

- Xem trực tiếp toàn bộ **42 ảnh concept**:31 P08 và11 ảnh tiền nhiệm. [Review từng ảnh](concept-review.md), [coverage và hashes](concept-coverage.json).
- Đọc manifests, recipes, importers, prefabs và kiểm UV từ bytes của **36 FBX P08**. [Review kỹ thuật](3d-technical-review.md), [snapshot](technical-current-snapshot.json).
- So sánh render 3D đã lưu với concept và các assets P06/P04 được reuse. [Review hình ảnh3D](3d-visual-review.md).
- Xem năm concept UI; capture Unity main, settings, gallery, career disconnected và error/loading. [Review runtime](ui-runtime-review.md), [observations](ui-observations.json), [source/capture hashes](ui-source-snapshot.json).

Studio renders không thay thế Unity native player; ảnh concept không chứng minh motion/gameplay/performance. Viewport UI thực đã review là1105 × 506 trong Editor; chưa chạy đủ ma trận Windows hoặc lobby nhiều người.

## Quyết định giữ / sửa / dựng lại

| Nhóm | Quyết định | Lý do chính |
|---|---|---|
| Concept xe và rider | Giữ hướng tốt, sửa sheet mâu thuẫn | Jackal/Ember/Specter/patrol thay số hoặc vị trí ống xả giữa các góc; Havoc thiếu gương ở một số góc; Sol chưa định nghĩa biến thể mũ. Kích thước sinh trong ảnh không phải số đo chuẩn. |
| Concept môi trường | Giữ làm mood/reference, bổ sung bản dựng kit | Có palette và vai trò props, chưa đủ mặt cắt, dimensions, module joins, near/far treatment để dựng scene nhất quán. |
| Concept UI | Làm bản v2 có dữ liệu/trạng thái thật | Cả năm có chữ, stats/catalog hoặc trạng thái tự bịa; HUD mô tả sai Q/E; garage thumbnail sai kiểu xe. Gallery cần tạo lại hero vì có chữYAMAHA và actors không thuộc roster. |
| Bike 3D P08 hiện có | Dựng lại phần hình khối chính và vật liệu của hero models | Nhiều xe dùng chung stance/khung/fork/engine/wheels quá giống nhau; faired sports vẫn có dáng roadster dựng đứng. Fairing/tank/lamp/saddle đơn giản, shading nhựa/phẳng, thiếu cấu trúc bám concept. Đổi màu hoặc thêm polygon không giải quyết được vấn đề này. |
| Rider 3D | Dựng lại mesh/garments theo một mẫu chuẩn; cân nhắc giữ rig/clip làm nền | Rider P06 có chi và joints tách khúc, thân/helmet/boots giống hình khối lắp ghép, chưa đạt phong cách grounded của concept. Tám rider P08 mới chưa xuất thành FBX; không có24 portraits hoàn thiện để nghiệm thu. |
| Environment/props | Sửa có chọn lọc, giữ geometry cơ bản phù hợp vật thể xa | Kiến trúc còn dạng hộp, cửa/kính phẳng; cây/bụi/hay/rock thiếu cấu trúc và chất liệu. Hero foliage, cliff/roadside gần camera cần làm lại; poles/fences/road furniture có thể giữ nền và nâng material/detail theo khoảng cách thật. |
| UI runtime | Thiết kế lại presentation và skin components; giữ application logic | Menu hẹp/scroll, default white scrollbars/dropdown, gallery chưa có stage thuyết phục và localization chưa nhất quán. Cần giải quyết responsive theo pixel output, focus ownership và state coverage. |
| Code/pipeline | Giữ phần đúng; sửa cách ràng buộc nghiệm thu | Semantic IDs, simulation/backend authority, sessions/read models/intents, URP/LOD/importer infrastructure hữu ích. Audit phải bám hash của chính revision được kiểm và có visual/player gates. |

Phân loại concept 42 ảnh: **22 giữ hướng,11 sửa,8 chỉ tham khảo,1 tạo lại phần hình**. Đây là quyết định về ảnh concept, không phải tỷ lệ đạt của game.

## Ba vấn đề cần xử lý trước

1. **Khoảng cách concept → model quá lớn.** Apex là ví dụ rõ: concept có thân xe thấp, fairing ôm khung, intake/lamp và đuôi có cấu trúc; render hiện tại có thân cao/hẹp, gương tròn dựng đứng, mũi đèn đơn giản và fairing như tấm vỏ. Cần thay cách xây hình khối và vật liệu, không tiếp tục nhân rộng recipe hiện tại.
2. **Nghiệm thu kỹ thuật chưa gắn với chất lượng và revision.** Unity receipt chỉ29 IDs cũ trong khi có36 exports; sáu Ridge assets lệch source/FBX hashes. Fir hiện10.476 triangles LOD0, manifest4.202. Standalone BC7/BC5 mới nằm trong builder, chưa áp dụng lên metadata hiện tại. UV có channel/nonoverlap cục bộ chưa chứng minh chi tiết ở garage/portrait.
3. **UI nhìn đẹp trong concept nhưng chưa thành trải nghiệm thật.** Nền/model thực chưa đạt; hệ controls còn lẫn skin mặc định, chưa đủ state/resolution/input QA. Runtime smoke không thay cho Windows player.

## Trình tự thay thế rồi tiếp tục P08

1. Giữ nguyên snapshot hiện tại và review làm mốc; đánh dấu bản cũ superseded khi có replacement. Không xóa `.meta`/GUID hoặc source đang được scene/prefab tham chiếu để tránh đứt references. Club riêng của người dùng không nằm trong lệnh dọn tự động.
2. Chốt reference v2 có silhouette/dimensions/assembly/data thật. Tạo concept 2D mới hoặc chỉnh concept bị lỗi **trước** khi dựng 3D/UI mới; ghi provider/model provenance đúng mức tool cung cấp.
3. Làm một bộ mẫu: **Apex + Ash + đoạn Canyon gần camera + menu/garage**. Dựng chi tiết đúng concept, UV/material có mục đích, animation/contacts hợp lý; render cùng camera/ánh sáng/khoảng cách gameplay trong Unity.
4. Chỉ khi mẫu qua visual và technical gates mới nhân rộng roster/biomes. Thay geometry/material có kiểm soát, giữ gameplay IDs và phần code đúng. Chạy lại source/FBX/prefab/importer/rig/clip hash-bound audits trên revision đã freeze.
5. Đóng content mapping, build Windows, kiểm UI/input/audio/memory/FPS/network thật rồi mới tiếp tục nghiệm thu phase. Không lấy số file, độ phân giải texture hay dung lượng build làm đại diện cho chất lượng.

## So sánh trực tiếp

### Apex: concept và model đã dựng

![Apex concept](../../../ArtSource/Concepts/P08/Bikes/05-apex-v1.png)

![Apex current Blender render](../art/RB_P08_Bike_05-render.png)

### UI hiện chạy trong Unity

![Current Unity main menu](captures/editor-main.png)

![Current Unity gallery](captures/editor-gallery.png)

Các ảnh runtime trên là bằng chứng về phần trình bày hiện tại, không phải hình quảng bá hoặc ảnh concept giả làm gameplay.
