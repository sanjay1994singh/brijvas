# Brijvas → Property Website SaaS: code analysis and implementation blueprint

Date: 10 September 2026. Language: Hinglish.

## Nateeja

Brijvas ko multi-tenant property website SaaS banana feasible hai. Recommended approach: Brijvas ka property product preserve karein, NewsWebSaas se audited SaaS components adapt karein, aur separate property SaaS deployment banayein. Existing Brijvas business uska pehla tenant hoga. News aur property products ka production database/deployment merge karna is phase mein zaroori nahi hai.

Ek customer = ek real-estate business/agency = ek tenant. Us customer ke sellers, agents aur buyers us tenant ke users hain. Current `User.user_type='owner'` ka matlab property seller hai; ise SaaS business owner samajhna galat hoga.

Instant delivery ka matlab: signup/payment ke baad ready platform URL, dashboard aur default website. Custom domain activation DNS aur certificate readiness par depend karega. Native Android/iOS apps is analysis ka scope nahi; user ke existing Django web app ko SaaS banana scope hai.

## Review scope aur evidence limits

Actual news directory `C:/django_project/InfoSaas/NewsWebSaas` mili; supplied `C:/django/_project/InfoSaas/NewsWebSaas` exist nahi karti. Property directory `C:/django_project/brijvas/brijvas` hai.

Models, views, forms, middleware, auth helpers, URL routing, context processors, SEO/sitemaps, media cleanup, subscription provisioning/payment services, domain services, test source, requirements aur deployment documentation inspect kiye. `.env` secrets read nahi kiye. Live server, actual DB contents, billing delivery, DNS, TLS, traffic/capacity aur test suite execute karke verify nahi kiye. Findings static code review par based hain; project ka self-description production readiness ka proof nahi maana gaya. Application code ya customer data change nahi hua.

## NewsWebSaas mein kya reusable hai

Paths below news project ke relative hain.

| Component | Code evidence | Property SaaS mein use |
|---|---|---|
| Tenant lifecycle | `tenants/models.py`: Tenant status, onboarding status, owner | Business workspace identity; publication-specific names adapt karein |
| Membership | TenantMembership, tenant/user uniqueness, active/suspended membership | Business owner, admin, agent, manager roles |
| Visitor separation | TenantVisitor separate from staff membership | Buyer/seller participation ko SaaS administration se separate rakhein |
| Request routing | `domains/middleware.py`: host → TenantDomain → request.tenant | Domain ke hisaab se property website |
| Query/form/view helpers | `core/models.py`: for_tenant, scoped form/view mixins, access helper | Listing, lead, category aur staff access scoping |
| Commercial catalog | `subscriptions/models.py`: Plan, Feature, PlanFeature, AddOn, overrides | Listings, storage, staff, custom domain aur optional product capabilities |
| Billing lifecycle | TenantSubscription, BillingRecord, entitlement snapshots | Subscription periods, renewals aur purchased-feature history |
| Checkout provisioning | `subscriptions/services.py:create_tenant_after_verified_subscription` | Verified acquisition se tenant, membership, subscription, pages/domain create karna |
| Transaction protection | Atomic services, acquisition row lock, existing-tenant handling | Repeated checkout callbacks se duplicate workspace avoid karne ka pattern |
| Webhooks | Signature verification; unique provider/environment/event ID | Verified event processing aur retry protection |
| Publishing policies | OnboardingAutomationPolicy: instant/manual/delayed | Ready site auto-publish; optional manual review |
| Domain verification | DNS TXT token verification, domain ownership check | Customer custom-domain onboarding |
| Test examples | `tenants/tests.py`, subscription and webhook tests | Two-tenant isolation, foreign IDs, payment retries aur feature enforcement tests adapt karein |

News-specific articles, epaper, live TV, newsroom roles, news entitlement defaults, templates, seed plans, support branding aur legal text ko wholesale copy nahi karna. `core` aur `accounts` dono projects mein already exist karte hain; directories/migrations overwrite nahi karein. Property project ka existing custom user model preserve karke memberships add karein.

## News foundation ko adapt karne se pehle gaps

