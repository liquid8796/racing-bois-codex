# Racing Bois

Game Unity đua xe/chiến đấu lấy Road Rash PC làm tham chiếu gameplay. Client chính là **Windows 10/11 x64**; Web bổ sung sau. Assets production làm mới từ đầu, online có server authority trên OCI và LAN dùng realm cục bộ độc lập khi mất Internet.

**Hiện trạng xác minh ngày 2026-09-27:** P08–P10 đang triển khai, chưa có bản Windows được nghiệm thu phát hành. [Regression mới nhất](docs/p10/regression/20260927T105143Z/receipt.json) PASS 261 nhóm/17 suite, source ổn định và production gate còn đóng. [Soak socket tám giờ](docs/p10/network/20260927T003037Z/run.json) hoàn tất 359 vòng đua, 238 reconnect và 47 storm; ghi nhận một dropped catch-up tick và correction thô tối đa 5.489338 m, nên không thay cho nghiệm thu hình ảnh/chuyển động hoặc soak Unity player. [Receipt OCI staging f](docs/p09/releases/f/deployment-after-soak.json) xác nhận multiplayer protocol 6, HTTPS/WSS public và dữ liệu private; [WAN 30 phút](docs/p09/releases/f/capacity.json) chỉ đo một phòng tám client từ một mạng Windows đến Frankfurt. Đây là bằng chứng đã lưu, không phải kiểm tra trạng thái dịch vụ trực tiếp ở thời điểm đọc README.

Các mẫu Apex R4, Ash V6, garage V7 và menu environment V1 đã có kiểm chứng Unity theo phạm vi; Ash V7 đang chờ import và Spark V1 đang hoàn thiện export. Tất cả vẫn chưa đạt concept đã chốt; production masks giữ **1/1/1**. Roster/routes, bản game native đầy đủ, performance/input/hardware, LAN hai PC cắt WAN, client thật nhiều vùng và đóng gói phát hành còn mở. P01 reverse/parity và các gate P05/P06 chưa được tự đóng. Xem [checkpoint và danh sách tiếp tục](docs/P08_P10_RUN.md), [P08](docs/P08_STATUS.md), [P10](docs/p10/README.md).

**Hồ sơ P07 lịch sử:** bản `0.7.0` đã bàn giao local hồ sơ/tài khoản, garage/shop, wallet ledger, campaign, SQLite và lobby công khai/riêng tư. Các receipt Web/native/application ở [P07_STATUS.md](docs/P07_STATUS.md) chỉ xác nhận snapshot đó; 15 SKU không đồng nghĩa 15 mẫu art được nghiệm thu. Hướng dẫn bên dưới được giữ cho gói P07, không phải bản phát hành Windows P08–P10.

## Chạy gói P07 lịch sử

Snapshot P07 ghi nhận runtime `3cac900`, Web `Build/Web-p07-v4` và database QA riêng. Commit ID/URL demo dưới đây là thông tin lịch sử, không xác nhận Git binding hoặc tiến trình đang chạy hiện tại. Khi chạy lại, kiểm tra lựa chọn trong `Build/current-web.txt` và receipt của đúng gói.

