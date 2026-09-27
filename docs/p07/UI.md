# P07 — Garage, hành trình và tài khoản

P07 nối UI Toolkit hiện có với API career của máy chủ. Nút **GARAGE / HỒ SƠ** dùng được từ menu và lobby; panel đóng trong lúc đua. Tông graphite/amber, font Noto Sans, focus viền sáng và control tối thiểu 44 px nối tiếp P06. UI không tạo thêm asset 3D nên không phát sinh bước concept mới.

## Các luồng đã triển khai

- **Garage:** xe sở hữu, chiếc đang chọn, tình trạng, giá đổi và giá sửa; chọn/sửa sau xác nhận máy chủ. Nút đổi và sửa bị khóa khi đang ở phòng. Nếu tất cả xe hỏng và không đủ sửa chiếc rẻ nhất, nút bắt đầu lại yêu cầu xác nhận mất garage/tiến trình, nhận Spark 450 nguyên vẹn và quỹ $0; tài khoản/ledger vẫn giữ. Máy chủ quyết định đủ điều kiện và ghi reset idempotent.
- **Cửa hàng:** 15 SKU từ `BikeCatalog`, mua thêm hoặc bán xe đang chọn để đổi mẫu khác, xác nhận chi phí trước giao dịch. UI ghi rõ tất cả hiện dùng chung hình ảnh P06 và thông số lái; không quảng bá 15 model hay hiệu năng khác nhau.
- **Hành trình:** 5 cấp × 5 tuyến, trạng thái đã qua/chưa mở/chờ P08. Chỉ Canyon Run có nội dung chơi; các tuyến khác bị khóa. Chỉ chọn chặng ở cấp hiện tại để tạo phòng riêng cho hồ sơ máy chủ; cấp đã qua hiển thị hoàn thành và không tạo phòng đua lại. Tập offline trên menu không cộng thưởng vào hồ sơ này.
- **Giao dịch:** ledger do máy chủ trả về, biến động và số dư. Không thay đổi quỹ lạc quan ở client.
- **Tài khoản:** nâng cấp hồ sơ vô danh đã kết nối, đăng nhập, khôi phục bằng mã một lần, tạo mã khôi phục mới bằng mật khẩu hiện tại, đăng xuất máy này hoặc thu hồi mọi phiên. Không email giả, không lưu mật khẩu/mã vào PlayerPrefs, log hoặc telemetry. Mã mới chỉ nằm trong bộ nhớ panel; đóng panel xóa phần hiển thị.
- **Sao lưu LAN:** xuất/nhập văn bản có chữ ký máy chủ, chỉ trong realm offline. Cần cùng hồ sơ, cùng realm và revision/generation hợp lệ; không cho nhập dữ liệu offline vào online hay hồi lại tiền đã tiêu bằng save cũ. UI yêu cầu xác nhận trước nhập.
- **Lobby:** công khai/riêng tư, chọn cấp Canyon hiện tại, danh sách công khai, mã và liên kết lời mời. `?room=ABC123` chỉ điền mã sáu ký tự ASCII, không tự kết nối hay tự vào phòng. Liên kết ở text field chỉ đọc để sao chép thủ công nếu quyền clipboard trình duyệt không khả dụng.

## Ranh giới và độ tin cậy

`CareerView` chỉ dùng `CareerIntent` và các readmodel bất biến của Client Application. `CareerSession` chuyển intent sang wire DTO, kiểm tra/projection phản hồi, lưu capability theo endpoint qua port hiện hữu. `UnityCareerTransport` dùng UnityWebRequest, TLS của hệ điều hành và không tự vượt kiểm tra chứng chỉ.

Mỗi intent tài chính có UUID dạng D. Một request chạy tại một thời điểm; khi mạng lỗi chưa rõ kết quả, **THỬ LẠI** giữ nguyên ID. Từ chối dứt khoát không retry tự động. Không retry ngầm mật khẩu/mã khôi phục; người chơi nhập lại. API account cần HTTPS, kể cả LAN; career vô danh trong LAN có thể dùng HTTP. Đổi identity đợi WS disconnect trước, lưu token mới và xóa resume lease cũ. Khách mới không được trình bày như hồ sơ garage bền vững. Mỗi WS session mới tự đọc career một lần để chọn đúng cấp; session khách luôn về cấp 1. Nếu capability cũ hết hạn, tab tài khoản cho bỏ khóa cục bộ sau xác nhận mất quyền truy cập hồ sơ vô danh: chỉ xóa credential/resume của endpoint đó sau disconnect, không tác động realm khác; đăng nhập/khôi phục tài khoản vẫn có sẵn.

Panel có trạng thái loading, vô hiệu hóa thao tác trong lúc chờ, thông báo thành công/lỗi kèm bước khắc phục, tab bàn phím, Escape quay lại/đóng, focus giữ trong modal. Nội dung danh mục, tài khoản và thành viên phòng cuộn theo chiều dọc ở viewport thấp. Header, thông tin quỹ, tab, xác nhận và footer không bị flex-shrink; body/scroll nhận phần chiều cao còn lại với flex-basis 0 và min-height 0, tránh danh sách dài đẩy chồng các vùng. Nút bị khóa có màu chữ/nền/viền riêng; đổi xe cần chiếc đang chọn còn chạy được và phép cộng quỹ/giá đổi dùng số nguyên 64-bit. Các thao tác tiền/sao lưu/thu hồi được xác nhận ngay trong panel.

## Kiểm thử

Chạy `dotnet run --project src/Tests/RacingBois.P07Client.Tests -c Release` để tạo [client-validation.json](client-validation.json). 19 test tập trung vào authority/retry/identity: không tự trừ tiền, chống double submit, retry cùng ID, idempotency boundary, credential theo endpoint, phản hồi cũ khi đổi endpoint, xóa lease khi đổi identity, HTTPS password policy, secret lifetime, import đi qua server, projection tách wire DTO và từ chối garage bất hợp lệ.

Đây là bằng chứng tầng Application. Kết quả Unity compile, hình ảnh thực tế, browser HTTPS/WSS, clipboard và luồng tài khoản end-to-end được ghi riêng trong hồ sơ nghiệm thu P07; tài liệu này không thay thế nghiệm thu đó.

UI/UX áp dụng `ui-ux-pro-max`: truy vấn `form authentication recovery feedback` trả về Error Recovery, Submit Feedback và Accessible Authentication. Đã dùng phản hồi submit rõ ràng, bước khắc phục, cho phép dán mật khẩu/mã, focus nhìn thấy và giữ hướng thiết kế P06.
