# Racing Bois — Yêu cầu sản phẩm và tiêu chuẩn nghiệm thu

Ngày lập: 2026-09-21 (Asia/Bangkok). Tài liệu gốc để đối chiếu ở mọi phase.

## 1. Phạm vi đã được người dùng yêu cầu

- Tên sản phẩm: **Racing Bois**.
- Reverse-engineer sâu bản mod tại `C:\Users\Liquid\Downloads\Unity\racing_bois_mod`, hướng tới hiểu đầy đủ logic và toàn bộ nội dung/assets.
- Video tham chiếu: `C:\Users\Liquid\Downloads\prompt\Road Rash PC (1995) - Big Game Mode (All Levels).mp4`.
- Lối chơi mục tiêu giống Road Rash bản PC mà người dùng gọi là Road Rash 1996. Tên video có năm 1995; không tự coi hai build là cùng một binary. Bản mod và video là hai nguồn đối chiếu riêng.
- Phát triển game bằng Unity; **mục tiêu chính hiện tại là desktop Windows 10/11, bản Web thực hiện sau** (cập nhật trực tiếp của người dùng ngày 2026-09-26, thay ưu tiên browser trước đây).
- Giữ cảm giác đua xe, chiến đấu, va chạm, té xe, trở lại xe và tiến trình chơi của tham chiếu; bổ sung multiplayer online và LAN.
- Multiplayer online cho người chơi ở nhiều quốc gia, kết nối qua Internet đến server. Backend quyết định di chuyển, chiến đấu, sát thương, kết quả trận, tài khoản, vật phẩm, tiền tệ, lobby và join lobby.
- **LAN chơi được khi mất Internet hoàn toàn** (người dùng đã xác nhận). Gói LAN ưu tiên client Windows 10/11, assets đã cài, server trận và dữ liệu cần thiết để tự chạy trong mạng nội bộ; client Web bổ sung sau.
- Resource, database, assets và user data online đặt trên VM OCI. Dữ liệu LAN offline buộc lưu cục bộ trong thời gian mất Internet; phân biệt dữ liệu LAN và tài khoản online, không tự đẩy tiền/vật phẩm offline vào economy online.
- Đồ họa, hiệu ứng phải đẹp, sống động, bắt mắt ở góc nhìn gameplay thực tế; hiệu năng tốt là điều kiện nghiệm thu, không phải việc làm sau cùng.
- **Cập nhật của người dùng về UI/UX:** đẹp, mượt mà; hiệu ứng sống động, bắt mắt; chuyên nghiệp, thân thiện và dễ sử dụng. Chi tiết và gate: [UI_UX_DIRECTION.md](UI_UX_DIRECTION.md).
- **Cập nhật của người dùng về source code:** design pattern chuẩn và phù hợp bài toán, readable/clean/maintainable, dễ bảo trì và mở rộng chức năng mới. Kiến trúc, hướng dependency, pattern và gate: [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md).
- Khối lượng nội dung/assets hoàn thiện **ít nhất bằng bản gốc được kiểm kê**, đồng thời có nội dung multiplayer mới. Theo dõi ánh xạ nội dung gốc → nội dung Racing Bois; không tăng số lượng bằng file trùng, LOD hay đổi tên.
- **Cập nhật trực tiếp của người dùng: assets chỉ dựa trên bản gốc để chỉnh sửa thiết kế và làm lại từ đầu, không copy 100% bản gốc.** Toàn bộ asset production được sáng tạo/sản xuất mới: model, texture, material, rig/animation, UI/portrait, audio/music và cinematic. Assets trích xuất chỉ phục vụ nghiên cứu/tham chiếu; không import vào Unity hoặc đóng gói vào game.
- Dùng Blender MCP trên máy để sản xuất assets, Unity MCP để thao tác/code/import/kiểm tra trong Unity.
- Yêu cầu thực hiện mới: triển khai P01 và P02 sau P00. Các bằng chứng/giới hạn cập nhật ở [P01_P02_STATUS.md](P01_P02_STATUS.md); không tự chuyển sang sản xuất nội dung đầy đủ hoặc triển khai public P09.

## 2. Cách hiểu mục tiêu “100%”

