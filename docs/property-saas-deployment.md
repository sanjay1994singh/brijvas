# Deployment and existing-customer migration

## Release boundaries

Development changed source files in the current Brijvas workspace. NewsWebSaas was used as architectural reference, not overwritten. Existing customer MySQL data, media and live DNS were not migrated. Never deploy this code against an unmigrated customer database.

## Staging first

1. Create a separate checkout, MySQL database/user and upload root. Install `requirements-production.txt` and use a production secret. Configure `.env` from `.env.example` without committing credentials.
2. Restore a customer database/media backup into staging and verify restore integrity before running migrations. Do not run `create_demo` outside the isolated SQLite development environment.
3. Record model counts, existing property/blog URLs, users and file references. Run `manage.py migrate --plan`, then `manage.py migrate` on staging.
4. Migration `saas.0002_backfill_brijvas` assigns all existing business root records to Brijvas, preserves IDs/slugs/media paths and maps users to Brijvas memberships. It refuses multiple legacy SiteSetting rows rather than deleting or guessing. Resolve that condition manually if present.
5. The legacy Brijvas plan preserves existing access with a long expiry; review its limits and commercial terms explicitly. Run `manage.py assign_business_owner brijvas EXISTING_USERNAME` to designate the customer owner. Global staff flags do not automatically grant tenant management privileges.
6. Run the test suite on a dedicated MySQL test database, not production. Verify concurrent signup, quota checks and payment retries using MySQL/InnoDB before launch. SQLite tests do not establish database lock behavior in production.
7. Rehearse two-tenant isolation and restoration. Existing old code must not be restarted against multi-tenant data after cutover: it has unscoped queries. Rollback needs a coordinated old-code/database backup restore and reconciliation of writes accepted after cutover.

## Host routing and HTTPS

- Choose a platform domain and set SAAS_BASE_URL, SAAS_PLATFORM_HOSTS and SAAS_DOMAIN_TARGET consistently.
- Configure wildcard DNS and wildcard certificate for customer subdomains. Route the base domain and its subdomains to the same app with the original validated Host header.
- Keep `ALLOWED_HOSTS` restricted to the platform suffix and explicitly onboarded custom hosts. Update deployment configuration when adding custom domains; unknown hosts must not bypass application routing checks.
- Terminate HTTPS at a trusted reverse proxy. Only set Django SECURE_PROXY_SSL_HEADER when that proxy strips incoming forwarded headers and sets its own. Without it, use TLS to Django or configure the trusted proxy deliberately to avoid redirect loops.
- Customer adds domain in the dashboard and publishes its TXT token; `Check ownership` verifies DNS.
- Operations configures DNS routing and certificate issuance/renewal outside Django. After this, run `manage.py activate_domain customer.example` to validate public TLS and activate its primary route. This command does not issue certificates and does not prove the reverse proxy routes to the correct application; confirm the branded page in browser afterwards.
- Existing Brijvas custom domains must be added and verified through this flow in staging/cutover. Do not assume DNS ownership or enable a domain based solely on its spelling.
- Serve public media with a static server on a separate non-executable origin/path, block directory listing and scripts, enforce upload size limits. The app currently stores local filesystem media; shared storage is required before adding multiple app hosts.

## Payments and email

- Configure independent Razorpay keys and webhook secret for the property product. Do not reuse another project's keys blindly.
- Set actual plan prices via platform admin. Verify business pricing/currency and required commercial disclosures before enabling checkout.
- Register webhook `/saas/webhook/razorpay/` for `payment.captured` and `order.paid`.
- Sandbox-test valid payment, invalid signature, failed/cancelled payment, duplicate delivery, captured-payment reconciliation and renewal. Local tests mock provider calls; no real transaction was performed.
- BillingOrder provides payment history, not a tax invoice or complete accounting system. Tax/invoicing and customer terms must be configured before commercial rollout.
- Configure SMTP and test password recovery. Outbound welcome notifications and durable notification jobs are not included in this version.
- Google OAuth is disabled by default. A cross-domain account handoff flow has not been implemented; enable only after reviewing callback and tenant membership behavior.

## Operations

Use a dedicated application service user, supervised Gunicorn process and reverse proxy. Keep database credentials and backups out of web roots. Run `manage.py check --deploy` using actual production settings. Add proxy rate limits for signup, sign-in, password recovery, enquiry submission and domain verification before public exposure. Configure error monitoring, database/media backup schedules, restore drills and TLS renewal alerts.

For initial rollout, use one app host with durable local media and MySQL/InnoDB. Directory-based media accounting scans tenant files and is intended for initial scale; a durable usage ledger/object storage inventory is needed before large-scale deployment. Failed database transactions can leave uploaded files requiring an orphan-file reconciliation job; automatic orphan cleanup is not implemented.

## Launch acceptance

- Existing Brijvas data counts, URLs, images and enquiries preserved.
- Two different businesses cannot access each other's private records or management screens.
- New signup produces a complete independently branded website.
- HTTPS works on wildcard and approved custom hosts, including renewal monitoring.
- Razorpay sandbox flow, SMTP recovery and production configuration checks pass.
- MySQL tests/concurrency, backup restore and cutover/rollback rehearsals pass.

Until these checks are completed, treat this as a locally verified application release, not a certified production deployment.
