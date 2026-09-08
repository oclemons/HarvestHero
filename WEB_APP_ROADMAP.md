# Harvest Hero Web App — Roadmap

Decided: rebuild the pantry app as a browser-based web app hosted on
Fly.io so (a) the data is always available and always backed up, and
(b) fixing an issue is one deploy, not "please install the update on
every pantry PC."

This document is the single source of truth for what's built, what's
next, and what got left on the desktop app.

---

## Current state — Phase 0 (this session)

**Scaffold only. Runs. Nothing real inside yet.**

* `web/` subdirectory holds a Flask + Jinja + HTMX + Tailwind app.
* Reuses the desktop app's `database.py`, `auth.py`, `paths.py`
  unchanged — same schema, same password hashing.
* Login and a placeholder dashboard render. Logging in against the
  desktop app's sqlite file works.
* `Dockerfile` + `fly.toml` are ready.  A one-line `flyctl deploy`
  puts it on the internet.
* The Windows desktop app in the repo root is untouched. It still
  ships from `HarvestHero.spec` + Inno Setup, still auto-updates
  from GitHub Releases. This gives us a fallback while the web app
  matures.

---

## What YOU need to do before Phase 1

Three one-time chores. I can't do these — they need your credit card
and your identity.

### 1. Register a domain

Recommendations (check availability on Namecheap / Cloudflare / Porkbun):

| Option | Vibe | Approx. cost / yr |
|---|---|---|
| `harvesthero.org` | Nonprofit / community-forward | $12 |
| `harvesthero.app` | Modern SaaS | $18 |
| `pantryhero.app` | Product-focused | $18 |
| `getharvesthero.com` | Classic .com fallback | $13 |
| `harvest-hero.io` | Tech vibe | $40+ |

Pick whichever fits your brand.  Buy it wherever you like — I recommend
Cloudflare Registrar (at-cost pricing, no upsells).

### 2. Sign up for Fly.io

```
brew install flyctl
flyctl auth signup
```

You'll need a credit card, but the free tier covers our current needs:
3 shared-cpu-1x/256mb machines, 3 GB of persistent volume storage, 160
GB/mo of outbound bandwidth. A pilot pantry stays under this
comfortably.  Expect $0/mo for pilot, $5–15/mo once you have real
traffic.

### 3. Tell me the two names above

Once you have the domain and a Fly.io account, tell me:

* Domain you registered.
* Fly.io org name (usually your username).
* Which region you want the app in (`iad`=US East, `sea`=US West,
  `lhr`=London, etc. — pick the one closest to your pantries).

Then I run `flyctl launch`, deploy Phase 0, and give you back a live
URL.

---

## Phased delivery

Every phase ends with a working, deployed URL.  If you decide to stop
partway through, the app is still usable at whatever level of parity
we reached.

### Phase 0 — Scaffold (this session)
* [x] Flask app runs locally
* [x] Dockerfile + fly.toml
* [x] Login + placeholder dashboard
* [x] Deploy-ready (needs Fly.io account to actually deploy)

### Phase 1 — Login + Read (~1 week)
* Real dashboard: item count, low stock, out of stock, active users.
* Inventory list with search, pagination, and view-item detail page.
* User profile page.
* Log everything sensitive to an audit table (already exists in db).

### Phase 2 — Write (~1 week)
* Add item, edit item, delete item (admin).
* Barcode scan-in / scan-out screen with keyboard-scanner focus.
* Shopping list (auto-populated from low stock).
* CSV export of inventory.

### Phase 3 — Ops (~3–5 days)
* User management (admin creates/edits/disables users, resets pwds).
* Shelf manager.
* First-time admin account bootstrap flow.
* "Forgot password" email flow (Postmark or Mailgun, free tier).
* Basic reports: low stock, out of stock, expiring, movement history.

### Phase 4 — Polish (~1 week)
* Weight / pounds tracking.
* Pantry visual view (grid of sections + shelves).
* AI assistant (Ava).
* Advanced reports with charts.
* Onboarding tour.

### Phase 5 — Wind down desktop (~2–3 days)
* Freeze Windows installer at 2.1.1.  Push a final v2.1.2 whose only
  change is to display a "Harvest Hero has moved to the web — visit
  https://your-domain to sign in" banner on the login screen.
* Data-migration tool: pantry admin exports their existing DB and
  uploads it via a special web endpoint.  Web app merges.
* Update `README.md` to point at the web app.

---

## Architecture notes for future me

### Why Flask + Jinja + HTMX + Tailwind
* Zero JS build pipeline — no npm, no webpack, no bundler churn.
* Server-rendered HTML means barcode-scanner focus management works
  the same way as any keyboard input, and accessibility is baked in.
* HTMX gives us modern "swap a fragment" UX (edit-in-place, live
  filter, infinite scroll) without a SPA.
* Tailwind lets us skip naming CSS classes and iterate on layout
  quickly.  Once things settle we ship a pre-built stylesheet instead
  of the CDN.

### Why keep the Database class instead of SQLAlchemy
* Zero-cost reuse of a battle-tested schema and its migrations.
* Two front-ends over one class means fewer sources of truth.
* If we ever migrate to Postgres, we do it once inside `database.py`
  and both the desktop app and the web app get it.

### Why Fly.io
* Free tier fits a pilot pantry.
* Simple `flyctl deploy` model — no cluster to manage.
* Persistent volumes so sqlite works fine in production (moving to
  Postgres later is a `flyctl postgres create` away).
* TLS is automatic.  Bring-your-own-domain in one command.

### Why deprecate the desktop app instead of running both forever
* Every screen doubles our maintenance surface if both UIs exist.
* Sync between two authoritative databases is a real project by
  itself.
* Once web app has feature parity, "just go to this URL" is a
  simpler onboarding story than "download an installer and update
  it every few weeks."

---

## Rollback plan

If the web app doesn't work out, the desktop app is untouched on
`main` and still builds/ships via GitHub Actions.  Anyone on 2.1.1
keeps running and receives future patches through the existing
auto-updater.  We can `rm -rf web/` and forget the pivot happened.
