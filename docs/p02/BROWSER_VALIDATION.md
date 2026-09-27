# P02 — Unity Web / WS / WSS validation

Ngày thực hiện: 2026-09-21. Client là Unity 6000.5.7f1 WebGL2/IL2CPP thật, không phải HTML mô phỏng scene.

## Đã xác minh trực tiếp

- Web build tải qua HTTP từ host local; loader đọc Brotli `.data`, `.framework.js`, `.wasm` thành công.
- Nhấn nút UI trong browser tạo kết nối WS, server cấp player ID, tick và ACK tăng liên tục.
- Input bàn phím đi qua browser → Unity Input System → command → authority → snapshot. Ví dụ pulse throttle tạo speed `0.375 m/s`, distance `0.016 m`, ACK 4349; đây là fixture movement mới của P02, không phải vật lý Road Rash đã port.
- Sau khi người dùng **tự xác nhận** dev certificate localhost, browser mở `https://localhost:7778/` và Unity kết nối `wss://localhost:7778/ws` thành công. Không bỏ qua kiểm tra certificate trong browser.
- WSS sample: `Connected`, player `p1`, tick 8298, ACK 2873, inputs 2876. Sau pulse throttle: distance `0.090 m`, ACK 4050; không có browser Console error/warning trong lần chạy đã kiểm tra sau fix stripping.
- Hai Unity browser tabs kết nối thật đồng thời: tab thứ hai hiển thị `Connected · 2/8 riders`, tick 48630. Đây là hai client trong cùng máy, không thay kiểm tra LAN nhiều máy hoặc Internet nhiều quốc gia.
- Fixture shared C# 300 ticks full throttle cho `150500 mm`, `60000 mm/s` ở native Windows, native OCI ARM64 và Unity Web (`sharedFixture=true`). Chỉ xác minh fixture này, không chứng minh mọi phép toán/collision đa nền tảng.

## Lỗi đã phát hiện và sửa

1. Font mặc định mất ký tự tiếng Việt trên Web dù Editor hiển thị được. Bổ sung Noto Sans có OFL, atlas SDF và nguồn font cho dynamic population; đã quan sát dấu tiếng Việt hiện đúng trong browser.
2. `CreatePrimitive(Cylinder/Capsule)` báo thiếu `CapsuleCollider` sau IL2CPP stripping. Bổ sung preserve rule giới hạn đúng type; browser Console sau sửa không còn lỗi này.
3. Native/client lifecycle được review độc lập: chặn welcome muộn, use-after-dispose, snapshot/ACK không hợp lệ và sửa cùng rounding với server. Các tests mới đều PASS.
4. Đợt input hợp lệ dồn sau stream stall 900 ms làm rate limiter cũ disconnect. Token bucket hữu hạn khắc phục và flood vẫn bị ngắt; xem [transport ADR](backend/ADR_TRANSPORT.md).
5. Ký tự mũi tên ngoài font và khoảng cách panel ở viewport thấp được thay/sửa trong source cuối. Bản cuối đã được quan sát lại trong browser: chữ tiếng Việt, nút và dòng hướng dẫn đều hiển thị đầy đủ.
6. Presentation đã tách khỏi wire DTO bằng immutable Application readmodel. Stale world khi disconnected không tạo lại/destroy rider mỗi frame; bài kiểm tra Unity 180 lượt render ghi nhận0 renderer được tạo.

Source cuối: `906593098208af8ba80e48e002ec34aa08ca33f8`. Web payload ở `Build/Web-9065930-r2`, chạy từ self-contained Windows host; xem [final-build.json](unity/final-build.json) và [publish-evidence.json](backend/publish-evidence.json). Build độc lập PASS,0 errors/0 warnings. Source/export buildability đã được kiểm; byte-identical build reproducibility chưa được khẳng định.

## Giới hạn của nghiệm thu này

Số FPS hiển thị là rolling frame-rate trong scene nền tảng nhỏ trên máy hiện tại, không phải benchmark p95/p99 hoặc chứng nhận hiệu năng toàn game. Chưa nghiệm thu 8 người trong 8 browser độc lập, cold-cache LAN với WAN tắt trên hai máy, packet loss ở kernel, Internet liên vùng, gameplay/combat đầy đủ hoặc reconnect có session persistence.

Protocol v1 prediction là phép thử: ACK biểu thị intent mới nhất được server lấy mẫu, chưa có timeline tick/remainder hoàn chỉnh cho reconciliation. Phần này được giữ sau adapter/application boundary để hoàn thiện ở P05.

Ảnh thử đầu có lỗi font/stripping không được dùng làm ảnh chứng nhận bản cuối. Xem báo cáo P02 tổng hợp và build receipts để xác định chính xác revision được kiểm tra.
