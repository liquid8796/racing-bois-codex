# Build, package và integrity verification

Source game cuối: `906593098208af8ba80e48e002ec34aa08ca33f8`. Unity6000.5.7f1, URP17.5.0, Input System1.20.0, WebGL2/IL2CPP, Brotli và filenames theo hash.

## Clean source build

Một thư mục Unity-source độc lập được tạo bằng Git archive của Assets/Packages/ProjectSettings/global.json; không sao chép Library/Temp/Build của project chính. Build cold đầu gặp lỗi nội bộ Bee: `Backend has requested a buildprogram run 6 times`. Log và [receipt thất bại](unity/cold-first-attempt.json) được giữ. Chạy lại đúng source đó hoàn tất với0 errors/0 warnings; không sửa game code để làm mất lỗi.

Sau các sửa review cuối, source đã commit được xuất lại vào cùng thư mục kiểm tra độc lập và build incremental từ cache do chính thư mục đó tạo ra. [Final receipt](unity/final-build.json) ghi `Succeeded`,0 errors,0 warnings. Đây là source/export buildability, không phải khẳng định byte-identical determinism giữa mọi lần build.

Wrapper `tools/foundation/build-web.ps1` chỉ retry một lần cho đúng lỗi Bee trên; lỗi compiler khác không retry, lỗi Bee lặp lại vẫn thất bại. [Ba regression cases](unity/build-wrapper-tests.json) kiểm tra bằng process thật: recover cần2 lần, unrelated failure chỉ1 lần, persistent failure tối đa2 lần. Wrapper chờ Editor process bằng `WaitForExit`, không chờ vô hạn các shared licensing/compiler descendants.

## Gói đã tạo

- `Build/Web-9065930-r2`: payload Web đang phục vụ; `Build/current-web.txt` trỏ tới phiên bản này.
- `Build/LanHost/win-x64-9065930`: executable tự chứa runtime, web payload và `launch-local.bat`/`launch-lan.bat`.
- `Build/LanHost/linux-arm64-9065930`: runtime ARM64 + cùng web payload; chương trình đã chạy `--SelfTest` trên VM được người dùng chỉ định.

Các bản cũ được giữ riêng; không ghi đè hoặc dọn thư mục build đang phục vụ để chuyển phiên bản. `_DoNotShip` không nằm trong hai gói phát hành thử. [Publish manifest](backend/publish-evidence.json) ghi executable/DLL/Web hashes. [Delivery verifier](delivery-verification.json) hash lại từng file Web, đối chiếu hai gói với bản đang phục vụ và kiểm không có file trùng SHA-256 nguồn game trong Unity Assets.

## Phạm vi PASS

- 18 nhóm native/application tests,3 build-wrapper cases, Unity stale-world view check180 lượt không tạo renderer.
- Blender geometry/UV/source QA và Unity prefab/LOD/collider/material/UV2 checks.
- Unity browser thực qua WS/WSS,2 clients, input và authoritative ACK; shared300-tick fixture khớp Windows/Unity Web/OCI ARM64.
- Toàn bộ374 file gốc còn nguyên; không đưa bản trích xuất vào production assets.

P01 full logic parity còn mở. P02 không thay nghiệm thu campaign/combat hoàn chỉnh, LAN mất WAN trên hai máy, global WAN, capacity production hay performance của toàn bộ content cuối.

Lệnh kiểm tra hồ sơ hiện có: `python tools/foundation/verify-delivery.py`. Rebuild source bằng `tools/foundation/build-web.bat` khi Editor của chính thư mục đó đã đóng, hoặc truyền `-ProjectPath` tới checkout riêng.
