"""Build reviewed keyed multiplayer template candidates outside Assets. No locale acceptance."""
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LOBBY = 'Assets/RacingBois/Client/Presentation/MultiplayerLobbyView.cs'
COPY = 'Assets/RacingBois/Client/Presentation/MultiplayerCopy.cs'
UXML = 'Assets/RacingBois/UI/Race.uxml'
entries = {}
source = {path: (ROOT / path).read_text(encoding='utf8') for path in (LOBBY, COPY, UXML)}
candidate = dict(source)


def literal(value):
    return json.dumps(value, ensure_ascii=False)


def entry(key, vi, arguments, file, member, expression, **extra):
    key = 'multiplayer.' + key
    row = entries.setdefault(key, dict(key=key, vi=vi, arguments=arguments, bindings=[]))
    if row['vi'] != vi or row['arguments'] != arguments:
        raise ValueError('Conflicting semantic key: ' + key)
    row['bindings'].append(dict(file=file, member=member, sourceExpression=expression, **extra))
    return key


def replace(key, vi, expression=None, arguments=None, member='MultiplayerLobbyView', locale=None):
    arguments = arguments or {}
    expression = expression if expression is not None else literal(vi)
    if expression not in candidate[LOBBY]:
        raise ValueError('Source expression absent: ' + key + ': ' + expression)
    full = entry(key, vi, list(arguments), LOBBY, member, expression)
    values = ', '.join('new UiTextArgument(' + literal(name) + ', ' + value + ')' for name, value in arguments.items())
    if locale:
        replacement = 'UiText.' + ('Format' if arguments else 'Get') + '(' + locale + ', ' + literal(full) + (', ' + values if values else '') + ')'
    else:
        replacement = ('Format' if arguments else 'Text') + '(' + literal(full) + (', ' + values if values else '') + ')'
    candidate[LOBBY] = candidate[LOBBY].replace(expression, replacement)


# Full dynamic messages keep inserted names, codes, numbers and route titles opaque.
replace('level.current', 'CẤP {level} · HIỆN TẠI', '"CẤP " + (careerLevel + 1) + " · HIỆN TẠI"', {'level': '(careerLevel + 1).ToString()'}, 'SetCareerLevel')
replace('invite.received', 'Đã nhận lời mời {code}. Kết nối và chọn VÀO PHÒNG khi bạn sẵn sàng.', '"Đã nhận lời mời " + code + ". Kết nối và chọn VÀO PHÒNG khi bạn sẵn sàng."', {'code': 'code'}, 'PrefillInvite')
replace('level.mismatch', 'Hồ sơ của bạn đang ở cấp {current}. Phòng vẫn giữ cấp {room}; hãy rời phòng và tạo chặng ở cấp hiện tại.', '"Hồ sơ của bạn đang ở cấp " + (expected + 1) + ". Phòng vẫn giữ cấp " + (session.Room.LevelIndex + 1) + "; hãy rời phòng và tạo chặng ở cấp hiện tại."', {'current': '(expected + 1).ToString()', 'room': '(session.Room.LevelIndex + 1).ToString()'}, 'RoomLevelHint')
replace('seat.waiting', '{seat}   Đang chờ người chơi…', '(i + 1).ToString("00") + "   Đang chờ người chơi…"', {'seat': '(i + 1).ToString("00")'}, 'Render')
replace('room.info', '{players} / {capacity} NGƯỜI · {bots} MÁY\n{course} · CẤP {level}{visibility}', 'room.Members.Count + " / " + room.MaxPlayers + " NGƯỜI · " + room.BotCount + " MÁY\\n" +\n                        CampaignCatalog.GetRoute(room.CourseIndex).DisplayName + " · CẤP " + (room.LevelIndex + 1) + (room.PublicRoom ? " · CÔNG KHAI" : " · RIÊNG TƯ")'.replace('\\n" +\n', '\\n" +\n'), {'players': 'room.Members.Count.ToString()', 'capacity': 'room.MaxPlayers.ToString()', 'bots': 'room.BotCount.ToString()', 'course': 'CampaignCatalog.GetRoute(room.CourseIndex).DisplayName', 'level': '(room.LevelIndex + 1).ToString()', 'visibility': 'Text(room.PublicRoom ? "multiplayer.room.public" : "multiplayer.room.private")'}, 'Render')
replace('invite.code', 'Mã phòng: {code}', '"Mã phòng: "+room.Code', {'code': 'room.Code'}, 'Render')
replace('countdown', 'XUẤT PHÁT SAU {seconds}', '"XUẤT PHÁT SAU " + seconds', {'seconds': 'seconds.ToString()'}, 'Render')
replace('result.finished', 'HẠNG {rank} · {seconds}s', '"HẠNG " + entry.Rank + " · " + (entry.FinishTick / 60f).ToString("0.0") + "s"', {'rank': 'entry.Rank.ToString()', 'seconds': '(entry.FinishTick / 60f).ToString("0.0")'}, 'Render')
replace('result.wallet', '{reward} · QUỸ ${credits}', '(entry.Reward >= 0 ? "+" : "") + "$" + entry.Reward + " · QUỸ $" + entry.Credits', {'reward': '(entry.Reward >= 0 ? "+" : "") + "$" + entry.Reward', 'credits': 'entry.Credits.ToString()'}, 'Render')
replace('room.summary', '{players} / {capacity} · CẤP {level}', 'entry.Players + " / " + entry.MaxPlayers + " · CẤP " + (entry.LevelIndex + 1)', {'players': 'entry.Players.ToString()', 'capacity': 'entry.MaxPlayers.ToString()', 'level': '(entry.LevelIndex + 1).ToString()'}, 'RoomRow.Bind', 'locale')