Không có một phần trăm chung suy ra từ số file, số strings, số hàm disassemble hoặc số ảnh đã xem. Báo cáo riêng:

| Trục | Bằng chứng cần có trước khi ghi hoàn tất |
|---|---|
| File coverage | Mọi file trong snapshot có đường dẫn, kích thước, SHA-256 và phân loại |
| Container coverage | Mọi entry được thống kê, offset/size hợp lệ, giải nén có kiểm tra đầy đủ |
| Asset decode | Mọi ảnh/âm thanh/video/font/sprite có decode report; palette/alpha/timing/metadata đúng |
| Logic coverage | Mỗi hệ thống có hàm/data reference, đặc tả hành vi và test đối chiếu; gọi rõ logic chưa hiểu |
| Behavior parity | Replay có input/timing, trạng thái và kết quả so sánh với reference; định lượng sai lệch |
| Content parity | Mọi nội dung độc lập có mapping sang asset làm mới từ đầu và tiêu chí tương đương được nghiệm thu |
| Production readiness | Prefab, build Windows 10/11, multiplayer, LAN, server, lưu dữ liệu và performance đều vượt gate; Web có nghiệm thu riêng khi triển khai sau |

Mã máy tối ưu không giữ nguyên tên biến, comment hoặc cấu trúc source; disassembly không phải khôi phục nguyên source. Ghi rõ `verified`, `inferred`, `unknown`, `blocked` cho từng kết luận. Mục tiêu đầy đủ được giữ nguyên nhưng không tuyên bố đạt khi thiếu bằng chứng.

## 3. Checklist 3D asset production-ready (bắt buộc)

### Model

- [ ] Scale đúng (quy ước dự kiến 1 Unity unit = 1 m), có vật chuẩn kích thước.
- [ ] Pivot hợp lý theo vai trò: bánh xe ở trục quay, xe ở root điều khiển, props tiếp đất đúng.
- [ ] Không mesh lỗi, mặt ngược, vertex thừa; normals nhất quán, không geometry rác.
- [ ] Polycount phù hợp budget từng loại và lượng xuất hiện trong gameplay.
- [ ] Naming rõ ràng và ID bền vững giữa Blender, export, Unity, manifest.

### UV & Texture

- [ ] UV không overlap ngoài chủ đích; phần mirrored/reused phải khai báo.
- [ ] Texture đúng resolution và texel density theo khoảng cách quan sát.
- [ ] Có Base Color, Normal, Metallic, Roughness hoặc Mask Map khi vật liệu cần.
- [ ] Chuyển Roughness ↔ Smoothness và packing theo đúng shader; không gắn nhầm channel.
- [ ] Texture compression đúng platform/quality tier; kiểm tra normal, alpha và artifact.

### Material

- [ ] Shader đúng pipeline đã chọn: URP cho client Windows chính và target Web bổ sung.
- [ ] Không missing material/shader, không vật thể màu hồng.
- [ ] Không tạo material duplicate không cần thiết; atlas/shared material khi phù hợp.

### Optimization

- [ ] Có LOD khi asset lớn hoặc xuất hiện nhiều; chuyển LOD không gây popping khó chịu.
- [ ] Mesh compression hợp lý và đã kiểm tra sai lệch silhouette/UV/animation.
- [ ] Static flag chính xác đối với asset tĩnh; không đánh static sai cho xe/nhân vật.
- [ ] Texture/material không vượt budget; có số đo bộ nhớ resident và tải qua mạng.
- [ ] Pooling/instancing/culling và streaming cho nhóm xuất hiện lặp lại.

### Collider

- [ ] Collider đúng hình dạng phục vụ gameplay, khớp asset và server collision proxy.
- [ ] Dùng Box/Sphere/Capsule khi đủ; chỉ dùng MeshCollider khi có lý do đo được.
- [ ] Collider không thừa hoặc chồng lặp; trigger/hitbox intentional phải ghi chức năng/layer.

### Prefab

- [ ] Đã tạo prefab có GUID và manifest entry.
- [ ] Root Position (0,0,0), Rotation phù hợp quy ước export, Scale (1,1,1).
- [ ] Không Missing Script hoặc Missing Reference.
- [ ] Không phụ thuộc object nằm riêng trong scene test để hoạt động.

