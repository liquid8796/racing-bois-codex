"""Generate a complete six-locale Career module from the frozen semantic inventory."""
from __future__ import annotations
import hashlib
import json
import re
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
STAGE=Path(__file__).resolve().parent
ORDER=['ENU','DEU','ESP','FRA','ITA','VI']
CANONICAL_SHA='a218856531fc62e289dfa42fb931a850ae40d3e6448284c328b692dd49e44109'
INSTALLED_SOURCE_SHA='47f78d8cfdfa4bcc819a522517c0fd6a3873bca2595287d82a686d3039677905'

def source_identity_allowed(source, actual):
    return actual == source['sha256'] or (source['path'] == 'Assets/RacingBois/Client/Presentation/CareerView.cs' and actual == INSTALLED_SOURCE_SHA)

ARGUMENT=re.compile(r'\{([A-Za-z][A-Za-z0-9]*)\}')


def strict_pairs(pairs):
    output={}
    for key,value in pairs:
        if key in output:
            raise ValueError('Duplicate JSON key: '+key)
        output[key]=value
    return output


def load(path):
    return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=strict_pairs)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_inventory():
    path=STAGE/'canonical-source.json'
    if digest(path)!=CANONICAL_SHA:
        raise ValueError('Frozen semantic inventory changed; author a reviewed revision first.')
    canonical=load(path)
    for source in canonical['sourceFiles']:
        if not source_identity_allowed(source,digest(ROOT/source['path'])):
            raise ValueError('Translation source drift: '+source['path'])
    entries=canonical['entries']
    if len(entries)!=151 or len({entry['key'] for entry in entries})!=151:
        raise ValueError('Expected exactly151 unique Career semantic keys.')
    return canonical


def validate_locale(data,locale,canonical,protected):
    if data.get('schema')!=1 or data.get('locale')!=locale or data.get('boundary')!='career' or data.get('sourceSha256')!=CANONICAL_SHA:
        raise ValueError('Locale metadata mismatch: '+locale)
    texts=data.get('strings')
    if not isinstance(texts,dict) or set(texts)!={entry['key'] for entry in canonical['entries']}:
        raise ValueError('Missing/extra locale keys: '+locale)
    for entry in canonical['entries']:
        key=entry['key'];text=texts[key]
        if not isinstance(text,str) or not text.strip():
            raise ValueError('Blank locale text: '+locale+'/'+key)
        if sorted(ARGUMENT.findall(text))!=sorted(entry['arguments']) or any(c in ARGUMENT.sub('',text) for c in '{}'):
            raise ValueError('Malformed/lost/extra/repeated named argument: '+locale+'/'+key)
        if text.count('\n')!=entry['vi'].count('\n'):
            raise ValueError('Authored line-break count changed: '+locale+'/'+key)
        for token in protected['protectedTemplateTokens'].get(key,[]):
            if token not in text:
                raise ValueError('Protected authored token changed: '+locale+'/'+key+'/'+token)
        if locale=='VI' and text!=entry['vi']:
            raise ValueError('Original VI template changed: '+key)
    return texts


def generate():
    raise ValueError('Active reviewed Career overlay: run python tools/p08/media/global-copy-effective/generate.py (or --check). Frozen baseline generation is disabled to prevent reverting the ENU amendment.')
    canonical=read_inventory();protected=load(STAGE/'protected-tokens.json')
    tables={}
    inputs=[]
    for locale in ORDER:
        path=STAGE/'VI.json' if locale=='VI' else STAGE/'locales'/f'{locale}.json'
        tables[locale]=validate_locale(load(path),locale,canonical,protected)
        inputs.append({'path':path.relative_to(ROOT).as_posix(),'sha256':digest(path)})
    text='''// Generated from frozen complete Career translations. Do not hand-edit.
// Provider order: ENU, DEU, ESP, FRA, ITA, VI.
using System.Collections.Generic;
namespace RacingBois.Client.Application
{
    public static partial class UiText
    {
        static partial void AddCareer(Dictionary<string, string[]> rows)
        {
'''
    for entry in canonical['entries']:
        key=entry['key']
        values=', '.join(json.dumps(tables[locale][key],ensure_ascii=False) for locale in ORDER)
        text+='            rows.Add('+json.dumps(key)+', new[] { '+values+' });\n'
    text+='        }\n    }\n}\n'
    output=STAGE/'UiText.Career.Generated.cs'
    output.write_text(text,encoding='utf-8',newline='\n')
    meta=output.with_suffix('.cs.meta')
    if not meta.exists():
        meta.write_text('fileFormatVersion: 2\nguid: '+uuid.uuid4().hex+'\n',encoding='utf-8')
    coverage={'schema':1,'boundary':'career','canonicalSha256':CANONICAL_SHA,'localeOrder':ORDER,
        'keysPerLocale':151,'translatedLocales':5,'sourceLocale':'VI','explicitTranslationCells':906,
        'missingKeys':0,'missingTranslations':0,'fallbackFilledCells':0,'namedArgumentsValidated':True,
        'protectedTokensValidated':True,'authoredLineBreaksPreserved':True,'inputs':inputs,
        'generated':{'path':output.relative_to(ROOT).as_posix(),'sha256':digest(output)},
        'scope':'Complete authored translation data and generated lookup wiring. No native rendering or linguistic-quality acceptance claimed.'}
    (STAGE/'coverage.json').write_text(json.dumps(coverage,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(coverage,indent=2))


if __name__=='__main__':
    generate()