static = {
    'validation.code': 'Mã phòng gồm 6 ký tự. Hãy kiểm tra lại mã bạn nhận được.',
    'validation.create': 'Chọn một tuyến đã mở và đặt tên phòng trước khi tiếp tục.',
    'validation.route': 'Tuyến này chưa sẵn sàng.',
    'level.guest': 'Phiên khách chỉ đua ở cấp 1. Rời phòng này rồi tạo hoặc vào phòng cấp 1.',
    'content.incomplete': 'Nội dung đường đua chưa tải xong.',
    'title.saving': 'ĐANG LƯU KẾT QUẢ', 'title.suspended': 'TẠM DỪNG KẾT NỐI',
    'title.reconnecting': 'ĐANG KẾT NỐI LẠI', 'title.connecting': 'ĐANG KẾT NỐI',
    'title.results': 'CHẶNG ĐUA KHÉP LẠI.', 'title.browser': 'CÙNG LÊN ĐƯỜNG.',
    'message.saving': 'Máy chủ đang xác nhận lưu điểm và phần thưởng. Vui lòng giữ kết nối.',
    'message.reconnecting': 'Chỗ của bạn được giữ trong thời gian kết nối lại. Về menu để kết thúc phiên.',
    'message.results': 'Kết quả chính thức của phòng. Cùng trở về phòng chờ để bắt đầu chặng mới.',
    'message.browser': 'Tạo cuộc đua của riêng bạn hoặc nhập mã để cùng bạn bè lên đường.',
    'message.room': 'Mã phòng ở bên dưới. Mời bạn bè, chọn sẵn sàng và chờ chủ phòng xuất phát.',
    'member.you': ' · BẠN', 'member.host': ' · CHỦ PHÒNG', 'member.guest': 'KHÁCH',
    'member.saved': 'HỒ SƠ ĐÃ LƯU', 'member.held': 'GIỮ CHỖ', 'ready': 'SẴN SÀNG',
    'member.not-ready': 'CHƯA SẴN SÀNG', 'seat.empty': 'CHỖ TRỐNG', 'ready.cancel': 'HỦY SẴN SÀNG',
    'hint.countdown': 'Các tay đua đã sẵn sàng. Giữ nhịp, cuộc đua sắp bắt đầu.',
    'hint.not-ready': 'Bạn chưa sẵn sàng. Nhấn SẴN SÀNG để tham gia xuất phát.',
    'hint.waiting': 'Đã sẵn sàng. Đang chờ những tay đua còn lại.',
    'hint.host': 'Tất cả đã sẵn sàng. Bạn có thể bắt đầu cuộc đua.',
    'hint.members': 'Tất cả đã sẵn sàng. Đang chờ chủ phòng xuất phát.',
    'content.preparing': 'Đang chuẩn bị nội dung đường đua…', 'rematch': 'VỀ PHÒNG CHỜ',
    'rematch.waiting': 'CHỜ CHỦ PHÒNG', 'result.receiving': 'Đang nhận kết quả chính thức từ máy chủ…',
    'result.saved': 'ĐÃ LƯU KẾT QUẢ · Thưởng của phiên khách chỉ áp dụng trong phiên này.',
    'result.pending': 'ĐANG CHỜ XÁC NHẬN LƯU · Chưa xác nhận phần thưởng vào hồ sơ.',
    'result.busted': 'BỊ BẮT', 'result.wrecked': 'HỎNG XE', 'result.incomplete': 'KHÔNG HOÀN THÀNH',
}
for key, vi in static.items():
    replace(key, vi)
