"""Compose literal safe-mode Blender recipes on the host, never exec in Blender."""
import argparse
from pathlib import Path

root = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument('asset', choices=['motorcycle', 'rider', 'traffic', 'patrol'])
args = parser.parse_args()
folder = Path(__file__).resolve().parent
output = root / '_local' / ('p06-' + args.asset + '-recipe.py')
output.write_text((folder / 'common.py').read_text(encoding='utf8') + '\n' +
                  (folder / ('create_' + args.asset + '.py')).read_text(encoding='utf8'), encoding='utf8')
print(output)
