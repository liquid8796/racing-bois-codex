import copy
import tempfile
import unittest
from pathlib import Path
from generate import LOCALES, read_unique, validate
from prepare_source import HERE, source

class LocaleDataControls(unittest.TestCase):
    def setUp(self):
        self.expected = source()
        self.vi = read_unique(HERE / 'locales/VI.json')

    def test_real_authored_locale_coverage(self):
        for locale in LOCALES:
            validate(locale, read_unique(HERE / 'locales' / (locale + '.json')), self.expected)

    def reject(self, mutation):
        candidate = copy.deepcopy(self.vi)
        mutation(candidate)
        with self.assertRaises(ValueError):
            validate('VI', candidate, self.expected)

    def test_stale_english_binding(self):
        self.reject(lambda p: p.update(sourceSha256='0' * 64))

    def test_stale_storyboard_binding(self):
        self.reject(lambda p: p.update(storyboardsSha256='0' * 64))

    def test_missing_caption(self):
        self.reject(lambda p: p['strings'].pop('rb-busted-a-quiet-shoulder/beat/0'))

    def test_unrecognized_scene(self):
        self.reject(lambda p: p['strings'].update({'unknown/beat/0': 'Một câu mới'}))

    def test_blank_translation(self):
        self.reject(lambda p: p['strings'].update({'ui.play': '  '}))

    def test_lost_format_argument(self):
        self.reject(lambda p: p['strings'].update({'ui.summary': 'Các cảnh 3D'}))

    def test_extra_format_argument(self):
        self.reject(lambda p: p['strings'].update({'ui.summary': '{0} cảnh {1}'}))

    def test_malformed_brace(self):
        self.reject(lambda p: p['strings'].update({'ui.play': 'Phát {'}))

    def test_wrong_locale_identity(self):
        self.reject(lambda p: p.update(locale='ENU'))

    def test_english_is_exact_source(self):
        candidate = copy.deepcopy(self.expected)
        candidate['strings']['ui.play'] = 'Some other English'
        with self.assertRaises(ValueError):
            validate('ENU', candidate, self.expected)

    def test_duplicate_json_key(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'duplicate.json'
            path.write_text('{"strings":{"x":"one","x":"two"}}', encoding='utf-8')
            with self.assertRaises(ValueError):
                read_unique(path)

if __name__ == '__main__':
    unittest.main()
