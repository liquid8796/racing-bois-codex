import copy
import hashlib
import unittest
from generate import HERE, LOCALES, read, validate

class DataControls(unittest.TestCase):
    def setUp(self):
        self.source = read(HERE/'canonical-source.json')
        self.sha = hashlib.sha256((HERE/'canonical-source.json').read_bytes()).hexdigest()
        self.locale = read(HERE/'locales/DEU.json')
    def reject(self, mutation):
        candidate=copy.deepcopy(self.locale);mutation(candidate)
        with self.assertRaises(ValueError):validate(candidate,'DEU',self.source,self.sha)
    def test_all_authored_locales(self):
        for locale in LOCALES:validate(read(HERE/'locales'/(locale+'.json')),locale,self.source,self.sha)
    def test_stale_source(self):self.reject(lambda p:p.update(sourceSha256='0'*64))
    def test_wrong_locale(self):self.reject(lambda p:p.update(locale='FRA'))
    def test_missing_key(self):self.reject(lambda p:p['strings'].pop('menu.level'))
    def test_extra_key(self):self.reject(lambda p:p['strings'].update({'unknown.extra':'Text'}))
    def test_blank(self):self.reject(lambda p:p['strings'].update({'common.done':' '}))
    def test_changed_argument(self):self.reject(lambda p:p['strings'].update({'menu.level':'STUFE {other} /'}))
    def test_duplicate_argument(self):self.reject(lambda p:p['strings'].update({'menu.level':'{level} {level}'}))
    def test_broken_brace(self):self.reject(lambda p:p['strings'].update({'menu.level':'{level} {'}))
    def test_lost_linebreak(self):self.reject(lambda p:p['strings'].update({'results.practiceFunds':'Guthaben: ${credits}'}))
    def test_changed_slider_limit(self):self.reject(lambda p:p['strings'].update({'settings.hudRange':'80% — klein 115% — groß'}))
    def test_changed_currency(self):self.reject(lambda p:p['strings'].update({'results.fineDetail':'Strafe: €{fine}'}))
    def test_source_vi_must_remain_exact(self):
        p=read(HERE/'locales/VI.json');p['strings']['common.done']='ĐÃ XONG'
        with self.assertRaises(ValueError):validate(p,'VI',self.source,self.sha)
    def test_translated_parameter_order_is_allowed(self):
        p=copy.deepcopy(self.locale);p['strings']['display.requested']='{mode} · {resolution} angefordert.'
        validate(p,'DEU',self.source,self.sha)

if __name__=='__main__':unittest.main()
