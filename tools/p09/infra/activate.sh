#!/bin/bash
set -euo pipefail
release=${1:?release id required}
[[ "$release" =~ ^[a-z0-9-]{1,48}$ ]]
ready_attempts=${RB_READY_ATTEMPTS:-30}
[[ "$ready_attempts" =~ ^[0-9]+$ && "$ready_attempts" -ge 3 && "$ready_attempts" -le 60 ]]
exec 9>/run/lock/racing-bois-deploy.lock
flock -n 9
target=/srv/racing-bois/releases/$release
[[ -f "$target/release.json" && -x "$target/server/RacingBois.Server.Host" ]]
previous=''
if [[ -L /srv/racing-bois/current ]]; then previous=$(readlink -f /srv/racing-bois/current); fi
if [[ -n "$previous" ]]; then [[ "$previous" == /srv/racing-bois/releases/* ]]; fi
ln -s "$target" /srv/racing-bois/current.next
mv -Tf /srv/racing-bois/current.next /srv/racing-bois/current
systemctl restart racing-bois-staging || true
for ((attempt=1; attempt<=ready_attempts; attempt++)); do
    pid=$(systemctl show racing-bois-staging -p MainPID --value)
    executable=$(readlink -f "/proc/$pid/exe" || true)
    if [[ "$executable" == "$target/server/RacingBois.Server.Host" ]] && curl --max-time 2 --fail --silent http://127.0.0.1:18080/ready >/dev/null; then
        systemctl enable racing-bois-staging racing-bois-backup.timer racing-bois-monitor.timer >/dev/null
        systemctl start racing-bois-backup.timer racing-bois-monitor.timer
        printf '{"status":"passed","releaseId":"%s","previous":"%s"}\n' "$release" "$previous"
        exit 0
    fi
    sleep 1
done
if [[ -n "$previous" && "$previous" != "$target" ]]; then
    ln -s "$previous" /srv/racing-bois/current.rollback
    mv -Tf /srv/racing-bois/current.rollback /srv/racing-bois/current
    systemctl reset-failed racing-bois-staging
    systemctl restart racing-bois-staging
    curl --max-time 15 --retry 10 --retry-connrefused --fail --silent http://127.0.0.1:18080/ready >/dev/null
    printf '{"status":"rolled_back","rejectedReleaseId":"%s"}\n' "$release"
fi
exit 1
