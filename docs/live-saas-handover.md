# Brijvas Property SaaS handover

Deployed 10 September 2026 using local commits -> GitHub master -> server `git pull --ff-only`.

## Live entry points

- Existing customer website: https://brijvas.com/
- SaaS portal: https://propertystudio.live-app.in/saas/
- New customer signup: https://propertystudio.live-app.in/saas/signup/
- Business login: https://propertystudio.live-app.in/saas/login/
- Business selection after login: https://propertystudio.live-app.in/saas/workspaces/
- Existing Brijvas management: https://propertystudio.live-app.in/saas/business/brijvas/
- Platform administration: https://propertystudio.live-app.in/admin/ (superuser only)

Existing active account `admin_charan` owns the Brijvas workspace. Its password was not changed. The new application secret invalidates old sessions, so sign in again.

## Deliver a customer website

1. Customer opens signup and enters business name, unique site slug, account details and plan.
2. Signup creates the owner membership, branding, property categories and a 14-day trial.
3. Share `https://propertystudio.live-app.in/sites/<customer-slug>/`; it is usable immediately without new DNS or certificate provisioning.
4. In Business settings, update logo, contact information and business description. Add listings from the customer site's dashboard and manage approvals, enquiries and team access.

Starter allows 50 listings, 3 staff seats and 1 GB media; Agency 250/10/5 GB; Business 1000/25/20 GB. Existing Brijvas uses a separate legacy plan to preserve access. Prices have not been commercially configured and paid checkout remains disabled.

## Deployment and preservation

- Application: `/var/www/brijvas-saas`, Python 3.12, Gunicorn, Django 5.2.
- Service: `brijvas-saas.service`, user `www-data`, loopback port 8012.
- Database: `brijvas_saas`, MySQL/InnoDB. App database credentials remain in server-private `.env`.
- Apache proxies only the Brijvas virtual hosts. Existing Let's Encrypt certificate remains in use.
- Redis database 7 supplies shared public-write rate limits.
- Original `/var/www/brijvas` application and original database remain untouched by schema migration.
- Final backup: `/root/brijvas-backups/20260910T045048Z-cutover/` contains database, media and previous Apache configurations with private permissions.
- Preserved at cutover: 4 users, 12 properties, 1 blog, 31 contacts, 0 property enquiries. Property IDs, slugs and featured-image references matched before and after migration; existing image files were verified in the new upload root.

Tests covered tenant isolation, permissions, limits, uploads, payment verification and content sanitization. Actual MySQL concurrency checks verified a single remaining listing slot and idempotent duplicate payment settlement. Production-config signup with CSRF, a new path website, dashboard and cross-business denial passed in a rolled-back transaction; no synthetic customer was left in production.

Public HTTPS portal, signup and existing storefront were inspected in a browser. Unknown tenant URLs return 404. The application service was active and no service errors were recorded after cutover.

## Remaining integrations

- Configure independent Razorpay credentials, webhook secret and approved plan prices; then run provider sandbox and real settlement checks. Current billing supports one-time 30-day periods, not automatic recurring mandates or tax invoicing.
- Configure SMTP and test actual email delivery. Until then, recovery displays an explicit unavailable message. In-memory email/template tests do not establish real delivery.
- Wildcard DNS/certificate and custom-domain proxy/TLS activation remain separate operations. Path-based websites already work; automatic custom-domain issuance is not implemented.
- Google OAuth is disabled until callbacks and account handoff are configured.
- Schedule off-server backups, restore drills and operational monitoring. Current private server backups protect this migration but are not an off-server backup service.

## Safe maintenance

For source-only updates: review changes, push to GitHub, pull in the new application directory, run applicable checks and restart only `brijvas-saas`. Preserve `.env` group ownership `root:www-data` and mode 0640 after dotenv edits. Migrations require a fresh backup and compatibility review.

Do not blindly restore the old Apache configuration after new customer writes have been accepted: those writes now exist in the new database. A rollback requires a maintenance window and reconciliation of post-cutover writes. Never point old unscoped code at the multi-tenant database.

## Platform domain separation

The platform is now `https://propertystudio.live-app.in/`. Its dedicated certificate is issued with Certbot webroot and automatic renewal. Apache's `00-propertystudio.conf` must sort before the existing unrelated `*.live-app.in` HTTP wildcard so ACME challenges reach this application.

`brijvas.com` and `www.brijvas.com` serve only the verified existing Brijvas tenant. They are no longer platform hosts. Management GET links redirect to the platform; management POST requests must be submitted on the platform itself. Sessions remain host-only: sign in separately when opening the Brijvas property dashboard. Existing account passwords are unchanged.

The platform root has no default tenant. New customer websites use its `/sites/<slug>/` path. Brijvas retains its primary public URL `https://brijvas.com`.
