# gptpaynow domain and policy handoff — 2026-10-07

## Deployed application

- Existing Compose project: `payforothers18003`, directory `/opt/payforothers-18003`, port `18003`.
- Store name and canonical URL: `gptpaynow`, `https://www.gptpaynow.com`.
- Admin username changed through the existing authenticated API to `jetoxiao`. New login verified; old tokens revoked. Password intentionally omitted from this document and source control.
- Legal pages have a localized structured fallback; existing admin-authored legal HTML still takes precedence and is sanitized for display.
- Footer removed from the classic app shell. Primary-foreground dark token corrected to dark text on light buttons.

## Domain blocker

### Update — 2026-10-07 17:42 Asia/Shanghai

HTTP-01 probe requests now reach the correct server. Certificate issuance succeeded for BOTH domains (Let's Encrypt; expires 2027-01-05). The HTTPS vhost has been enabled and `nginx -t` passed. Local HTTPS verification with certificate validation returns 200 for `/health`; HTTP and apex redirects correctly target `https://www.gptpaynow.com`.

Public HTTPS still returns Cloudflare 522. A direct connection to `43.163.239.213:443` times out, although Nginx is listening on 443 and local TLS works. Host UFW is inactive; inspected host input rules do not block HTTPS. An inbound packet capture during external connection attempts saw no matching packets. The likely remaining blocker is the cloud-provider firewall/security group or upstream network filtering. The operator needs to allow inbound TCP 443; no cloud control-plane credentials were available to change this.

A certificate-specific renewal deploy hook has been installed at `/etc/letsencrypt/renewal-hooks/deploy/gptpaynow-nginx`; the Certbot timer is active. The renewal dry-run succeeded (exit 0), recorded in `/opt/payforothers-18003/domain-renewal-dryrun.log`.

The notes below describe the earlier failed attempt and are superseded by this update regarding certificate issuance and HTTPS activation.

DNS currently resolves through Cloudflare. The A/CNAME origin values are not visible in public DNS when proxied.
The dedicated Nginx HTTP virtual host is installed and configuration-tested. Direct source-server requests for the ACME probe succeed. Cloudflare requests return a different 404 or 522 and do not appear in the source-server access log. Certbot failed HTTP-01 validation for both names; **no domain certificate has been issued**.

Required operator check:

1. Verify `@` and `www` target `43.163.239.213`, with no stale origin IPv6 record. `www` may also CNAME to the correct apex.
2. Check Workers, Pages, redirects, Origin Rules, and firewall rules that might reroute/block this hostname or `/.well-known/acme-challenge/`.
3. Temporarily use DNS-only if needed for validation; wait for propagation.
4. Request a certificate for BOTH names using the existing Certbot webroot `/var/www/certbot`.
5. Only after successful issuance activate `deploy/nginx/gptpaynow-https.conf` for this site's vhost, run `nginx -t`, then reload Nginx. Do not overwrite other sites.
6. Select Cloudflare Full (strict). Verify both hostnames, HTTP→HTTPS, apex→www, deep-link/query preservation, certificate SAN/expiry, and `certbot renew --cert-name gptpaynow.com --dry-run`.
7. Configure a certificate-specific deploy hook to reload Nginx after renewal; keep the existing active Certbot timer. Do not claim renewal tested before completing these steps.

Source: [Cloudflare Full (strict)](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/).

## Legal publication gaps

The operator has not yet supplied legal name/company identity, business location/address, target markets, or a working support/privacy email. Pages visibly flag these missing details and ask users not to pay until they are supplied. Template Telegram/WhatsApp contacts were removed from public configuration; no replacement address was invented.

The pages are a cautious draft, not a legal compliance certificate or a substitute for local counsel. Before commerce:

- Publish operator identity and verified support/privacy contacts; verify licensing, taxes, regional service eligibility, supplier authorization, and payment-provider conditions.
- Confirm actual processors, hosting locations, recipients, retention schedules, cross-border safeguards, access/deletion procedures, and implement operational controls described by the policy.
- Validate product-specific subscription warranty, delivery timing, refunds, and after-sales promises. No blanket digital-goods no-refund rule or no-liability-for-suspension clause was introduced.
- The checkout does not gain a new statutory withdrawal waiver or stored consent record from merely publishing these documents. Where a separate valid confirmation is required, implement and record it before relying on an exception.
- Obtain jurisdiction-specific counsel review; do not invent governing law or exclusive courts.
- Public IP HTTP access remains for compatibility while domain TLS is blocked. Do not collect sensitive information over that fallback URL; use the verified HTTPS domain once ready.

Source reviewed: [PRC consumer-protection implementation regulations](https://www.gov.cn/zhengce/content/202403/content_6940158.htm), including rules on standard terms, withdrawal confirmation, and excessive personal-data collection. Applicability depends on the actual operator and customers; it was not assumed as the only governing law.
