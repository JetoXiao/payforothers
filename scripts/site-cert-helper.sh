#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DOMAIN="${SITE_CERT_BASE_DOMAIN:-gptpaynow.com}"
REQUEST_DIR="${SITE_CERT_REQUEST_HOST_DIR:-/opt/payforothers-18003/cert-requests}"
NGINX_ROOT="${SITE_CERT_NGINX_ROOT:-/etc/nginx/sites-available/payforothers-sites}"
ENABLED_ROOT="${SITE_CERT_NGINX_ENABLED_ROOT:-/etc/nginx/sites-enabled}"
CHALLENGE_ROOT="${SITE_CERT_CHALLENGE_ROOT:-/var/www/certbot}"
UPSTREAM="${SITE_CERT_UPSTREAM:-127.0.0.1:18003}"

mkdir -p "$REQUEST_DIR/status" "$NGINX_ROOT" "$CHALLENGE_ROOT/.well-known/acme-challenge"

json_value() {
  python3 - "$1" "$2" <<'PY'
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    data = json.load(f)
value = data.get(sys.argv[2], '')
print(value if isinstance(value, (str, int)) else '')
PY
}

valid_domain() {
  local domain="$1"
  [[ "$domain" == *".$BASE_DOMAIN" ]] || return 1
  [[ "$domain" =~ ^[a-z0-9][a-z0-9-]{0,61}\.${BASE_DOMAIN//./\\.}$ ]]
}

status_file() { printf '%s/status/%s.json' "$REQUEST_DIR" "$1"; }

write_status() {
  local site_id="$1" domain="$2" state="$3" error="$4" expires="$5" requested="$6"
  python3 - "$(status_file "$site_id")" "$site_id" "$domain" "$state" "$error" "$expires" "$requested" <<'PY'
import json, os, sys, tempfile
from datetime import datetime, timezone
path, site_id, domain, state, error, expires, requested = sys.argv[1:]
data = {'site_id': int(site_id), 'domain': domain, 'state': state, 'updated_at': datetime.now(timezone.utc).isoformat()}
if error: data['error'] = error
if expires: data['expires_at'] = expires
if requested: data['requested_at'] = requested
fd, tmp = tempfile.mkstemp(prefix='.status-', dir=os.path.dirname(path), text=True)
with os.fdopen(fd, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)
    f.flush(); os.fsync(f.fileno())
os.replace(tmp, path)
PY
}

write_http_config() {
  local domain="$1"
  cat > "$NGINX_ROOT/$domain.conf" <<EOF
server {
    listen 80;
    server_name $domain;
    location /.well-known/acme-challenge/ { root $CHALLENGE_ROOT; }
    location / { return 308 https://\$host\$request_uri; }
}
EOF
  ln -sfn "$NGINX_ROOT/$domain.conf" "$ENABLED_ROOT/payforothers-site-$domain.conf"
  nginx -t && systemctl reload nginx
}

write_https_config() {
  local domain="$1"
  cat > "$NGINX_ROOT/$domain.conf" <<EOF
server {
    listen 80;
    server_name $domain;
    location /.well-known/acme-challenge/ { root $CHALLENGE_ROOT; }
    location / { return 308 https://\$host\$request_uri; }
}
server {
    listen 443 ssl http2;
    server_name $domain;
    ssl_certificate /etc/letsencrypt/live/$domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$domain/privkey.pem;
    location / {
        proxy_pass http://$UPSTREAM;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
EOF
  nginx -t && systemctl reload nginx
}

process_request() {
  local request="$1" site_id domain requested cert_end
  site_id="$(json_value "$request" site_id)"
  domain="$(json_value "$request" domain)"
  requested="$(json_value "$request" requested_at)"
  [[ "$site_id" =~ ^[1-9][0-9]*$ ]] || return 0
  if ! valid_domain "$domain"; then
    write_status "$site_id" "$domain" error "domain is outside the configured site suffix" '' "$requested"
    mv -f "$request" "$request.failed"; return 0
  fi
  write_status "$site_id" "$domain" issuing '' '' "$requested"
  if ! write_http_config "$domain"; then
    write_status "$site_id" "$domain" error "nginx HTTP challenge configuration failed" '' "$requested"
    mv -f "$request" "$request.failed"; return 0
  fi
  if ! certbot certonly --webroot -w "$CHALLENGE_ROOT" -d "$domain" --cert-name "$domain" --non-interactive --agree-tos --register-unsafely-without-email --keep-until-expiring >/tmp/site-cert-$site_id.log 2>&1; then
    write_status "$site_id" "$domain" error "certbot issuance failed; see /tmp/site-cert log" '' "$requested"
    mv -f "$request" "$request.failed"; return 0
  fi
  cert_end="$(openssl x509 -enddate -noout -in "/etc/letsencrypt/live/$domain/cert.pem" | sed 's/^notAfter=//')"
  write_https_config "$domain"
  write_status "$site_id" "$domain" issued '' "$cert_end" "$requested"
  mv -f "$request" "$request.done"
}

case "${1:-once}" in
  --once) for request in "$REQUEST_DIR"/request-*.json; do [[ -f "$request" ]] && process_request "$request"; done ;;
  *) echo "usage: $0 --once" >&2; exit 2 ;;
esac
