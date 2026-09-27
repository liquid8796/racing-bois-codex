# Racing Bois — Reproducible research tooling

Các script đọc bản mod/video local và ghi vào `docs/reverse-engineering/`. Không chạy game, launcher, batch của mod hoặc import registry. Không sửa original. Không chứa game production code và không đưa research assets vào Unity.

## Kiểm tra nhanh bộ hồ sơ hiện có

Chạy từ bất kỳ thư mục nào:

```bat
"D:\Project\Unity\racing-bois\tools\reverse-engineering\verify-audit.bat"
```

Hoặc `python tools/reverse-engineering/verify_audit.py` từ project root. Công cụ tổng hợp chỉ cần Python standard library. Nó hash lại 374 file nguồn và video ~974 MB, so đường dẫn/kích thước/counter, hash từng CRSR member và code slice, kiểm validation receipts, frame paths và link tài liệu. Kết quả ghi `docs/reverse-engineering/verification-summary.json`; exit 0 là PASS, 1 là kiểm tra thất bại. Thiếu input/artifact gây lỗi, không tự bỏ qua.

`--source` / `--video` dùng khi di chuyển cùng snapshot sang vị trí khác. Một số evidence ảnh và công cụ chuyên sâu đang dùng path tuyệt đối theo máy hiện tại; di chuyển toàn workspace cần tái sinh evidence. Không áp địa chỉ mã của audit này cho executable khác.

PASS chỉ xác nhận integrity/consistency của phần đã khảo sát. Nó không xác minh 100% game logic, các semantic chưa biết, gameplay dynamics, Unity build, đồ họa hay FPS.

## Tái lập phân tích chuyên sâu

1. [Asset tools](assets/README.md): Pillow, ffprobe/ffmpeg, CRSR/FAM/DAT/RIFF/parser và media validation. Chạy audit → internals → validate. Không chạy Python với `-O` vì parser dùng assertion để kiểm dữ liệu.
2. [Logic tools](logic/README.md): pefile/capstone được pin trong requirements, PE/resources/disassembly, bảng/save, vùng mã và verifier.
3. [Video report](../../docs/reverse-engineering/video/GAMEPLAY_REFERENCE.md): script `video/sample_reference.py`, Python/Pillow/ffmpeg và skill watch local; đường dẫn watch được ghi trong script. Không dùng Whisper/API.

Các source Python audit là công cụ khảo sát một snapshot, không phải ví dụ architecture chuẩn để copy vào game. Source production mới sẽ theo `docs/ENGINEERING_STANDARDS.md`.

Các dependency local trong `logic/vendor/` chỉ phục vụ audit; có thể tái cài từ requirements. Không cần đưa vendor/cache/samples nghiên cứu vào Unity hoặc production build. Không khởi tạo repo/push từ đợt khảo sát này.
