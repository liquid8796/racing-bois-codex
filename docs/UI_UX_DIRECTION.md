# Racing Bois — Định hướng UI/UX và tiêu chí nghiệm thu

Trạng thái: yêu cầu và định hướng tổng thể; P02 đã có menu/HUD fixture trong Unity Web để kiểm tra input, typography và networking. Đây chưa phải bộ UI/art cuối P06. Người dùng yêu cầu UI/UX **đẹp, mượt mà, hiệu ứng sống động/bắt mắt, chuyên nghiệp, thân thiện và dễ sử dụng**. PC/laptop browser là nền tảng đầu tiên; assets được thiết kế mới từ đầu.

## 1. Trải nghiệm và ngôn ngữ thị giác

Racing Bois có bản sắc đua xe đường phố: mặt đường, kim loại, gara, ánh sáng nóng/lạnh và chuyển động tốc độ. Không sao chép dashboard/portrait/menu pixel của game gốc; giữ khả năng đọc trạng thái và nhịp chuyển màn, tạo typography, iconography, layout, illustration và âm thanh UI mới.

Hướng để thử ở vertical slice: nền graphite tối, chữ sáng, một accent amber/orange cho hành động chính, màu semantic riêng cho ready/danger/connection. Không khóa mã màu/font trước moodboard và kiểm contrast. Header có cá tính nhưng body/số tốc độ/rank phải dễ đọc; tối đa hai họ font, hỗ trợ tiếng Việt nếu có localization. Font được đóng gói trong game/LAN bundle, không tải từ CDN lúc chơi.

Gara có thể có xe 3D/ánh sáng chuyển động chậm; lobby có backdrop sinh động vừa phải. Khi đua, thứ tự ưu tiên là **đường → đối thủ/traffic → tín hiệu combat → HUD**. Hạn chế hiệu ứng nền, overlay lớn và nhấp nháy khiến mất khả năng đọc gameplay.

Skill `ui-ux-pro-max` đã dùng để tham khảo: nhóm Gaming/3D showcase, keyboard navigation/focus, reduced motion và excessive motion. Mẫu landing-page/CTA/Three.js từ kết quả tìm kiếm không phù hợp client Unity nên không áp dụng; phần dưới là thiết kế dành riêng cho Racing Bois, chưa phải art direction được người dùng nghiệm thu.

## 2. Luồng chính và hierarchy

| Màn/luồng | Hành động chính | Trạng thái cần thiết |
|---|---|---|
| Boot/loading | Vào game hoặc tiếp tục | Progress tải thực, lỗi/retry, phiên bản content, audio unlock từ thao tác người dùng |
| Home | Chơi đơn / Online / LAN | Lần đầu có hướng dẫn ngắn, tiếp tục phiên đang chơi, settings rõ |
| Online | Quick join / tạo phòng / nhập mã | Region/latency, phiên đăng nhập, lỗi mạng, empty/full/incompatible room |
| LAN | Vào host đã mở hoặc hướng dẫn mở LAN Host | Trạng thái offline, URL/QR, tên host/realm, không ép đăng nhập Internet |
| Lobby | Chọn xe/ready | Thành viên/slot, course/rule, ready/countdown, host lobby, ping và reconnect |
| Gara/shop | Xem xe/so sánh/chọn/mua | Ownership, đủ/thiếu tiền, trade/cost rõ, xác nhận giao dịch có hậu quả |
| Campaign/route | Chọn chặng/tiếp tục | Qualification/progression, độ dài/độ khó, unlock và phần thưởng |
| Race HUD | Lái và đánh | Speed/rank/progress, rider/bike state, đối thủ, connection warning dễ hiểu |
| Pause/settings | Tiếp tục/đổi cài đặt/rời trận | Phân biệt pause chơi đơn với menu online trong khi trận vẫn chạy |
| Results | Hiểu kết quả, nhận thưởng, rematch | Hạng/thời gian/penalties, reward trạng thái đã ghi nhận hoặc đang xử lý |
| Reconnect/error | Quay lại chơi | Lý do ngắn gọn, tiến trình retry, lựa chọn thoát an toàn, không giả báo thành công |

Mục tiêu usability để test: người chơi mới tìm được Play/Online/LAN mà không cần giải thích; sau khi tải xong, vào quick match qua tối đa ba quyết định chính (không tính thao tác login nếu bắt buộc). Không ẩn Join sau nhiều tầng menu. Thông tin nâng cao mở dần, không dồn thông số kỹ thuật vào flow chơi game.

## 3. Motion, âm thanh và phản hồi