Demo local: [Racing Bois P07](https://localhost:7888/), hoặc [HTTP local](http://127.0.0.1:7887/). Chọn **Vào cuộc đua** để luyện tập offline. Để chơi mạng, chọn **Online / LAN → Kết nối**, tạo phòng hoặc nhập mã, mọi người **Sẵn sàng**, rồi chủ phòng **Bắt đầu**. Nếu mở thêm người chơi trong cùng browser, chọn **Khách mới** ở tab thứ hai. Sau reload, nhấn **Kết nối** trong 30 giây để xin trở lại chỗ cũ. Endpoint tự chọn `/multiplayer` theo địa chỉ trang.

Trên bản P07, mở **Garage / Hồ sơ** từ menu hoặc lobby để xem xe, cửa hàng, hành trình, giao dịch và tài khoản. Chỉ cấp campaign hiện tại có thể tạo chặng. Đăng nhập/đăng ký/khôi phục cần trang HTTPS và endpoint `wss://`; hãy tự lưu mã khôi phục một lần. Khách mới và luyện tập offline không tích lũy vào garage máy chủ. Export/import LAN chỉ nhận checkpoint hợp lệ của cùng hồ sơ/realm và không hoàn lại giao dịch đã chốt. Nếu mọi xe đều hỏng và không đủ sửa, có thể xác nhận bắt đầu lại với starter nguyên vẹn, quỹ $0 và mất tiến trình garage/campaign; tài khoản/ledger vẫn giữ.

Điều khiển: **W/S** ga/phanh, **A/D** lái, **Q/E** đánh trái/phải, **Shift+Q/E** đá, **R** đua lại local, **Esc** đóng cài đặt/thoát focus điều khiển trước khi rời cuộc đua. Nút **Giữ ga** hỗ trợ tăng tốc liên tục; vẫn cần tự lái qua cua. **Cài đặt** có Low/Medium/High, giảm chuyển động, bật/tắt âm thanh và HUD 85–115%. Cuộc đua tiếp tục khi mở cài đặt.

Gói P07 và SHA-256: [hồ sơ phân phối](docs/p07/backend/DELIVERY.md). Giải nén toàn bộ ZIP Windows, chạy `launch-lan.bat`; mở `LAN_JOIN.html` để xem URL/QR. Gói dùng port 7777 mặc định; demo đang mở dùng 7887/7888. Dữ liệu ở thư mục riêng `data`, cần giữ lại khi nâng cấp; migration P05 có backup và không tự trộn realm. Windows SelfTest/SQLite native đã chạy; ARM64 mới kiểm tra tĩnh, chưa chạy native. Xem [hướng dẫn P07](tools/p07/README-P07.md) và [build/đóng gói/kiểm chứng](tools/p07/VALIDATION.md). Build outputs không commit vào Git. `tools\foundation\stop-local.bat` nhận diện đúng PID/executable/start time trước khi dừng demo đã ghi nhận.

- [P07: tài khoản, progression, kiểm chứng và trạng thái phân phối](docs/P07_STATUS.md)
- [P08–P10: checkpoint hiện tại và việc cần tiếp tục](docs/P08_P10_RUN.md)
- [P10: regression, soak, native WSS và gate phát hành](docs/p10/README.md)
- [P07: SQLite, migration, recovery và realm offline/online](docs/p07/PERSISTENCE.md)
- [P07: garage/shop/account UI](docs/p07/UI.md)
- [P07: nghiệm thu browser bản cuối](docs/p07/BROWSER_VALIDATION.md)
- [P06: triển khai, kiểm chứng và gate còn mở](docs/P06_STATUS.md)
- [Kiểm thử browser P06 bản cuối](docs/p06/BROWSER_VALIDATION.md)
- [Video P06 combat/recovery](docs/p06/unity/gameplay-combat-recovery.mp4)
- [Concept P06 và prompt](ArtSource/Concepts/P06/PROMPTS.md)
- [P05, kiểm chứng và gate còn mở](docs/P05_STATUS.md)
- [Kiểm thử browser P05](docs/p05/BROWSER_VALIDATION.md)
- [Asset gậy và QA](docs/p04/club/ASSET.md)
- [Triển khai P03/P04 và gate còn mở](docs/P03_P04_STATUS.md)
- [Nghiệm thu browser P03/P04](docs/p03p04/BROWSER_VALIDATION.md)
- [Video combat/recovery](docs/p03p04/unity/gameplay-combat-recovery.mp4)
- [Assets mới và QA](docs/p03/assets/ASSET_PACK.md)
- [Concept2D và prompt thực tế](ArtSource/Concepts/P03P04/PROMPTS.md)

- [Trạng thái P01/P02 và các gate còn mở](docs/P01_P02_STATUS.md)
- [Kiểm chứng Unity browser WS/WSS](docs/p02/BROWSER_VALIDATION.md)
- [Backend tests/transport/packaging](docs/p02/backend/README.md)
- [Blender MCP setup và authoring](tools/blender/README.md)

## Bắt đầu đọc

- [Báo cáo reverse và các gap](docs/REVERSE_ENGINEERING_REPORT.md)
- [Kế hoạch từng phase, deliverable và gate](docs/PHASE_PLAN.md)
- [Yêu cầu đã chốt và checklist asset](docs/REQUIREMENTS.md)
- [Kiến trúc Unity/Web/Online/LAN/OCI](docs/TECHNICAL_ARCHITECTURE.md)
- [Định hướng UI/UX](docs/UI_UX_DIRECTION.md)
- [Chuẩn kiến trúc và source code](docs/ENGINEERING_STANDARDS.md)

## Hồ sơ kiểm chứng

- [Assets/container/media](docs/reverse-engineering/assets/ASSET_AUDIT.md)
- [Logic/save/network native](docs/reverse-engineering/logic/LOGIC_AUDIT.md)
- [Gameplay video theo timestamp](docs/reverse-engineering/video/GAMEPLAY_REFERENCE.md)
- [Môi trường Unity/Blender MCP](docs/reverse-engineering/ENVIRONMENT_AUDIT.md)

Từ thư mục project chạy `tools\reverse-engineering\verify-audit.bat` để kiểm lại source hashes, member/slice integrity và hồ sơ. Chi tiết tái lập trong [README công cụ](tools/reverse-engineering/README.md).

`docs/reverse-engineering/` và `docs/p01/` chứa tư liệu nghiên cứu. Bulk dumps, ảnh/MIDI trích xuất và runtime-copy giữ local/ignored; không đưa vào Unity Assets, game distribution hoặc lịch sử source production. Tái sinh bằng các tool đã lưu khi có snapshot nguồn. Các tooling audit không phải mẫu architecture để copy vào runtime game.
