import unittest
from template_rules import validate_template


class TemplateRules(unittest.TestCase):
    def test_reordering_is_allowed(self):
        validate_template('{second} puis {first}', '{first} then {second}')

    def test_duplicate_translation_placeholder_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_template('NIVEAU {level}, encore {level}', 'CẤP {level}')

    def test_missing_and_extra_placeholders_are_rejected(self):
        for value in ('CẤP', 'CẤP {level} {other}'):
            with self.assertRaises(ValueError):
                validate_template(value, 'CẤP {level}')

    def test_canonical_repetitions_must_remain_exact(self):
        validate_template('{name} / {name}', '{name} then {name}')
        with self.assertRaises(ValueError):
            validate_template('{name}', '{name} then {name}')

    def test_malformed_delimiters_are_rejected(self):
        for value in ('x}', '{', '{{level}}'):
            with self.assertRaises(ValueError):
                validate_template(value, '{level}')


if __name__ == '__main__':
    unittest.main()