for key, vi in [('room.racing', 'ĐANG ĐUA'), ('room.full', 'ĐÃ ĐỦ NGƯỜI'), ('join', 'VÀO PHÒNG')]:
    replace(key, vi, locale='locale', member='RoomRow.Bind')
for key, vi in [('room.public', ' · CÔNG KHAI'), ('room.private', ' · RIÊNG TƯ')]:
    entry(key, vi, [], LOBBY, 'Render visibility argument', literal(vi))

# Protocol/application errors stay raw. Only this presentation mapping is localized.
pattern = re.compile(r'((?:(?:case "[^"]+":)\s*)+|default:)\s*return ("[^"\n]*");')
def error_match(match):
    codes = re.findall(r'case "([^"]+)"', match.group(1))
    vi = json.loads(match.group(2))
    key = entry('error.' + (codes[0].replace('_', '-') if codes else 'unknown'), vi, [], COPY, 'MultiplayerCopy.Error', match.group(2), serverCodes=codes)
    return match.group(1) + ' return UiText.Get(locale, ' + literal(key) + ');'
candidate[COPY], error_count = pattern.subn(error_match, candidate[COPY])
if error_count != 28:
    raise ValueError('Unexpected server error mapping count: ' + str(error_count))
candidate[COPY] = 'using RacingBois.Client.Application;\n\n' + candidate[COPY]
candidate[COPY] = candidate[COPY].replace('Error(string message)', 'Error(string message, string locale = DisplayLanguage.Default)')
candidate[COPY] = candidate[COPY].replace('))return message;', '))return UiText.ClientMessage(locale,message);')
assert 'const string prefix="Máy chủ từ chối: ";' in candidate[COPY]

# Presentation wiring only. Explicit error templates retain their key/arguments across locale changes;
# externally supplied errors stay raw until the dedicated display boundary classifies them.
def edit(before, after):
    if candidate[LOBBY].count(before) != 1:
        raise ValueError('Wiring anchor must be unique: ' + before)
    candidate[LOBBY] = candidate[LOBBY].replace(before, after)

edit('        private string localError = "";', '''        public string Locale { get; private set; } = DisplayLanguage.Default;
        private string localError = "", localErrorKey = "";
        private UiTextArgument[] localErrorArguments = Array.Empty<UiTextArgument>();''')
edit('        public void ShowError(string text) { localError = text; localErrorUntil = Time.unscaledTime + 6; }', '''        public void ShowError(string text) { localError = text; localErrorKey = ""; localErrorArguments = Array.Empty<UiTextArgument>(); localErrorUntil = Time.unscaledTime + 6; }
        private void ShowErrorKey(string key, params UiTextArgument[] arguments)
        { localError = ""; localErrorKey = key; localErrorArguments = arguments; localErrorUntil = Time.unscaledTime + 6; }
        private string Text(string key) => UiText.Get(Locale, key);
        private string Format(string key, params UiTextArgument[] arguments) => UiText.Format(Locale, key, arguments);
        public void SetLocale(string locale)
        {
            string next = DisplayLanguage.Normalize(locale); if (next == Locale) return; Locale = next;
            if (root == null) return;
            renderedRoom = null; renderedRooms = null; renderedResult = null; previousCountdown = -1;
            SetCareerLevel(careerLevel);
            if (currentSession != null) Render(currentSession);
        }
        private void ShowRoomLevelError(MultiplayerSession session)
        {
            if (session.IsGuest) ShowErrorKey("multiplayer.level.guest");
            else ShowErrorKey("multiplayer.level.mismatch", new UiTextArgument("current", (careerLevel + 1).ToString()), new UiTextArgument("room", (session.Room.LevelIndex + 1).ToString()));
        }''')