1. **Query helpers automatic isolation nahi hain.** `TenantAwareManager.get_queryset()` normal unfiltered queryset return karta hai. `.for_tenant(tenant)` explicitly call karne par filtering hoti hai; `.objects.all()` ab bhi all tenants return karega. Tenant-owned request paths ke liye missing context reject karein, mandatory service scoping aur cross-tenant tests use karein. Platform admin ke global access ko explicit rakhein.
2. **SSL queue function incomplete hai.** `domains/services.py:enqueue_ssl_provisioning()` status/timestamp save karta hai; actual worker enqueue ya ACME issuance call us function mein nahi hai. `docs/nginx-certificate-automation.md` proposed infrastructure describe karta hai. Dependencies mein Celery/Redis hona working certificate automation ka proof nahi.
3. **Resolver ko stricter boundary chahiye.** Reviewed middleware active domain/status check karta hai, lekin `is_verified` query condition nahi hai. Creation service inactive domain banati hai, phir verification activate karti hai; fir bhi middleware ko independently verified domain require karna chahiye. Unknown host par `request.tenant=None` rehta hai: property SaaS ko allowlisted platform host aur unknown/suspended customer host explicitly distinguish karne honge.
4. **Primary-domain concurrency.** Model `clean()` ek primary domain check karta hai, service other domains unset karti hai. Concurrent requests ke liye tenant-row locking jaisi serialization add karein; application validation alone ko database invariant na samjhein.
5. **Provisioning slug collision.** Tenant creation service slug par `get_or_create()` karti hai aur returned tenant ke owner ko is block mein validate kiye bina membership banati hai. Acquisition slug unique hona existing tenant slug ownership ka proof nahi. Collision reject/reserve karein; manually seeded tenants aur concurrent signup test karein.
6. **Media organization incomplete as a generic SaaS guarantee.** Onboarding logos generic `tenant-branding/logos/` paths par hain; optimized storage image compression karta hai. Tenant-scoped records, paths aur private-file authorization separately design karne honge.
7. **News naming deeply embedded hai.** Provisioning defaults mein newsroom tagline, news pages aur news entitlements hain. Business defaults ko property onboarding service mein replace karein.

In points ko confirmed production exploits nahi maana gaya; reviewed code ki boundaries aur adaptation risks hain.

## Brijvas mein concrete conversion work

| Current evidence | SaaS mein impact | Required change |
|---|---|---|
| `properties/models.py`: Property has user, no tenant | User ownership business isolation nahi deta | Required tenant FK; user relation retain |
| `accounts/models.py`: global owner/agent/buyer, is_verified | Ek site ki seller approval doosri site mein reuse ho sakti hai | Tenant-specific participant role/approval |
| `dashboard/views.py`: user filters and global staff checks | Owner cannot safely represent whole agency; global privileges too broad | Tenant membership + permission + object scope |
| `core/context_processors.py`: SiteSetting.objects.first() | Har website same settings le sakti hai | One settings row per tenant |
| Public listing/search/detail/related queries unscoped | Multiple customers add karne par data mixing | Tenant filter on every entry point, including slug similarity fallback |
| SiteSetting, Contact, Blog/Category no tenant | Branding, contacts/blog content mix | Explicit tenant ownership |
| Property/Blog/Category slug unique globally | Customers same independent URL slug use nahi kar sakte | Unique(tenant, slug); slug generator bhi scope karein |
| `core/seo.py:site_base_url()` prioritizes global SITE_URL | Canonical/share URLs Brijvas par point karenge | Verified primary tenant domain per request/job |
| `properties/sitemap.py`, `blog/sitemap.py` global queries | Foreign listings search engines ko expose honge | Tenant-specific sitemap instances and canonical URLs |
| `templates/base.html`, model-generated description, admin labels | New customer's site mein Brij Vas branding | Tenant branding and safe defaults |
| Generic media paths and global cleanup signals | Migration/shared seed references mein accidental deletion risk | Tenant namespaces, ownership checks, commit-safe cleanup |
| CKEditor upload permission only authenticated in settings | SaaS role/tenant/quota enforcement demonstrated nahi | Tenant-authorized upload endpoint and limits |
| Reviewed tests are placeholder files | Current flows ka automated regression baseline nahi | Before migration, meaningful regression/isolation suite |

Additional existing behavior: `dashboard/views.py:delete_property()` HTTP method guard ke bina delete karta hai. SaaS release se pehle POST-only mutation + CSRF protection enforce karein. `PropertyForm` tenant parameter nahi leta; tenant field add hone par exclude-based form use karna especially risky hai. Explicit permitted fields aur server-side tenant assignment use karein.

## Proposed data model

| Scope | Models/design |
|---|---|
| Platform/global | User identity, Plan, Feature, PlanPrice, payment event registry, global geography |
| Tenant root | Tenant, TenantDomain, TenantMembership, TenantSubscription, TenantSiteSetting, ProvisioningJob |
| Tenant-owned business records | Property, PropertyType, Amenity, Blog, BlogCategory, Contact; optional future lead workflow |
| Property children | Gallery, Video, Enquiry, Review, View, PropertyAmenity: derive tenant through property; query using property__tenant |
| Blog children | Comment/View: derive tenant through blog |
| User participation | TenantParticipant(user, tenant, role, approval status); Wishlist/Compare bounded by property's tenant and current user |

