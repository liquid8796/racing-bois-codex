# Asset research tools

Chỉ đọc dữ liệu nguồn. Không chạy EXE/DLL nguồn, không sửa registry, không import vào Unity.
Theo yêu cầu mới của người dùng: toàn bộ assets production phải làm mới; các bản giải mã ở `docs/reverse-engineering/assets` chỉ là tư liệu nghiên cứu.

Chạy từ `D:\Project\Unity\racing-bois` với Python 3 + Pillow và ffprobe/ffmpeg trên PATH:

```powershell
python tools/reverse-engineering/assets/audit_assets.py
python tools/reverse-engineering/assets/inspect_internals.py
python tools/reverse-engineering/assets/decode_bob.py
python tools/reverse-engineering/assets/inspect_mips.py
python tools/reverse-engineering/assets/validate_decoders.py
```

Không dùng `python -O`: kiểm tra biên dữ liệu trong các parser sử dụng assertion. Không dùng parser cho dữ liệu internet không tin cậy mà chưa thêm giới hạn bộ nhớ/CPU bên ngoài.

`audit_assets.py` nhận `--source` và `--output`; các script bổ sung hiện cố định đường dẫn snapshot của dự án này.

- `audit_assets.py`: SHA256 toàn bộ file, phân loại theo magic, bảng CRSR, FAM giải nén và cây offset, sprite DAT, JPEG/BMP, RIFF, font TrueType, metadata media.
- `inspect_internals.py`: RRAN/RRFD frame tables, RIFF/MIDS event blocks và sample headers SoundFont 1.0.
- `decode_bob.py`: ảnh nghiên cứu với dimensions truy từ native loader; ghi rõ cloud còn thiếu.
- `inspect_mips.py`: kiểm tra các record mip PC và TEMPLATE.MIP; ghi vùng cấu trúc chưa hỗ trợ riêng.
- `validate_decoders.py`: vector DCL chuẩn, dữ liệu cắt ngắn/sai biên, giải mã toàn bộ stream của 61 AVI, và xác nhận 374 file nguồn giữ nguyên SHA256.
- `dcl.py`: Python port có giới hạn output của thuật toán PKWARE DCL trong Mark Adler blast.c; đây là phiên bản đã sửa, không phải mã upstream nguyên bản.
- `blast-reference.c`, `blast.h`: upstream zlib v1.3.1, giữ nguyên bản quyền và điều kiện phân phối. Nguồn: https://github.com/madler/zlib/tree/v1.3.1/contrib/blast

Các parser có kiểm tra kết quả hiện tại; chưa phải bộ chuyển đổi asset production. Các field chưa xác định phải giữ là unknown thay vì tự gán nghĩa gameplay.
