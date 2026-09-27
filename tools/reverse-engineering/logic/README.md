# Static logic analysis tooling

Source: `C:\Users\Liquid\Downloads\Unity\racing_bois_mod` (read only).
Output: `D:\Project\Unity\racing-bois\docs\reverse-engineering\logic`.

Các script chỉ phân tích bytes/PE resources/disassembly; không launch game, không import registry, không write nguồn. Assets/data trích xuất chỉ là research reference. Theo yêu cầu, assets production sẽ được làm mới hoàn toàn.

Python 3.13 đã dùng; dependency versions ở `requirements.txt`. Cài local vào thư mục tool để không thay Python environment chung:

```powershell
Set-Location 'D:\Project\Unity\racing-bois'
python -m pip install --target tools/reverse-engineering/logic/vendor -r tools/reverse-engineering/logic/requirements.txt
python tools/reverse-engineering/logic/analyze_pe.py
python tools/reverse-engineering/logic/decode_text_saves.py
python tools/reverse-engineering/logic/decode_logic_tables.py
python tools/reverse-engineering/logic/export_function_evidence.py
python tools/reverse-engineering/logic/verify_evidence.py
```

Paths đang hard-code có chủ đích để tái lập audit đúng source. Muốn phân tích bản khác, sửa ROOT/OUT và fingerprint expectations trong một bản copy tool riêng, không âm thầm dùng byte offsets từ bản hiện tại cho binary khác.

- `analyze_pe.py`: inventory PE, strings (ASCII/UTF16), direct xrefs, linear disassembly. Không phải decompiler. Linear sweep sẽ gặp data/jump tables; targeted evidence mới được dùng cho kết luận code.
- `decode_text_saves.py`: RT_STRING chính xác theo resource ID, raw saves.
- `decode_logic_tables.py`: checksum phục hồi, validate saves, decode mapping giá/tên xe/profile defaults; không sửa saves.
- `export_function_evidence.py`: slices theo địa chỉ đã audit, file offsets và hashes.
- `verify_evidence.py`: kiểm chứng source fingerprint, slice hashes, mọi save/checksum và số localization; ghi verification.json.

`vendor/` là Python dependencies tải từ package registry, không thuộc original game hay production Unity assets. Không cần commit thư mục này.
