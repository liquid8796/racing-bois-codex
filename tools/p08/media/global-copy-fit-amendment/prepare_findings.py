"""Bind only visually confirmed run04 copy-fit changes to immutable evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).with_name("changes.json")
KEY = "career.garage.pristine"
CHANGES = (
    ("DEU", "MOTORRAD UNBESCHÄDIGT", "UNBESCHÄDIGT"),
    ("ESP", "MOTO EN PERFECTO ESTADO", "SIN DAÑOS"),
    ("FRA", "MOTO EN PARFAIT ÉTAT", "MOTO INTACTE"),
)

def main():
    if OUT.exists():
        raise SystemExit("Refusing to overwrite existing findings")
    rows = []
    for locale, before, after in CHANGES:
        current = json.loads((ROOT / f"tools/p08/media/global-copy-career-staging/locales/{locale}.json").read_text(encoding="utf-8"))
        if current["strings"][KEY] != before:
            raise SystemExit(f"Source differs for {locale}/{KEY}")
        evidence = []
        for width in (1920, 1366):
            path = f"docs/p08/ui-owned-render/20260928-ui-render-04-{width}/career-garage-{locale.lower()}.png"
            evidence.append({"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()})
        rows.append({
            "provider": "Career", "locale": locale, "key": KEY,
            "before": before, "after": after,
            "reason": "Actual run04 images at 1920 and 1366 show the pristine-condition label reaching or exceeding the fixed button border; shorten the same condition meaning while preserving geometry, font size, and disabled behavior. New rendering is required to verify the proposed text fits.",
            "evidence": evidence, "protectedTokens": [],
        })
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} independently reviewed copy-fit changes")

if __name__ == "__main__":
    main()
