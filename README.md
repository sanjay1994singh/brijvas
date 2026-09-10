# Vistaflo — Brijvas Property SaaS

Multi-tenant Django property websites with trial provisioning, business administration, listing approvals, tenant branding, enquiries, team roles, plan limits, Razorpay adapter and verified domain routing.

## Local development

Use Python 3.12+ and a dedicated virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force .dev
.\.venv\Scripts\python.exe manage.py migrate --settings=brijvas.settings_dev
.\.venv\Scripts\python.exe manage.py create_demo --settings=brijvas.settings_dev
.\start-dev.ps1
```

`create_demo` prints a random local-only password on first creation; repeated runs do not reset it. Local development uses `.dev/saas.sqlite3` and `.dev/media/`, independently of the existing MySQL database and customer media. No production database migration was performed during development.

- Platform: http://localhost:8000/
- Signup: http://localhost:8000/saas/signup/
- Demo site: http://demo-realty.localhost:8000/
- Business administration: http://localhost:8000/saas/workspaces/
- Website listing dashboard: http://demo-realty.localhost:8000/dashboard/

Host-only cookies mean the platform and each customer website have separate sign-in sessions. Use the same account credentials when opening your website dashboard. Modern browsers resolve `*.localhost` to loopback; if a local resolver does not, configure those development hostnames explicitly.

## Verification

```powershell
.\.venv\Scripts\python.exe manage.py test saas --settings=brijvas.settings_test
.\.venv\Scripts\python.exe manage.py check --settings=brijvas.settings_dev
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=brijvas.settings_test
```

Tests use an isolated in-memory database and temporary upload directory. Coverage includes independent businesses, foreign IDs and form choices, transaction rollback, payment signature/amount checks, payment replay, uploads, quotas, member permissions, signup, listing creation and branding.

## Plan behavior

Starter, Agency and Business are seeded as configurable trial plans. Prices default to zero and online checkout remains disabled until the administrator sets commercial prices and gateway credentials. Prices are integer paise; subscription periods in this version are exactly 30 days, not calendar months. This is one-time checkout with manual renewal, not a recurring payment mandate. Plan switching starts a fresh period without proration; the checkout screen discloses this.

Listing limits count all listings, including unpublished submissions. Staff limits cover approved owner/admin/agent memberships. Buyers and sellers are not staff seats. New uploads are limited by the tenant media directory usage; legacy pre-migration files are not included in that directory-based meter. Profile-image uploads are disabled until tenant-specific profile storage is implemented. Platform administrators are trusted operators and can manage plans/subscriptions through `/admin/`; customer administrators cannot enter global Django admin.

## Production status

The local application and tests are runnable. Production launch still requires the deployment checklist below, real MySQL validation, credentials and DNS/TLS setup. Custom-domain ownership verification and TLS readiness activation are implemented; automatic certificate issuance/renewal workers are not included. Do not advertise unattended custom-domain provisioning until infrastructure automation is installed and verified.

See [deployment and migration runbook](docs/property-saas-deployment.md) and [original architecture analysis](docs/saas-conversion-analysis.md).