### Lighting

- [ ] Normal/tangent đúng, thử với ánh sáng ở nhiều hướng.
- [ ] Có lightmap UV khi dùng baked lighting; UV2 không overlap và có padding phù hợp.
- [ ] Không artifact khi chiếu sáng, seam bất thường hoặc bóng đổ sai.

### Animation (nếu có)

- [ ] Rig đúng; bone naming, bind pose và weight sạch.
- [ ] Animation clip sạch, đủ trạng thái phục vụ gameplay.
- [ ] Loop/Root Motion đúng yêu cầu; chuyển động có thẩm quyền thuộc simulation.
- [ ] Avatar/Humanoid mapping đúng nếu dùng Humanoid; Generic rig phải khai báo rõ.
- [ ] Các clip lái, nghiêng xe, đánh trái/phải, trúng đòn, té, chạy về xe, lên xe khớp state machine.

### Test cuối

- [ ] Drag prefab vào scene và chạy bình thường.
- [ ] Không Console Error/Warning liên quan asset.
- [ ] Quan sát tốt ở khoảng cách, camera, tốc độ và số lượng đối tượng gameplay thực tế.
- [ ] FPS/memory không bị ảnh hưởng bất thường; có capture profiler trước/sau.
- [ ] Web build thực chạy được; Editor PASS không thay cho browser PASS.

## 4. Hồ sơ bắt buộc cho từng asset

`assetId`, loại, reference ID từ bản gốc, thiết kế mới, nguồn/provenance sản xuất mới, đường dẫn `.blend` hoặc source audio/UI, file export, Unity GUID, phiên bản, kích thước mét, pivot, triangles từng LOD, materials, texture sizes/format/memory, UV/UV2 report, colliders, rig/clips, dependency list, screenshot gameplay và trạng thái checklist. Phải có bằng chứng source mới; chỉ đổi tên, resize, re-encode hoặc thay vài pixel của file trích xuất không đáp ứng yêu cầu làm lại từ đầu.

Kiểm tra build loại trừ thư mục research và file/hash gốc. Hash khác nhau chỉ phát hiện copy byte-for-byte, không tự chứng minh asset được làm mới; cần review source/design/production history.

LOD, bản nén, quality variants và animation frames không được cộng như nhiều nội dung độc lập để làm đẹp số lượng. Các animation clip mới phải bao phủ hành động gốc, không yêu cầu một mesh mới cho mỗi sprite frame.

## 5. Nguyên tắc nghiệm thu

Mỗi phase kết thúc bằng bản chạy được hoặc artifact kiểm tra được, bằng chứng, danh sách gap và bản cập nhật kế hoạch. Không chuyển sang sản xuất hàng loạt khi vertical slice chưa chứng minh chất lượng hình ảnh, gameplay và budget. Những con số performance/capacity trong kiến trúc là **mục tiêu đề xuất**, chưa phải kết quả benchmark.

Các chỉ tiêu còn cần chốt bằng prototype: số người/trận, concurrent users, chất lượng thấp nhất hỗ trợ, địa điểm OCI, chi phí/tháng, domain, RPO/RTO và cách đo tương đương nội dung đặc biệt như FMV/nhạc. Không dùng thiếu thông tin này để ngăn việc reverse và lập kế hoạch.
# Bổ sung quy trình assets — 2026-09-21

Mọi asset 3D mới phải có **concept 2D được tạo trước khi dựng/chỉnh thiết kế 3D**, theo yêu cầu người dùng dùng GPT Image 2.5. Lưu ảnh concept, prompt, công cụ/model thực tế nếu xác nhận được, rồi dùng Blender MCP dựng asset mới theo hình đó; lưu mapping concept → nguồn Blender → FBX/maps → prefab → QA. Không lấy assets game gốc làm production assets. Nếu công cụ không cho chọn/xác minh model được yêu cầu, ghi rõ thực tế, không tự gắn nhãn model. Bộ graybox tạo trước yêu cầu này phải đi qua revision dựa trên concept trước khi chốt.

## Bổ sung UI và kiến trúc — 2026-09-26

