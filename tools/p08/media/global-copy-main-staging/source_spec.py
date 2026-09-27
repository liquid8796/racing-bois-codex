"""Frozen semantic display templates for the first global-copy boundary; no live writes."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCES = [
 'Assets/RacingBois/UI/Race.uxml',
 'Assets/RacingBois/Client/Presentation/RaceScreen.cs',
 'Assets/RacingBois/Client/Presentation/RaceScreen.Content.cs',
 'Assets/RacingBois/Client/Presentation/DesktopDisplaySettings.cs',
 'Assets/RacingBois/Client/Presentation/CareerView.cs',
]
# English is an authored fallback/translation aid; Vietnamese is the exact current display-copy source.
# Parameter values retain existing caller formatting and user/catalog data. No names are translated by value.
ROWS = [
 ('common.done', 'XONG', 'DONE'),
 ('common.cancel', 'HỦY', 'CANCEL'),
 ('common.confirm', 'XÁC NHẬN', 'CONFIRM'),
 ('common.refresh', 'LÀM MỚI', 'REFRESH'),
 ('common.retry', 'THỬ LẠI', 'RETRY'),
 ('common.backMenu', 'VỀ MENU', 'BACK TO MENU'),
 ('menu.careerOpen', 'GARAGE / HỒ SƠ', 'GARAGE / PROFILE'),
 ('menu.galleryOpen', 'CÂU CHUYỆN', 'STORIES'),
 ('settings.open', 'CÀI ĐẶT', 'SETTINGS'),
 ('menu.offlinePractice', 'LUYỆN TẬP OFFLINE', 'OFFLINE PRACTICE'),
 ('menu.raceStart', 'VÀO CUỘC ĐUA', 'START RACE'),
 ('menu.practiceChoose', 'CHỌN TUYẾN / XE', 'CHOOSE ROUTE / BIKE'),
 ('menu.networkOpen', 'ONLINE / LAN', 'ONLINE / LAN'),
 ('menu.networkClose', 'ĐÓNG KẾT NỐI', 'CLOSE CONNECTION PANEL'),
 ('menu.playerNameLabel', 'TÊN TAY ĐUA', 'RIDER NAME'),
 ('menu.endpointLabel', 'ĐỊA CHỈ MÁY CHỦ ONLINE / LAN', 'ONLINE / LAN SERVER ADDRESS'),
 ('menu.connectSaved', 'HỒ SƠ ĐÃ LƯU', 'SAVED PROFILE'),
 ('menu.connectGuest', 'KHÁCH MỚI', 'NEW GUEST'),
 ('menu.connect', 'KẾT NỐI', 'CONNECT'),
 ('menu.connecting', 'ĐANG KẾT NỐI...', 'CONNECTING...'),
 ('menu.practiceDisclaimer', 'Kết quả luyện tập không cộng vào hồ sơ máy chủ.', 'Practice results do not count toward your server profile.'),
 ('menu.profileHelp', 'Hồ sơ lưu trên máy chủ; Khách mới tạo một người chơi riêng.', 'Profiles are saved on the server; New guest creates a separate player.'),
 ('menu.level', 'CẤP {level} /', 'LEVEL {level} /'),
 ('connection.ready', 'SẴN SÀNG LÊN ĐƯỜNG', 'READY TO RIDE'),
 ('connection.connecting', 'ĐANG KẾT NỐI', 'CONNECTING'),
 ('connection.reconnecting', 'ĐANG KẾT NỐI LẠI', 'RECONNECTING'),
 ('connection.onlineLan', 'ONLINE / LAN', 'ONLINE / LAN'),
 ('connection.latency', 'ONLINE / {milliseconds} MS', 'ONLINE / {milliseconds} MS'),
 ('connection.highLatency', 'ĐỘ TRỄ CAO / {milliseconds} MS', 'HIGH LATENCY / {milliseconds} MS'),
 ('connection.local', 'CHƠI ĐƠN / OFFLINE', 'SOLO / OFFLINE'),
 ('connection.server', 'ĐÃ KẾT NỐI MÁY CHỦ', 'CONNECTED TO SERVER'),
 ('hud.positionLabel', 'VỊ TRÍ', 'POSITION'),
 ('hud.riderLabel', 'TAY ĐUA', 'RIDER'),
 ('hud.bikeLabel', 'XE', 'BIKE'),
 ('hud.weapon.club', 'GẬY', 'CLUB'),
 ('hud.weapon.chain', 'DÂY XÍCH', 'CHAIN'),
 ('hud.weapon.fist', 'TAY KHÔNG', 'BARE HANDS'),
 ('hud.cruise.on', 'GIỮ GA: BẬT', 'CRUISE: ON'),
 ('hud.cruise.off', 'GIỮ GA: TẮT', 'CRUISE: OFF'),
 ('hud.leave', 'RỜI CUỘC ĐUA', 'LEAVE RACE'),
 ('hud.mode.attacking', 'ĐANG RA ĐÒN', 'ATTACKING'),
 ('hud.mode.hit', 'TRÚNG ĐÒN', 'HIT'),
 ('hud.mode.airborne', 'RỜI MẶT ĐƯỜNG', 'AIRBORNE'),
 ('hud.mode.falling', 'MẤT THĂNG BẰNG', 'LOSING BALANCE'),
 ('hud.mode.detached', 'ĐỨNG DẬY', 'GETTING UP'),
 ('hud.mode.running', 'CHẠY VỀ XE', 'RUNNING TO BIKE'),
 ('hud.mode.remounting', 'LÊN XE', 'REMOUNTING'),
 ('hud.mode.wrecked', 'XE HƯ HỎNG', 'BIKE WRECKED'),
 ('hud.mode.busted', 'BỊ CẢNH SÁT BẮT', 'BUSTED BY POLICE'),
 ('hud.mode.finished', 'ĐÃ VỀ ĐÍCH', 'FINISHED'),
 ('hud.mode.riding', 'ĐANG ĐUA', 'RACING'),
 ('hud.recovery.running', 'Tay đua đang chạy về xe. Cuộc đua vẫn tiếp tục.', 'Your rider is running back to the bike. The race continues.'),
 ('hud.recovery.calm', 'Giữ bình tĩnh. Lấy lại nhịp đua.', 'Stay calm. Find your rhythm again.'),
 ('hud.event.hitOther', 'ĐÁNH TRÚNG', 'HIT LANDED'),
 ('hud.event.gotHit', 'TRÚNG ĐÒN', 'HIT TAKEN'),
 ('hud.event.weaponChanged', 'ĐỔI VŨ KHÍ', 'WEAPON CHANGED'),
 ('hud.event.remounted', 'TRỞ LẠI CUỘC ĐUA', 'BACK IN THE RACE'),
 ('hud.event.landed', 'TIẾP ĐẤT', 'LANDED'),
 ('controls.leftStick', 'CẦN TRÁI', 'LEFT STICK'),
 ('controls.throttleBrake', 'Ga/Phanh', 'Throttle/Brake'),
 ('controls.steer', 'Lái', 'Steer'),
 ('controls.attack', 'Đánh', 'Attack'),
 ('controls.kick', 'Đá', 'Kick'),
 ('results.practiceHeading', 'KẾT QUẢ / LUYỆN TẬP', 'RESULTS / PRACTICE'),
 ('results.qualified', 'VƯỢT QUA CHẶNG.', 'STAGE CLEARED.'),
 ('results.finished', 'VỀ ĐÍCH.', 'FINISHED.'),
 ('results.busted', 'BỊ BẮT.', 'BUSTED.'),
 ('results.wrecked', 'XE HƯ HỎNG.', 'BIKE WRECKED.'),
 ('results.finishDetail', 'Hạng {rank} · {seconds} giây\nThưởng luyện tập trong phiên: ${reward}', 'Rank {rank} · {seconds} seconds\nSession practice reward: ${reward}'),
 ('results.fineDetail', 'Tiền phạt luyện tập trong phiên: ${fine}', 'Session practice fine: ${fine}'),
 ('results.wreckDetail', 'Cuộc đua kết thúc. Thử lại với một đường chạy tốt hơn.', 'The race is over. Try again with a better line.'),
 ('results.practiceFunds', '\nQuỹ luyện tập trong phiên: ${credits}', '\nSession practice funds: ${credits}'),
 ('results.restart', 'ĐUA LẠI  >', 'RACE AGAIN  >'),
 ('settings.eyebrow', 'THEO NHỊP CỦA BẠN', 'AT YOUR PACE'),
 ('settings.title', 'CÀI ĐẶT.', 'SETTINGS.'),
 ('settings.qualityLabel', 'CHẤT LƯỢNG HÌNH ẢNH', 'GRAPHICS QUALITY'),
 ('settings.qualityHelp', 'Mức Vừa dành cho trải nghiệm cân bằng. Giảm chất lượng nếu nhịp hình chưa ổn định.', 'Medium offers a balanced experience. Lower the quality if frame pacing is uneven.'),
 ('settings.quality.low', 'THẤP — ưu tiên tốc độ', 'LOW — prioritize speed'),
 ('settings.quality.medium', 'VỪA — cân bằng', 'MEDIUM — balanced'),
 ('settings.quality.high', 'CAO — chi tiết', 'HIGH — detailed'),
 ('settings.reducedMotion', 'Giảm chuyển động', 'Reduce motion'),
 ('settings.reducedMotionHelp', 'Giảm rung camera và chuyển cảnh; tín hiệu chiến đấu vẫn hiển thị.', 'Reduce camera shake and transitions; combat cues remain visible.'),
 ('settings.audio', 'Bật âm thanh', 'Enable audio'),
 ('settings.hudScale', 'KÍCH THƯỚC HUD  ·  {percent}%', 'HUD SIZE  ·  {percent}%'),
 ('settings.hudRange', '85% — gọn hơn                         115% — dễ đọc hơn', '85% — compact                         115% — easier to read'),
 ('settings.navigationHelp', 'TAB / PHÍM MŨI TÊN hoặc D-PAD để chọn · ENTER / A để xác nhận', 'TAB / ARROW KEYS or D-PAD to navigate · ENTER / A to confirm'),
 ('settings.contextRace', 'Cuộc đua vẫn tiếp tục khi mở cài đặt. Xe ngừng nhận điều khiển.', 'The race continues while settings are open. Bike input is suspended.'),
 ('settings.contextIdle', 'Tinh chỉnh để tìm nhịp đua phù hợp với bạn.', 'Adjust the settings to find your racing rhythm.'),
 ('display.title', 'MÀN HÌNH WINDOWS', 'WINDOWS DISPLAY'),
 ('display.modeLabel', 'CHẾ ĐỘ', 'MODE'),
 ('display.windowed', 'Cửa sổ', 'Windowed'),
 ('display.borderless', 'Toàn màn hình không viền', 'Borderless fullscreen'),
 ('display.exclusive', 'Toàn màn hình độc quyền', 'Exclusive fullscreen'),
 ('display.resolutionLabel', 'ĐỘ PHÂN GIẢI', 'RESOLUTION'),
 ('display.apply', 'ÁP DỤNG MÀN HÌNH', 'APPLY DISPLAY SETTINGS'),
 ('display.help', 'Độ phân giải lấy từ màn hình hiện tại. Chất lượng hình ảnh được chọn riêng.', 'Resolutions come from the current monitor. Graphics quality is selected separately.'),
 ('display.requested', 'Đã yêu cầu {resolution} · {mode}. Windows áp dụng vào cuối frame.', 'Requested {resolution} · {mode}. Windows applies the change at the end of the frame.'),
 ('practice.title', 'CHỌN HÀNH TRÌNH.', 'CHOOSE YOUR RIDE.'),
 ('practice.help', 'Luyện tập tự do với mọi xe và tay đua đã có. Kết quả không cộng vào hồ sơ máy chủ.', 'Practice freely with every available bike and rider. Results do not count toward your server profile.'),
 ('practice.courseLabel', 'TUYẾN ĐƯỜNG', 'ROUTE'),
 ('practice.levelLabel', 'CẤP ĐỘ', 'LEVEL'),
 ('practice.bikeLabel', 'MÔ TÔ', 'MOTORCYCLE'),
 ('practice.riderLabel', 'TAY ĐUA', 'RIDER'),
 ('practice.levelChoice', 'CẤP {level}', 'LEVEL {level}'),
 ('practice.start', 'LÊN ĐƯỜNG  >', 'HIT THE ROAD  >'),
 ('content.heading', 'CHUẨN BỊ HÀNH TRÌNH.', 'PREPARING YOUR RIDE.'),
 ('content.defaultStatus', 'Đang tải nội dung cần dùng…', 'Loading the required content…'),
]

def freeze():
    entries = []
    bindings = json.loads((HERE / 'source-bindings.json').read_text(encoding='utf-8'))['entries']
    for key, vi, enu in ROWS:
        arguments = list(dict.fromkeys(re.findall(r'\{([a-zA-Z][a-zA-Z0-9]*)\}', vi)))
        if set(arguments) != set(re.findall(r'\{([a-zA-Z][a-zA-Z0-9]*)\}', enu)):
            raise ValueError('English placeholder mismatch: ' + key)
        entries.append({'key': key, 'vi': vi, 'enu': enu, 'arguments': arguments, **bindings[key]})
    if len({e['key'] for e in entries}) != len(entries): raise ValueError('Duplicate semantic key')
    data = {'schema': 1, 'boundary': 'main-menu-hud-settings-practice', 'sourceLanguage': 'VI',
            'sourceFiles': [{'path': p, 'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest()} for p in SOURCES], 'entries': entries}
    (HERE / 'canonical-source.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    source_hash = hashlib.sha256((HERE / 'canonical-source.json').read_bytes()).hexdigest()
    for locale, field in [('VI', 'vi'), ('ENU', 'enu')]:
        output = {'schema': 1, 'locale': locale, 'boundary': data['boundary'], 'sourceSha256': source_hash,
                  'strings': {e['key']: e[field] for e in entries}}
        (HERE / 'locales' / (locale + '.json')).write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (HERE / 'translation-source.tsv').write_text(''.join(str(i) + '\t' + e['key'] + '\t' + e['enu'].replace('\n', '\\n') + '\t' + e['vi'].replace('\n', '\\n') + '\n' for i,e in enumerate(entries)), encoding='utf-8')
    (HERE / 'templates-freeze.json').write_text(json.dumps({'schema':1,'canonicalSourceSha256':source_hash,'keyCount':len(entries),
        'sourceBindingsSha256':hashlib.sha256((HERE / 'source-bindings.json').read_bytes()).hexdigest(),'nativeAcceptance':False},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'keys': len(entries), 'sourceSha256': source_hash}))

if __name__ == '__main__': freeze()