Child records can use parent ownership without duplicating tenant FK. Agar reporting/performance ke liye child par tenant store ho, parent-child mismatch reject karne ka invariant zaroor banayein. Tenant-owned Amenity/PropertyType select karte waqt property tenant match validate ho. Global State/City read-only master data rakhein; customer service areas ke liye separate tenant-location link add karein.

Suggested indexes: Property(tenant, is_active, created_at), Property(tenant, city, purpose), Blog(tenant, is_published, created_at). Query plans aur traffic ke basis par refine karein. Tenant+slug database uniqueness ke saath concurrent slug collision retry handle karein. Django supports multi-field [UniqueConstraint](https://docs.djangoproject.com/en/5.2/ref/models/constraints/).

## Architecture decision

Recommended MVP: shared application + shared MySQL database + explicit tenant ownership. Dono projects MySQL-oriented hain; sirf SaaS conversion ke liye database engine replace karna necessary nahi.

| Option | Benefit | Cost/tradeoff | Decision |
|---|---|---|---|
| Shared tables with tenant ownership | Fast signup, one deployment and migration stream | Application scoping must be comprehensive; per-tenant restore needs tooling | Recommended first version |
| Database per customer | Stronger storage boundary, easier isolated DB restore | Per-customer migrations, connections and provisioning operations | Later enterprise offering if required |
| Full app deployment per customer | Maximum customization/operational separation | Fleet upgrades and capacity management per customer | Optional managed hosting product |

Keep News SaaS and Property SaaS as separate products initially. Reuse reviewed source patterns with fresh integration migrations; shared internal package extraction can follow once both implementations stabilize. Brijvas visual design becomes first property theme.

Suggested module responsibilities: `tenants` for identity/membership; `domains` for routing/ownership; `subscriptions` for pricing/entitlements; `onboarding` for property-site provisioning; existing `core` for tenant site configuration/public pages; existing product apps for property workflows. Keep platform operations and customer dashboard distinct. A customer admin must not receive Django superuser powers.

## Instant delivery flow

1. Customer enters business name, contact, site slug and selects plan. Reserve slug transactionally; prevent collision with existing tenants/reserved platform routes.
2. Create checkout with backend-calculated amount/currency. Provision paid access only after server-side verified payment. Customer callback parameters alone are insufficient.
3. Persist a provisioning job/idempotency key tied to acquisition. Lock acquisition; retry must return same tenant.
4. Create tenant, owner membership, subscription snapshot, site settings, Brijvas-derived theme, default pages, property types, and platform domain. No real Brijvas listings or customer information in seed data.
5. Mark application provisioning ready after required records exist. Send welcome/setup link after transaction commit through a retryable outbox/worker. Failed notification must not undo successful payment/site creation.
6. Return website URL + tenant dashboard. User can update logo/contact and publish first property. Listing approval is a separate tenant-controlled workflow from SaaS business onboarding.
7. Custom domain wizard: ownership TXT check, traffic DNS instructions, worker-driven TLS provisioning, HTTPS health check, then primary-domain switch. Preserve platform URL while pending.

Platform domain example `agency.platform.example` is illustrative, not a chosen domain. Preconfigure wildcard DNS and wildcard TLS for that platform zone. Let's Encrypt wildcard issuance uses DNS-01; customer custom domains still need their own certificate/validation workflow. [Official challenge documentation](https://letsencrypt.org/docs/challenge-types/).

Track provisioning states pending/running/ready/failed, last completed step, retry count/error and timestamps. Use durable jobs for external effects, timeouts/backoff and operator retry. Do not promise a delivery time before measuring full flow; eventual acceptance criterion can be a measured percentile from successful payment to ready platform site.

Authentication: keep cookies host-only by default; arbitrary custom domains cannot share a parent-domain cookie. Choose central dashboard login and tenant-local public login initially. Google OAuth currently uses global credentials; per-domain callbacks need an explicit central login/handoff design with signed, short-lived, single-use tenant-bound tokens if cross-domain SSO is required.

## Subscription packaging

Suggested dimensions, not final commercial pricing: active listings, staff seats, storage, images per property, custom domain, theme access, analytics, optional lead assignment/export/API. Starter/Agency/Business names can be used for discussion; rates and quotas should follow actual operating cost and customer demand.

Every limit must be enforced in backend services across create/edit/import/API/upload paths. Concurrent creates need locked quota counters or equivalent serialization. Define active-listing count precisely; drafts/archived items and storage accounting need explicit policy. Downgrade should preserve data while limiting new writes or premium features according to agreed rules. Expiry/grace/restriction/renewal behavior must be defined for both dashboard and public site.

Lead stage, assignment, notes, follow-up reminders and CSV export can form a later CRM tier. Current Enquiry is a basic name/contact/message record; full CRM is not an existing feature.

## Existing Brijvas migration

1. Preserve existing deployment. Create separate SaaS development/staging environment with pinned dependencies and a reproducible configuration. Never point staging migration tests at production DB.
2. Back up database and media; perform an actual restore drill before cutover. Capture counts, primary keys, relationships, URLs and file references.
3. Add Tenant and memberships; create Brijvas tenant/domain/settings mapping. Add nullable tenant columns to root business tables first.
4. Backfill current Brijvas records explicitly. Seller/agent/buyer role maps to Brijvas participant; verified status migrates for Brijvas only. Create SaaS owner membership separately. Review current staff accounts instead of blindly granting platform access.
5. Validate every root row assigned once, child relationships valid, no orphan file references, counts unchanged. Existing primary keys and slug values remain intact.
6. Add tenant indexes/constraints, then enforce non-null root ownership. Drop global slug uniqueness only after tenant uniqueness exists. Migrate scoped application reads/writes in coordinated release stages.
7. Preserve existing media URLs initially; new uploads use `tenants/<immutable-id>/...`. Do not relocate all media during the same DB migration. Existing cleanup signals need adjustment before copying shared default assets or bulk replacements.
8. Two-tenant acceptance tests in staging: Brijvas plus synthetic customer. Compare Brijvas public pages, forms, uploads, enquiries, canonical URLs and sitemaps against baseline.
9. Short write freeze or controlled final sync, reconcile data, cut over Brijvas domain, run smoke checks. Define rollback before accepting new writes: old app cannot safely resume on multi-tenant data without isolation; restoration must account for post-cutover writes.

## Delivery phases and exit criteria

| Phase | Deliverable | Exit criterion |
|---|---|---|
| 0: baseline | Dependency inventory, regression fixtures, staging backup restore | Existing key customer flows repeatably verified |
| 1: isolation | Tenant models, roles, scoped forms/services/public routes/admin | Two customers cannot read/write each other's data |
| 2: website configuration | Branding, tenant SEO, default theme, media boundary | New synthetic tenant renders independently on platform host |
| 3: onboarding | Provisioning service, plans/payment verification, retry state | Repeated payment events create one complete site |
| 4: operations | Domain/TLS worker, renewals, quotas, expiry, audit/backup | Failures observable/retryable; restore and access tests pass |
| 5: migration | Brijvas backfill and cutover rehearsal | Data/URLs preserved; approved release rollback procedure |

Do not attach fixed dates to these phases without runtime/test/infra baseline. First concrete implementation milestone should be two isolated businesses using existing property workflows; payment integration follows that foundation.

## Required release verification

- Tenant A cannot view/edit/delete B listings using guessed ID, slug, similar-slug fallback, form foreign keys or URLs. Test anonymous, buyer, seller, agent, tenant admin and platform admin separately.
- Search, related listings, counts, blog, contacts, enquiries, wishlist/compare, sitemaps, feeds/exports and cache entries contain current tenant data only.
- Missing/unknown/unverified host fails closed; suspended tenant must not fall through to platform content. Host/forwarded-host trust restricted to actual proxy boundaries.
- Duplicate tenant slugs across independent model categories behave correctly; identical listing slugs across different tenants work; same-tenant duplicate creation fails safely.
- Payment duplicate/reordered callbacks, webhook retry, amount/order mismatch, worker timeout and failed mail do not create duplicate tenants/credits or falsely ready sites.
- File upload foreign IDs and quota bypass fail; tenant branding is independent; private documents cannot be downloaded by another tenant. Public listing photos being public is expected.
- Subscription expiry, renewal and downgrade rules behave consistently in API, dashboard and background jobs. Cache keys carry tenant identity and appropriate configuration versions.
- Restore one tenant without modifying another in a rehearsal; media cleanup cannot delete files still in use or execute destructive file work before DB commit.
- Existing Brijvas URLs, property ownership, enquiries, Google login behavior, image optimization and SEO remain functional after migration.

No capacity number, production-safety certification or test-pass result is claimed by this static analysis.