- UI mới hoặc redesign cũng phải có **concept 2D được tạo và xem trước**, rồi mới triển khai layout/component Unity tương ứng. Lưu prompt, ảnh, provenance và mapping concept → màn hình → kiểm thử thực tế. Không dùng ảnh concept làm một tấm ảnh giả thay cho UI tương tác.
- Thiết kế UI cần có bản sắc motorsport của Racing Bois, bố cục rõ, hình ảnh từ assets thực, thao tác thuận tiện và motion có mục đích; tránh layout đại trà, panel/card lồng nhau, hiệu ứng trang trí quá mức và thông tin không giúp người chơi quyết định.
- Source toàn game tiếp tục dùng design pattern chuẩn phù hợp bài toán thực, readable, dễ dọn dẹp, maintainable và dễ mở rộng chức năng. Ranh giới domain/application/adapter/presentation và lifetime phải rõ; không thêm framework rỗng để trang trí kiến trúc.
- Nghiệm thu gồm bản chạy thật, focus bàn phím, trạng thái loading/error/retry, scale/responsive, giảm chuyển động, console và performance. Concept đẹp hoặc compile thành công riêng lẻ không xác nhận chất lượng sản phẩm cuối.

## Ưu tiên nền tảng — 2026-09-26

- Bản phát hành và nghiệm thu chính: client Unity desktop Windows 10/11 x64. UI hỗ trợ chuột/bàn phím, gamepad, thay đổi độ phân giải và chế độ cửa sổ/fullscreen.
- Backend online, database, tài nguyên và dữ liệu người chơi online tiếp tục triển khai trên VM OCI. Chuyển client sang desktop không chuyển quyền quyết định gameplay/economy về client.
- LAN offline tiếp tục dùng máy chủ cục bộ và realm riêng. Client desktop phải tải được content đã cài khi không có Internet; không phụ thuộc một browser/server web chỉ để khởi động luyện tập.
- Web là target bổ sung về sau. Các kiểm chứng Web ở P02–P07 là bằng chứng lịch sử; không thay cho build, chạy và benchmark Windows desktop hiện tại.
- Đồ họa/content dùng bundle đúng `StandaloneWindows64` cho desktop; không nạp bundle WebGL vào Windows. Gói client chứa content cần offline và tách hoàn toàn khỏi source nghiên cứu, WAV masters, credential và database server.

## Quy tắc công cụ và độ khớp prototype — 2026-09-27

- Người dùng đã cho phép thực hiện liên tục P08–P10, gồm triển khai OCI và nghiệm thu phát hành, không yêu cầu xác nhận lại giữa các bước đã được phép. Chỉ dùng công cụ local/miễn phí cho phục hồi assets; không mua credit hoặc dùng dịch vụ tạo3D trả phí.

- **Tuyệt đối không dùng Jarvis MCP khi làm việc bằng Codex**, kể cả tìm công cụ, đọc trạng thái hoặc gọi gián tiếp Blender/Unity/tạo ảnh qua Jarvis. Dùng MCP Blender và Unity trực tiếp, công cụ tạo ảnh tích hợp; áp dụng cho mọi agent được giao việc.
- **UI và assets 3D phải giống 100% prototype/concept 2D đã chốt.** Concept là đặc tả hình ảnh bắt buộc. Không nghiệm thu một mẫu chỉ vì trông gần giống, có đủ chi tiết cơ bản hoặc vượt kiểm tra kỹ thuật.
- Đối chiếu ảnh UI/render thật với đúng phiên bản concept ở góc nhìn, khung hình, tỷ lệ và điều kiện ánh sáng tương ứng. Kiểm silhouette, tỷ lệ, hình khối, vị trí bộ phận, vật liệu, màu sắc, chi tiết, typography và bố cục.
- Mẫu còn khác phải được ghi rõ sai khác và giữ trạng thái chưa đạt. Không tuyên bố khớp100% khi chưa có bằng chứng; không tự hạ tiêu chí thành một tỷ lệ thấp hơn hoặc thay concept bằng render3D chưa đạt.
- Nếu reference có các góc hoặc thông tin mâu thuẫn, giải quyết và chốt reference nhất quán trước khi sản xuất. Quy trình concept2D trước3D/UI, checklist production, nghiệm thu native và hiệu năng vẫn bắt buộc.