edit('public void Initialize(UIDocument document)', 'public void Initialize(UIDocument document, string locale = null)')
edit('            if (root != null) return;\n            surface = document.rootVisualElement;', '            if (root != null) return;\n            if (locale != null) Locale = DisplayLanguage.Normalize(locale);\n            surface = document.rootVisualElement;')
edit('ShowError(Format("multiplayer.invite.received", new UiTextArgument("code", code)))', 'ShowErrorKey("multiplayer.invite.received", new UiTextArgument("code", code))')
for key in ('validation.code', 'validation.create', 'validation.route'):
    edit('ShowError(Text("multiplayer.' + key + '"))', 'ShowErrorKey("multiplayer.' + key + '")')
edit('ShowError(RoomLevelHint(session))', 'ShowRoomLevelError(session)')
edit('ShowError(string.IsNullOrEmpty(contentStatus) ? Text("multiplayer.content.incomplete") : contentStatus);', 'if (string.IsNullOrEmpty(contentStatus)) ShowErrorKey("multiplayer.content.incomplete"); else ShowError(contentStatus);')
edit('Time.unscaledTime < localErrorUntil ? localError :', 'Time.unscaledTime < localErrorUntil ? (localErrorKey.Length > 0 ? Format(localErrorKey, localErrorArguments) : MultiplayerCopy.Error(localError, Locale)) :')
edit('MultiplayerCopy.Error(session.Error)', 'MultiplayerCopy.Error(session.Error, Locale)')
edit('Text("multiplayer.content.preparing") : contentStatus', 'Text("multiplayer.content.preparing") : UiText.ClientMessage(Locale, contentStatus)')
edit('roomPool[i].Bind(renderedRooms[i]);', 'roomPool[i].Bind(renderedRooms[i], Locale);')
edit('public void Bind(LobbySummaryReadModel entry)', 'public void Bind(LobbySummaryReadModel entry, string locale)')

# The shared UXML owner applies named target additions; this script never edits Race.uxml.
xml_root = ET.fromstring(source[UXML]); panel = next(node for node in xml_root.iter() if node.attrib.get('name') == 'multiplayer')
uxml_bindings = []
roles = {
    'RACING BOIS / CÙNG LÊN ĐƯỜNG': ('heading.eyebrow', 'mp-copy-eyebrow'),
    'PHÒNG ĐUA': ('heading.initial-title', 'mp-title'),
    'VỀ MENU': ('menu.return', 'mp-disconnect'),
    'TẠO PHÒNG': ('browser.create-heading', 'mp-copy-create-heading'),
    'Tên phòng': ('browser.room-name-label', 'mp-copy-room-name-label'),
    'Đối thủ máy': ('browser.bot-label', 'mp-copy-bot-label'),
    'Hiện trong danh sách phòng': ('browser.public-toggle', 'mp-public'),
    'Tuyến đường': ('browser.route-label', 'mp-copy-route-label'),
    'Cấp hiện tại của hồ sơ': ('browser.profile-level-label', 'mp-copy-profile-level-label'),
    'TẠO PHÒNG  >': ('browser.create', 'mp-create'),
    'CÓ MÃ TỪ BẠN BÈ?': ('browser.invite-heading', 'mp-copy-invite-heading'),
    'Nhập 6 ký tự của phòng': ('browser.join-code-hint', 'mp-copy-join-code-hint'),
    'PHÒNG TRÊN MÁY CHỦ': ('browser.room-list-heading', 'mp-copy-room-list-heading'),
    'LÀM MỚI': ('browser.refresh', 'mp-refresh'),
    'Chưa có phòng. Tạo một phòng và gửi mã cho bạn bè.': ('browser.empty-rooms', 'mp-empty'),
    'MÃ MỜI BẠN BÈ': ('room.invite-code-label', 'mp-copy-invite-code-label'),
    'SAO CHÉP LỜI MỜI': ('invite.copy', 'mp-copy-invite'),
    'Chọn và sao chép liên kết này để mời bạn bè.': ('invite.link-hint', 'mp-invite-link'),
    'BẮT ĐẦU': ('start', 'mp-start'),
    'RỜI PHÒNG': ('leave', 'mp-leave'),
}
for index, node in enumerate(panel.iter()):
    for attribute in ('text', 'label', 'tooltip'):
        value = node.attrib.get(attribute)
        if not value:
            continue
        existing = next((row['key'] for row in entries.values() if row['vi'] == value and not row['arguments']), None)
        role, proposed_name = roles[value] if not existing else ('', node.attrib.get('name'))
        name = node.attrib.get('name') or proposed_name
        if not name:
            raise ValueError('A display target requires an explicit semantic name: ' + value)
        key = existing or entry(role, value, [], UXML, name + '.' + attribute, value)
        if existing:
            entries[key]['bindings'].append(dict(file=UXML, member=name + '.' + attribute, sourceExpression=value))
        uxml_bindings.append(dict(elementType=node.tag.rsplit('}', 1)[-1], existingName=node.attrib.get('name'), suggestedName=name,
                                  attribute=attribute, key=key, vi=value))

