"""Author complete VI templates at reviewed source spans; never replace fragments globally."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
STAGE = Path(__file__).resolve().parent
SOURCE = 'Assets/RacingBois/Client/Presentation/CareerView.cs'
EXPECTED_SOURCE = '51ee1179cf071ddc973a671321d5325d4bf57353a84262368a0d6803b500b819'
INVENTORY = ROOT/'_local/ui-copy-inventory/reviewed.json'

STATIC_KEYS = {
2592:'tabs.garage',2618:'tabs.shop',2652:'tabs.characters',2683:'tabs.campaign',2727:'tabs.ledger',2759:'tabs.account',
2818:'common.done',2943:'summary.connectToSave',3542:'common.confirm',3745:'common.cancel',4010:'common.refresh',4100:'common.retry',
6165:'status.awaitingConfirmation',11406:'profile.requiredTitle',11496:'profile.storageHint',11651:'profile.connect',11762:'account.openLogin',
12456:'garage.ownedHeading',13136:'garage.empty',14301:'garage.thumbnailPending',15230:'garage.conditionHeading',15776:'garage.previewHint',
17567:'garage.bankruptNotice',17673:'garage.restart',17713:'garage.restartConfirm',18294:'shop.compareHint',19009:'garage.empty',
22890:'shop.trade',23613:'bike.preview',24813:'characters.heading',24900:'characters.selectionHint',25285:'characters.expressionLabel',
25320:'characters.expressionNeutral',25335:'characters.expressionHappy',25345:'characters.expressionFocused',27226:'characters.portraitPending',
27905:'characters.inspect',28206:'characters.leaveRoom',28339:'characters.connectProfile',29474:'campaign.heading',29547:'campaign.progressionHint',
30857:'campaign.leaveRoom',30993:'campaign.complete',31173:'ledger.heading',31247:'ledger.authorityHint',31423:'ledger.empty',
32255:'account.heading',32341:'account.securityHint',32615:'account.newRecoveryNotice',32729:'account.recoveryCodeLabel',33040:'account.usernameLabel',
33312:'account.passwordLabel',33464:'account.recoveryInputLabel',33652:'account.login',33759:'account.register',33982:'account.recover',
34116:'account.pasteHint',34302:'account.connectToRegister',34565:'account.expiredCredentialHint',34729:'account.forgetCredential',
34768:'account.forgetCredentialConfirm',35209:'account.logout',35244:'account.logoutConfirm',35409:'account.logoutAll',35447:'account.logoutAllConfirm',
35680:'account.rotateRecovery',35841:'backup.onlineRestriction',35988:'backup.heading',36066:'backup.privacyHint',36265:'backup.contentLabel',
36515:'backup.export',36635:'backup.import',36808:'backup.importConfirm',39166:'notice.buy',39213:'notice.trade',39249:'notice.repair',
39314:'notice.equip',39368:'notice.character',39427:'notice.register',39492:'notice.login',39564:'notice.rotateRecovery',39651:'notice.recover',
39737:'notice.logout',39810:'notice.forget',39950:'notice.restart',40049:'notice.import',40113:'notice.export',40188:'notice.default',
40380:'ledger.reasonBuy',40411:'ledger.reasonTrade',40443:'ledger.reasonRepair',40493:'ledger.reasonRace',40565:'ledger.reasonRestart',
40639:'ledger.reasonOpening',41267:'error.authRequired',41374:'error.httpsRequired',41491:'error.networkUnavailable',41620:'error.invalidUsername',
41762:'error.invalidPassword',41887:'error.notBankrupt',42024:'error.repairRequired',42125:'error.invalidSave',42252:'error.foreignSave',
42367:'error.staleSave',42481:'error.alreadyOwned',42576:'error.rateLimited',42683:'error.insufficientCredits',42821:'error.invalidCredentials',
42953:'error.usernameUnavailable',43085:'error.profileBusy',43183:'error.storageUnavailable',
}

raw = (ROOT/SOURCE).read_bytes()
if hashlib.sha256(raw).hexdigest() != EXPECTED_SOURCE:
    raise RuntimeError('Career source changed; review its new inventory before modifying templates.')
source = raw.decode('utf-8-sig')
inventory = json.loads(INVENTORY.read_text(encoding='utf-8-sig'))
rows = [row for row in inventory['rows'] if row['file'] == SOURCE]
if len(rows) != 175 or len({row['value'] for row in rows}) != 161:
    raise RuntimeError('Reviewed Career occurrence boundary changed.')
sites = {}
for row in rows:
    if row['sourceSha256'] != EXPECTED_SOURCE:
        raise RuntimeError('Inventory source hash differs.')
    start = row['expressionStart']
    expression = row['expression']
    if source[start:start+len(expression)] != expression:
        raise RuntimeError('Reviewed source expression no longer matches at '+str(start))
    sites.setdefault(start, {'file':SOURCE,'member':row['member'],'line':row['line'],'expressionStart':start,
        'sourceExpression':expression,'composite':row['composite'],'literalOccurrences':[]})['literalOccurrences'].append(row['value'])
if len(sites) != 141 or sum(site['composite'] for site in sites.values()) != 30:
    raise RuntimeError('Reviewed expression boundary changed.')
entries = {}
bindings = {}
external = {}
current = None


def full_key(key):
    return key if key.startswith('common.') else 'career.'+key


def register(key, vi, arguments):
    key = full_key(key)
    record = {'key':key,'vi':vi,'arguments':list(arguments),'bindings':[]}
    collection = external if key.startswith('common.') else entries
    previous = collection.setdefault(key,record)
    if (previous['vi'],previous['arguments']) != (vi,list(arguments)):
        raise RuntimeError('Conflicting semantic key '+key)
    found = re.findall(r'\{([A-Za-z][A-Za-z0-9]*)\}',vi)
    if sorted(found) != sorted(arguments) or len(found) != len(set(found)):
        raise RuntimeError('Template named arguments differ: '+key)
    binding = {'file':SOURCE,'member':sites[current]['member'],'sourceExpression':sites[current]['sourceExpression']}
    if binding not in previous['bindings']:
        previous['bindings'].append(binding)
    bindings.setdefault(current,{'keys':[],'arguments':{}})
    if key not in bindings[current]['keys']:
        bindings[current]['keys'].append(key)
    return key


def T(key,vi):
    key = register(key,vi,[])
    return 'T('+json.dumps(key)+')'


def F(key,vi,**arguments):
    key = register(key,vi,arguments)
    bindings[current]['arguments'][key] = arguments
    return 'F('+json.dumps(key)+', '+', '.join('A('+json.dumps(name)+', '+value+')' for name,value in arguments.items())+')'


def set_rule(start, replacement):
    bindings[start]['replacementExpression'] = replacement


for current,key in STATIC_KEYS.items():
    site = sites[current]
    if site['composite'] or len(site['literalOccurrences']) != 1:
        raise RuntimeError('Expected one reviewed static display literal: '+str(current))
    set_rule(current,T(key,site['literalOccurrences'][0]))

current=8182
empty=T('summary.empty','Kết nối một hồ sơ để bắt đầu hành trình.')
offline=F('summary.offline','{player}   /   ${credits}   /   CẤP {level}   /   HỒ SƠ LAN · TÁCH BIỆT ONLINE',
    player='profile.DisplayName',credits='profile.Credits.ToString("N0")',level='(profile.LevelIndex + 1).ToString()')
realm=F('summary.realm','{player}   /   ${credits}   /   CẤP {level}   /   HỒ SƠ {realm}',
    player='profile.DisplayName',credits='profile.Credits.ToString("N0")',level='(profile.LevelIndex + 1).ToString()',realm='profile.RealmKind.ToUpperInvariant()')
set_rule(current,'profile == null ? '+empty+' : profile.RealmKind == "offline" ? '+offline+' : '+realm)
current=8553;set_rule(current,F('summary.endpoint','MÁY CHỦ  {endpoint}',endpoint='session.Endpoint'))
current=8612;set_rule(current,'session.Busy ? '+T('status.busy','ĐANG XỬ LÝ · Chờ máy chủ xác nhận…')+' : !string.IsNullOrEmpty(session.ErrorCode) ? ErrorText(session.ErrorCode) : SuccessText(session.Notice)')
current=13670;set_rule(current,F('garage.previewTooltip','Xem trước {bike}',bike='bike.DisplayName'))
current=14646;set_rule(current,'bike.Id == profile.SelectedBikeId ? '+T('bike.equipped','ĐANG DÙNG')+' : '+T('bike.owned','ĐÃ SỞ HỮU'))
current=15912;set_rule(current,'inRoom ? '+T('garage.leaveRoom','Rời phòng trước khi đổi hoặc sửa xe.')+' : '+T('profile.guestTransactions','Phiên khách không thực hiện giao dịch hồ sơ.'))
for current in [16208,21679]:
    set_rule(current,'equipped ? '+T('bike.equipped','ĐANG DÙNG')+' : '+T('garage.equip','CHỌN XE'))
current=16650;set_rule(current,'condition == 100 ? '+T('garage.pristine','XE NGUYÊN VẸN')+' : '+F('garage.repairButton','SỬA XE · ${cost}',cost='inspected.RepairCredits.ToString("N0")'))
for current,definition in [(16772,'inspected'),(22028,'selectedDefinition')]:
    set_rule(current,F('garage.repairConfirm','Sửa {bike} về 100% với ${cost}?',bike=definition+'.DisplayName',cost=definition+'.RepairCredits.ToString("N0")'))
current=18189;set_rule(current,'shop ? '+T('shop.heading','TÌM MỘT CẤU HÌNH PHÙ HỢP.')+' : '+T('garage.browserHeading','XE CỦA BẠN.'))
current=19406
item_args={'index':'(bike.CatalogIndex + 1).ToString("00")','bike':'bike.DisplayName'}
owned=F('bikeList.owned','{index}   {bike}\nĐÃ SỞ HỮU',**item_args)
owned_equipped=F('bikeList.ownedEquipped','{index}   {bike}\nĐÃ SỞ HỮU · ĐANG DÙNG',**item_args)
locked=F('bikeList.locked','{index}   {bike}\nCHƯA MỞ',**item_args)
locked_equipped=F('bikeList.lockedEquipped','{index}   {bike}\nCHƯA MỞ · ĐANG DÙNG',**item_args)
price=F('bikeList.price','{index}   {bike}\n${cost}',**item_args,cost='bike.PriceCredits.ToString("N0")')
price_equipped=F('bikeList.priceEquipped','{index}   {bike}\n${cost} · ĐANG DÙNG',**item_args,cost='bike.PriceCredits.ToString("N0")')
set_rule(current,'owned ? (bike.Id == profile.SelectedBikeId ? '+owned_equipped+' : '+owned+') : !bike.HasDistinctArt ? (bike.Id == profile.SelectedBikeId ? '+locked_equipped+' : '+locked+') : (bike.Id == profile.SelectedBikeId ? '+price_equipped+' : '+price+')')
current=20671
equipped=F('bikeDetail.equipped','TÌNH TRẠNG {condition}% · ĐANG DÙNG',condition='condition.ToString()')
owned=F('bikeDetail.owned','TÌNH TRẠNG {condition}% · ĐÃ SỞ HỮU',condition='condition.ToString()')
available=F('bikeDetail.available','${cost} · CÓ THỂ MUA',cost='inspected.PriceCredits.ToString("N0")')
locked=F('bikeDetail.locked','${cost} · CHƯA MỞ',cost='inspected.PriceCredits.ToString("N0")')
set_rule(current,'isOwned ? (equipped ? '+equipped+' : '+owned+') : (inspected.HasDistinctArt ? '+available+' : '+locked+')')
current=21240;set_rule(current,F('bike.compare','SO VỚI {bike}\nGiới hạn tốc độ {difference} km/h\nHệ số 1× lấy Spark 450 làm mốc. Đây là thông số thiết kế trong game.',bike='current.DisplayName.ToUpperInvariant()',difference='difference.ToString("+0.#;-0.#;0", CultureInfo.InvariantCulture)'))
current=21959;set_rule(current,F('garage.repairButton','SỬA XE · ${cost}',cost='inspected.RepairCredits.ToString("N0")'))
current=22413;set_rule(current,F('shop.buyButton','MUA THÊM · ${cost}',cost='inspected.PriceCredits.ToString("N0")'))
current=22483;set_rule(current,F('shop.buyConfirm','Mua {bike} với ${cost}?',bike='selectedDefinition.DisplayName',cost='selectedDefinition.PriceCredits.ToString("N0")'))
current=22914;set_rule(current,F('shop.tradeConfirm','Bán chiếc đang dùng với ${tradeValue} và mua {bike} với ${cost}?',tradeValue='tradeValue.ToString("N0")',bike='selectedDefinition.DisplayName',cost='selectedDefinition.PriceCredits.ToString("N0")'))
current=23380;set_rule(current,'inRoom ? '+T('shop.leaveRoom','Rời phòng trước khi đổi, mua hoặc sửa xe.')+' : '+T('profile.guestTransactions','Phiên khách không thực hiện giao dịch hồ sơ.'))
current=23929;set_rule(current,F('bike.previewTooltip','Xem thiết kế {bike} và trở lại hồ sơ.',bike='bike.DisplayName'))
current=24214;set_rule(current,F('bike.stats','GIỚI HẠN {speed} km/h  ·  TĂNG TỐC ×{acceleration}\nPHANH {braking} m/s²  ·  BÁM CUA ×{cornering}',
    speed='(tuning.MaximumSpeedMillimetersPerSecond * .0036).ToString("0.#", CultureInfo.InvariantCulture)',
    acceleration='(tuning.EnginePermille / 1000.0).ToString("0.00", CultureInfo.InvariantCulture)',
    braking='(tuning.BrakeDeceleration / 1000.0).ToString("0.#", CultureInfo.InvariantCulture)',
    cornering='(tuning.CorneringPermille / 1000.0).ToString("0.00", CultureInfo.InvariantCulture)'))
current=27425;set_rule(current,'selected ? '+T('characters.accompanying','ĐANG ĐỒNG HÀNH')+' : available ? '+T('characters.ready','SẴN SÀNG LÊN ĐƯỜNG')+' : '+T('state.locked','CHƯA MỞ'))
current=27593;set_rule(current,'selected ? '+T('characters.selected','ĐANG CHỌN')+' : '+T('characters.choose','CHỌN TAY ĐUA'))
current=29913;set_rule(current,F('campaign.level','CẤP {level}',level='(level + 1).ToString("00")'))
current=30290;set_rule(current,'!route.IsPlayable ? '+T('campaign.comingSoon','SẮP RA MẮT')+' : level > profile.LevelIndex ? '+T('state.locked','CHƯA MỞ')+' : qualified ? '+T('campaign.qualified','ĐÃ QUA')+' : '+T('campaign.race','ĐUA'))
current=32023;set_rule(current,F('ledger.balance','SỐ DƯ ${balance}',balance='entry.Balance.ToString("N0")'))
current=32937;set_rule(current,F('account.loggedIn','ĐANG ĐĂNG NHẬP: {username}',username='profile.Username'))
current=40784;set_rule(current,'DateTimeOffset.TryParse(value, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var timestamp) ? timestamp.ToString("dd/MM/yyyy HH:mm \'UTC\'", CultureInfo.InvariantCulture) : '+T('ledger.unknownTime','Thời gian chưa rõ'))
current=43298;set_rule(current,F('error.unknown','Chưa thực hiện được thao tác ({code}). Làm mới hồ sơ và kiểm tra dữ liệu vừa nhập.',code='code'))

if set(bindings) != set(sites) or len(bindings) != 141:
    raise RuntimeError('Every reviewed expression needs exactly one whole-expression binding.')
for entry in entries.values():
    if not entry['key'].startswith('career.') or not entry['vi'].strip():
        raise RuntimeError('Invalid Career template identity.')
external_rows=[external[key] for key in sorted(external)]
canonical={'schema':1,'boundary':'career','sourceFiles':[{'path':SOURCE,'sha256':EXPECTED_SOURCE}],
    'entries':[entries[key] for key in sorted(entries)],
    'externalCommonKeys':[entry['key'] for entry in external_rows],
    'scope':'Complete VI semantic templates for CareerView only. Names, protocol operations, diagnostic codes, numeric precision and layout remain unchanged.'}
site_map={'schema':1,'boundary':'career','source':canonical['sourceFiles'][0],
    'reviewedInventorySha256':hashlib.sha256(INVENTORY.read_bytes()).hexdigest(),
    'reviewedLiteralOccurrences':175,'reviewedDistinctFragments':161,'reviewedExpressionSites':141,'reviewedCompositionSites':30,
    'commonBindings':external_rows,
    'sites':[dict(sites[start],**bindings[start]) for start in sorted(sites)],
    'untouchedData':['RACING BOIS','Spark 450','bike/character/route display names','user display names/usernames','realm codes/endpoints',
        'CareerIntent operations and server error codes','UI element names/classes','numeric format strings and UTC timestamp format'],
    'translationsAuthored':False}

def write_new(name,value):
    path=STAGE/name
    payload=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if path.exists() and path.read_bytes()!=payload:
        raise RuntimeError('Existing template freeze differs; preserve it and create a revision: '+str(path))
    if not path.exists():
        path.write_bytes(payload)

write_new('canonical-source.json',canonical)
write_new('source-bindings.json',site_map)
write_new('VI.json',{'schema':1,'locale':'VI','boundary':'career','strings':{entry['key']:entry['vi'] for entry in canonical['entries']}})
worksheet='key\targuments\tvi_json\n'+''.join(entry['key']+'\t'+','.join(entry['arguments'])+'\t'+json.dumps(entry['vi'],ensure_ascii=False)+'\n' for entry in canonical['entries'])
worksheet_path=STAGE/'VI-source.tsv'
if worksheet_path.exists() and worksheet_path.read_text(encoding='utf-8')!=worksheet:
    raise RuntimeError('VI worksheet already exists with different content.')
worksheet_path.write_text(worksheet,encoding='utf-8',newline='\n')
print(json.dumps({'careerKeys':len(entries),'commonKeys':len(external),'wholeExpressionBindings':len(bindings),
    'compositionSites':30,'canonicalSha256':hashlib.sha256((STAGE/'canonical-source.json').read_bytes()).hexdigest(),
    'scope':'VI template/key preparation only; no translation or live source edits.'},ensure_ascii=False,indent=2))
