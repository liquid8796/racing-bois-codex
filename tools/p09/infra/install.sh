#!/bin/bash
set -euo pipefail
umask 077
release=${1:?release id required}
archive=${2:?archive path required}
expected=${3:?archive sha256 required}
ops=${4:?uploaded ops directory required}
[[ "$release" =~ ^[a-z0-9-]{1,48}$ && "$expected" =~ ^[a-f0-9]{64}$ ]]
[[ "$(realpath "$archive")" == /tmp/racing-bois-p09.*/* && "$(realpath "$ops")" == /tmp/racing-bois-p09.*/* ]]
[[ "$(sha256sum "$archive" | cut -d' ' -f1)" == "$expected" ]]
if ! id racing-bois-staging >/dev/null 2>&1; then useradd --system --home /var/lib/racing-bois-staging --shell /usr/sbin/nologin racing-bois-staging; fi
install -d -m 0755 /srv/racing-bois /srv/racing-bois/releases /srv/racing-bois/assets /srv/racing-bois/ops
install -d -m 0700 -o racing-bois-staging -g racing-bois-staging /var/lib/racing-bois-staging /srv/racing-bois/backups
destination=/srv/racing-bois/releases/$release
[[ ! -e "$destination" ]]
install -d -m 0755 "$destination"
tar -xzf "$archive" -C "$destination" --no-same-owner
python3 - "$destination" <<'PY'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]); m=json.loads((p/'release.json').read_text())
for f in m['files']:
    q=(p/f['path']).resolve()
    if not q.is_relative_to(p) or not q.is_file():raise RuntimeError('Invalid release member')
    with q.open('rb') as s:h=hashlib.file_digest(s,'sha256').hexdigest()
    if h!=f['sha256'] or q.stat().st_size!=f['bytes']:raise RuntimeError('Release hash mismatch')
print(json.dumps({'status':'passed','scope':'uploaded immutable release hashes','files':len(m['files']),'sourceSha256':m['source']['sha256']}))
PY
find "$destination" -type d -exec chmod 0755 {} +
find "$destination" -type f -exec chmod 0644 {} +
chmod 0755 "$destination/server/RacingBois.Server.Host" \
    "$destination/tests/persistence/RacingBois.Persistence.Tests" \
    "$destination/tests/multiplayer/RacingBois.Multiplayer.Integration.Tests" \
    "$destination/tests/gameplay/RacingBois.Gameplay.Tests"
install -m 0755 "$ops/backup.py" "$ops/restore-drill.py" "$ops/validate-restored.py" "$ops/monitor.py" /srv/racing-bois/ops/
install -m 0644 "$ops/racing-bois-staging.service" "$ops/racing-bois-backup.service" "$ops/racing-bois-backup.timer" "$ops/racing-bois-monitor.service" "$ops/racing-bois-monitor.timer" /etc/systemd/system/
if [[ ! -f /var/lib/racing-bois-staging/backup-key ]]; then
    openssl rand -base64 48 > /var/lib/racing-bois-staging/backup-key
    chown racing-bois-staging:racing-bois-staging /var/lib/racing-bois-staging/backup-key
    chmod 0600 /var/lib/racing-bois-staging/backup-key
fi
systemctl daemon-reload
printf '%s\n' "Prepared release $release; activation and Caddy reload are separate verified steps."
