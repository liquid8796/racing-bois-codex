"""Emit the main display module only after complete source-bound authored locale validation."""
import collections
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCALES = ['ENU','DEU','ESP','FRA','ITA','VI']

def read(path):
    def pairs(items):
        result = {}
        for key,value in items:
            if key in result: raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs)

def placeholders(value):
    names = re.findall(r'\{([A-Za-z][A-Za-z0-9]*)\}',value)
    residue = re.sub(r'\{[A-Za-z][A-Za-z0-9]*\}','',value)
    if '{' in residue or '}' in residue: raise ValueError('Malformed template braces')
    return collections.Counter(names)

def validate(payload, locale, source, source_hash):
    if payload.get('schema') != 1 or payload.get('locale') != locale or payload.get('sourceSha256') != source_hash or payload.get('boundary') != source['boundary']:
        raise ValueError('Locale identity or source binding mismatch: '+locale)
    strings = payload.get('strings',{})
    if set(strings) != {entry['key'] for entry in source['entries']}: raise ValueError('Missing/extra locale keys: '+locale)
    for entry in source['entries']:
        key = entry['key']; value = strings[key]
        if not isinstance(value,str) or not value.strip() or '\ufffd' in value or any(ord(c)<32 and c!='\n' for c in value):
            raise ValueError('Invalid display copy: '+key)
        if placeholders(value) != placeholders(entry['vi']): raise ValueError('Named argument mismatch: '+key)
        if value.count('\n') != entry['vi'].count('\n'): raise ValueError('Explicit line breaks changed: '+key)
        if locale=='VI' and value!=entry['vi'] or locale=='ENU' and value!=entry['enu']:
            raise ValueError('Frozen source/fallback changed: '+key)
        if key=='settings.hudRange' and re.findall(r'\d+%',value)!=['85%','115%']:
            raise ValueError('HUD range values changed')
        if key=='settings.navigationHelp' and any(not re.search(r'(?<![A-Za-z0-9])'+token+r'(?![A-Za-z0-9])',value) for token in ['TAB','ENTER','A']):
            raise ValueError('Keyboard/controller button identities changed')
        if value.count('$') != entry['vi'].count('$'): raise ValueError('Game currency marker changed: '+key)
    return strings

def generate():
    source = read(HERE/'canonical-source.json')
    source_hash = hashlib.sha256((HERE/'canonical-source.json').read_bytes()).hexdigest()
    freeze = read(HERE/'templates-freeze.json')
    if source_hash != freeze['canonicalSourceSha256'] or len(source['entries']) != freeze['keyCount']:
        raise ValueError('Canonical templates changed after freeze')
    catalogs = {locale:validate(read(HERE/'locales'/(locale+'.json')),locale,source,source_hash) for locale in LOCALES}
    lines = ['// Generated from source-bound authored locale JSON; do not edit by hand.','using System.Collections.Generic;',
             'namespace RacingBois.Client.Application','{','    public static partial class UiText','    {',
             '        public const string MainSourceSha256 = "'+source_hash+'";',
             '        static partial void AddMain(Dictionary<string, string[]> rows)','        {']
    for entry in source['entries']:
        key=entry['key'];values=', '.join(json.dumps(catalogs[locale][key],ensure_ascii=True) for locale in LOCALES)
        lines.append('            rows.Add('+json.dumps(key)+', new[] { '+values+' });')
    lines += ['        }','    }','}']
    output = HERE/'UiText.Main.Generated.cs';output.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    result={'schema':1,'sourceSha256':source_hash,'keyCount':len(source['entries']),'locales':LOCALES,
            'generatedSha256':hashlib.sha256(output.read_bytes()).hexdigest(),'nativeAcceptance':False,'gamewideLocalizationAccepted':False}
    (HERE/'coverage.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':generate()
