#!/bin/bash
set -euo pipefail
source=${1:?uploaded Caddy site required}
[[ "$(realpath "$source")" == /tmp/racing-bois-p09.*/ops/racing-bois.caddy ]]
destination=/etc/caddy/conf.d/racing-bois.caddy
[[ ! -e "$destination" ]]
before=$(sha256sum /etc/caddy/Caddyfile /etc/caddy/upstream.conf)
legacy_status=$(curl --max-time 15 -s -o /dev/null -w '%{http_code}' https://158.180.59.36.sslip.io/)
install -m 0644 "$source" "$destination"
if ! caddy validate --config /etc/caddy/Caddyfile >/var/lib/racing-bois-staging/caddy-validation.log 2>&1; then
    rm -- "$destination"
    printf '%s\n' 'Racing Bois site validation failed; its file was removed; Caddy was not reloaded.' >&2
    exit 1
fi
if ! systemctl reload caddy; then
    rm -- "$destination"
    printf '%s\n' 'Caddy reload failed; own site removed.' >&2
    exit 1
fi
[[ "$(sha256sum /etc/caddy/Caddyfile /etc/caddy/upstream.conf)" == "$before" ]]
after_status=$(curl --max-time 15 -s -o /dev/null -w '%{http_code}' https://158.180.59.36.sslip.io/)
[[ "$legacy_status" == "$after_status" ]]
printf '{"status":"passed","combinedConfigValidated":true,"existingConfigHashesUnchanged":true,"legacyHttpStatusBefore":"%s","legacyHttpStatusAfter":"%s"}\n' "$legacy_status" "$after_status"
