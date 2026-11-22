#!/bin/sh
# Reload only after successful renewal of this site's certificate.
set -eu
if [ "${RENEWED_LINEAGE:-}" = /etc/letsencrypt/live/gptpaynow.com ]; then
    /usr/sbin/nginx -t
    /bin/systemctl reload nginx
fi