chrome = ['        private void ApplyLocalizedChrome()', '        {']
for binding in uxml_bindings:
    name = literal(binding['suggestedName']); key = literal(binding['key'])
    if binding['attribute'] == 'tooltip':
        chrome.append('            root.Q<VisualElement>(' + name + ').tooltip = Text(' + key + ');')
    elif binding['elementType'] == 'Toggle':
        chrome.append('            root.Q<Toggle>(' + name + ').text = Text(' + key + ');')
    elif binding['attribute'] == 'text':
        chrome.append('            UiViewState.Text(root.Q<TextElement>(' + name + '), Text(' + key + '));')
    else:
        raise ValueError('Unsupported display-only UXML binding: ' + repr(binding))
chrome.append('        }')
edit('            if (root == null) return;\n            renderedRoom =', '            if (root == null) return;\n            ApplyLocalizedChrome();\n            renderedRoom =')
edit('            foreach (var panel in new[] { root, browser, roomPanel, resultsPanel }) panel.style.display = DisplayStyle.None;',
     '            foreach (var panel in new[] { root, browser, roomPanel, resultsPanel }) panel.style.display = DisplayStyle.None;\n            ApplyLocalizedChrome();')
edit('        private void JoinCode()', '\n'.join(chrome) + '\n\n        private void JoinCode()')

for path in (LOBBY, COPY):
    (HERE / Path(path).name).write_text(candidate[path], encoding='utf8', newline='\r\n' if b'\r\n' in (ROOT / path).read_bytes() else '\n')
document = dict(schema=1, scope='Canonical Vietnamese semantic templates and source bindings only; no multilingual or rendered acceptance.',
                fileHashes={path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in source},
                entries=list(entries.values()), fiveLocaleTranslationsComplete=False, visualAccepted=False)
(HERE / 'canonical-source.json').write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
(HERE / 'uxml-bindings.json').write_text(json.dumps(dict(schema=1, owner='shared main stage; do not edit Race.uxml from this module', bindings=uxml_bindings), ensure_ascii=False, indent=2) + '\n', encoding='utf8')
(HERE / 'worksheet.tsv').write_text('key\targuments\tvi\n' + ''.join(row['key'] + '\t' + ','.join(row['arguments']) + '\t' + row['vi'].replace('\n', '\\n') + '\n' for row in entries.values()), encoding='utf8')
(HERE / 'source-lines.tsv').write_text(''.join(str(index) + '\t' + row['key'] + '\t' + row['vi'].replace('\n', '\\n') + '\n' for index, row in enumerate(entries.values())), encoding='utf8')
print(json.dumps(dict(keys=len(entries), serverErrorMappings=error_count, uxmlBindings=len(uxml_bindings), productionModified=False)))
