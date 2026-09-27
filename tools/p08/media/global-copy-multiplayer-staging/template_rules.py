"""Canonical display-template checks shared by authoring and generation."""
from collections import Counter
import re


def validate_template(value, canonical):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 and c != '\n' for c in value):
        raise ValueError('Invalid display text.')
    expected = Counter(re.findall(r'\{([^{}]+)\}', canonical))
    actual = Counter(re.findall(r'\{([^{}]+)\}', value))
    if actual != expected:
        raise ValueError('Named placeholder multiplicity differs from canonical source.')
    if re.search(r'[{}]', re.sub(r'\{[^{}]+\}', '', value)):
        raise ValueError('Malformed template placeholder.')