- Mọi control có trạng thái normal/hover/focus/pressed/disabled/loading/success/error nhất quán.
- Phản hồi nhấn bắt đầu ở frame kế tiếp; tác vụ server cho thấy pending và không giả khẳng định thành công trước ack. Không khóa input chờ animation trang trí.
- Khoảng thời gian ban đầu để thử: feedback nhỏ 80–160 ms, panel 180–280 ms, reward showcase 300–600 ms và có skip. Đây là budget UX đề xuất, không hằng số cho mọi hiệu ứng.
- Transition liên tục về vị trí, tween bị ngắt vẫn đi đến state hợp lệ; click nhanh/back/resize không tạo modal chồng hoặc mất focus.
- UI sounds ngắn, volume riêng; không spam sound mỗi snapshot/cập nhật ping. Music ducking khi thoại/tín hiệu nguy hiểm nếu phù hợp.
- Tùy chọn Reduced Motion, camera shake, motion blur, HUD scale và audio sliders. Reduced Motion vẫn truyền đạt ready/hit/error bằng hình/âm/text; không chỉ bỏ hết feedback.
- Combat VFX có directional cue và phân biệt hit đã xác nhận với pose dự đoán. Reward animation không thay đổi ledger hoặc tạo thêm request thưởng.

## 4. Dễ đọc, điều khiển và khả năng tiếp cận

- Menu dùng được bằng mouse, keyboard và gamepad theo platform đã test; focus luôn thấy, thứ tự hợp lý, Back/Escape nhất quán; modal trả focus về nguồn khi đóng.
- Game canvas và web shell có quy tắc focus/input rõ để không nuốt text khi chat/nhập mã; tránh browser shortcut xung đột với controls mặc định. Remap và restore defaults.
- Mục tiêu contrast text thông thường ≥4.5:1; trạng thái không chỉ dựa vào màu. Đo với background gameplay sáng/tối thực, không chỉ bảng màu phẳng.
- Body menu xuất phát tương đương 16–18 px tại reference resolution; HUD scale tùy chỉnh. Nút có vùng bấm đủ rộng, mục tiêu tối thiểu 44×44 px ở menu; đây là lựa chọn usability của sản phẩm.
- Label rõ, lỗi ở gần input, copy lỗi ngắn có cách xử lý, tên phòng/nhân vật dài không phá layout.
- Thử 1280×720, 1366×768, 1920×1080, 2560×1440, ultrawide, window resize và browser scale. Tôn trọng tỉ lệ/chừa vùng an toàn; không kéo giãn xe/HUD.
- Không tuyên bố hỗ trợ screen reader/chuẩn accessibility đầy đủ chỉ vì dùng Unity UI. Phải kiểm khả năng expose semantic cho web shell/menu trên browser thực và ghi rõ phần hỗ trợ.

## 5. Kiến trúc UI và performance

Xem [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md): view chỉ render state và phát UI intent; presenter/view-model gọi application use case. UI không sửa trực tiếp HP/transform/tiền/network state. Tất cả logic hiển thị dùng cùng schema trạng thái loading/error/retry, không mỗi màn một cách.

Chọn UI Toolkit hoặc uGUI sau spike trên Unity 6000.5.7f1 Web; không trộn hai hệ thống rộng khắp mà thiếu lý do. Token typography/spacing/colors/motion, common controls, screen navigation/state và localization được dùng lại. Tránh allocations/rebuild layout mỗi network tick; update những giá trị đổi, pool/virtualize lobby lists và hạn chế overdraw.

Tách local feedback khỏi network response. Client có thể show pending nhanh nhưng kết quả mua/ready/join/hit tuân theo server. Không dùng animation completion callback làm thẩm quyền gameplay.

## 6. Nghiệm thu theo phase

| Phase | Artifact UI/UX bắt buộc |
|---|---|
| P02 | Input/focus/navigation spike trong Web build, draft tokens, component/state conventions |
| P03–P04 | HUD đọc được khi lái/đánh; telemetry không che đường; crash/recovery cues |
| P05 | Lobby/join/ready/reconnect/LAN flows end-to-end; các lỗi network có trạng thái/action |
| P06 | Bộ mockup/art direction mới, shared controls, menu+HUD+results hoàn thiện, motion/audio capture, test người mới |
| P07 | Shop/account/progression transaction feedback rõ; pending/retry/idempotency UX |
| P08 | Toàn bộ screens/content/localization bao phủ state matrix, không màn placeholder |
| P10 | Keyboard/gamepad/focus, reduced motion, scale/responsive, slow network, rapid navigation và browser performance PASS |

Đo riêng thời gian mở màn, input feedback, UI CPU/GC/overdraw ở lobby đông và HUD khi race có 16 riders. Không lấy animation mượt trong Editor làm bằng chứng browser đạt 60 fps. Chụp/video cả normal/loading/empty/error/disabled/offline thay vì chỉ một màn đẹp.
