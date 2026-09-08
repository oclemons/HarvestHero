# Harvest Hero — Web Application

Browser-based UI for the pantry inventory system. Lives in this
subdirectory so the existing Windows desktop app (in the repo root)
keeps building and shipping while we bring the web app up in parallel.

Once the web app reaches feature parity, the desktop app is deprecated
and users switch to the URL.

## What this is (Phase 0)

Scaffold only. A working Flask app that:

* Talks to the same SQLite schema as the desktop app via ``database.py``
  in the repo root — so if you pointed both at the same file, they'd
  agree on inventory.
* Renders login and a placeholder dashboard.
* Ships with Tailwind + HTMX preloaded so building screens is fast.
* Runs locally with ``flask run`` and on Fly.io with ``flyctl deploy``.

The remaining screens (add/edit item, barcode scan, shopping list,
reports, users, shelves, weights, …) get added phase by phase — see
``../WEB_APP_ROADMAP.md``.

## Running locally

```
cd web
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app.py
export FLASK_ENV=development
export HARVESTHERO_SECRET_KEY=dev-only-not-for-production
flask run --port 5001
```

Open http://localhost:5001 . Log in with whatever admin account the
desktop app created for you (same database).

## Deploying to Fly.io

See ``../WEB_APP_ROADMAP.md`` for one-time setup. Once configured:

```
flyctl deploy
```

Live URL: (TBD once you register the domain and deploy)
