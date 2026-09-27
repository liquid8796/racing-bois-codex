# UI runtime review — 2026-09-26

## Kết luận

UI hiện tại có cấu trúc ứng dụng dùng lại được, nhưng **chưa đạt chất lượng hình ảnh desktop và chưa bám đủ concept để nghiệm thu**. Cần sửa bố cục, hệ component và art nền; không cần xóa application sessions, backend hay viết lại toàn bộ UI logic. Concept v2 phải chốt dữ liệu/trạng thái thật trước khi thay phần trình bày.

## Phương pháp và giới hạn

Root xem trực tiếp năm concept UI và chạy scene Race trong Unity 6000.5.7f1, target StandaloneWindows64. Main menu được capture ở trạng thái khởi động thật. Các màn settings, gallery, career disconnected được mở qua public presentation APIs; loading/error là state được bơm có chủ đích qua `SetContentState`, không phải bằng chứng download hoặc backend thật.

Viewport Editor là **1105×506**, panel `ScaleWithScreenSize`, reference1600×900, logical layout1965.4×900. Ảnh không phải build Windows1920×1080. Kích thước chữ nhỏ trong ảnh phải đọc cùng scaling này; chưa kết luận font16px ở1080p không đọc được. P08 actor/content pack chưa hoàn chỉnh; xe/rider/canyon hiện lên là fallback P06. Không đánh dấu garage đã đăng nhập, lobby8người, HUD đang race hoặc cinematic playback đã được kiểm chứng hình ảnh trong lần review này.

Không sửa production code/assets hoặc PlayerPrefs trong review. Play mode được dừng sau khi capture. Console cuối smoke trả về0error/0warning; cảnh báo compiler MCP package ở lần switch target trước đó là bằng chứng khác.

## Findings

| Mức | Vấn đề | Bằng chứng và hướng sửa |
|---|---|---|
| P1 | Main menu mất hierarchy của concept và có scroll ngay ở màn chọn hành động chính | [Ảnh runtime](captures/editor-main.png) so với `ArtSource/Concepts/P08/UI/ui-main-v1.png`: concept cho CTA lớn, tuyến đọc một dòng, khung nhìn có chiều sâu; runtime là rail430logicalpx, CANYON RUN tách hai dòng, footnote nằm dưới vùng cuộn và cảnh nền/actor kém chi tiết. `Race.uss:12` đặt top19%, bottom94px, width430px. Thiết kế lại rail/safe-area theo nhiều tỉ lệ, giữ hành động chính không phải cuộn; không chỉ tăng font cho mọi thành phần. |
| P1 | Responsive dựa vào logical bounds chưa xử lý viewport nhỏ hiệu quả | `RaceScreen.cs:281–285` dùng bounds.height<780 hoặc width<1400; viewport thực1105×506 lại có logical1965×900, nên layout không vào compact/narrow. Panel reference1600×900 khiến các màn16:9 nhỏ có thể tiếp tục thu nhỏ mọi chữ/control mà không reflow. Cần dùng chiến lược UI scale/breakpoint có xét output pixels, tách scale menu với HUD, rồi kiểm1366×768/1920×1080/ultrawide thật. Đây là quan sát tại viewport đã ghi, không phải kết quả chạy cả ma trận độ phân giải. |
| P2 | Component chưa có skin đồng nhất | Main/gallery có scrollbar trắng và mũi tên mặc định. Gallery dropdown nền xám sáng, khác dropdown tối trong settings; progress error có track xám mặc định. [Gallery](captures/editor-gallery.png), [error](captures/editor-content-error.png), [settings](captures/editor-settings.png). Cần tokens chung cho ScrollView, dropdown, progress, focus, disabled; kiểm tương phản và trạng thái hover/focus/pressed thực. |
| P2 | Gallery có bố cục và nội dung chưa hoàn thiện | Panel69% che cả actor đang nằm phía dưới text, khoảng trống phía phải không tạo được sân khấu cho cảnh. Giao diện tiếng Việt nhưng titles/synopsis tiếng Anh; dòng `59 cảnh 3D` không thay cho chứng cứ59cảnh đã render. Cần stage/camera/art được kiểm chứng, danh mục và trạng thái browse/playback riêng, localization keys, caption/skip rõ. Không dùng ảnh gallery concept chứa xe Yamaha làm background production. |
| P2 | Trạng thái chưa có hồ sơ còn mang hình thức form tạm | [Career disconnected](captures/editor-career-disconnected.png) dồn nội dung lên đầu, hai nút kéo gần toàn chiều ngang, vùng trống lớn không có hierarchy. Thông điệp phân biệt realm/offline đúng và nên giữ. Cần thiết kế empty/account states có chiều rộng đọc và primary action hợp lý; đừng ép khuôn garagepreview lên mọi tab. |
| P2 cần debug | Các modal có thể tranh focus | Trên menu, bơm contenterror có `BlocksGameplayInput=true`, `ContentBusy=true`, focusRetry: PASS trong quan sát này. Khi contentloading được mở trên Settings, localbutton disabled và focus ban đầu là content-loading, nhưng ở lần đọc sau focus chuyển về root-container ngoài modal. `RaceScreen.cs:95–104`, `CareerView.cs:68–71`, `RaceScreen.Content.cs:46–58` có focus callbacks riêng, không có một owner ưu tiên thống nhất. Cần xác minh bằng keyboard/windowfocus ổn định và sửa ownership nếu tái hiện; chưa kết luận đã thấy gameplay input lọt qua. |

`FocusContent()` đọc `resolvedStyle.display` ngay sau đổi inline display là một rủi ro timing trong source. Lần bơm lỗi đã vào Retry đúng, nên không ghi nó thành bug đã tái hiện. Dữ liệu quan sát được giữ trong [ui-observations.json](ui-observations.json).

## Phần nên giữ

- Palette graphite/ivory/amber, bố cục ưu tiên cảnh3D, HUD ngoại vi, danh sách garage và lobby có ý nghĩa.
- Application sessions/read models/intents và authority backend; selected preview tách khỏi equip/purchase.
- `UiBindingScope`, cleanup callbacks, content ownership blocking, reduced-motion, font hỗ trợ tiếng Việt và native display adapter.
- Thông tin offline/guest/persistent-career rõ ràng; trạng thái chưa có pack phải báo đúng.

## Gate cho lần sửa tiếp theo

1. Concept v2 dùng đúng route/bike/character IDs, controls và UI states; bỏ chữ trang trí tự bịa/brand thật.
2. Một màn menu+garage thật đạt chất lượng với một xe và rider mẫu đã được duyệt trong Unity. Không lấy concept photoreal làm bằng chứng runtime.
3. Skin component đồng nhất; main actions trong safe-area; cơ chế focus/Back/Tab có một owner; loading/error không khóa người dùng vào đường cụt và không kích hoạt màn phía sau.
4. Chụp/so sánh native1366×768,1920×1080,2560×1440 vàultrawide, có UIscale, longVietnamese/playernames, disconnected/full/error states.
5. Kiểm mouse/keyboard/gamepad thật, chuyển màn/reduced-motion, profile memory/frame time. Cần build/source-bound receipts trước khi gắn productionPASS.

Không xóa UI source trong review. Các ảnh concept cũ giữ làm lịch sử; chỉ retire sau khi bản thay thế được kiểm chứng và cập nhật references.
