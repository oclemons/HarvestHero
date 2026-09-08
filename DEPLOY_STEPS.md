# Deploy Harvest Hero to harvestheropantry.com

Copy-paste-runnable steps to get the web app scaffold live at
`https://harvestheropantry.com` on Fly.io, using a Cloudflare-managed
domain and a Fly.io account you already own.

Total time: **~20 minutes**, most of it waiting for DNS to propagate
and Fly.io to issue a TLS certificate.

Everything happens from the `web/` subdirectory of this repo unless
noted otherwise.

---

## 0. One-time: install flyctl and log in

If you already ran `brew install flyctl` and `flyctl auth login`, skip
to step 1.

```bash
brew install flyctl

# Opens your default browser and logs you in as octayvia-clemons@gmail.com
flyctl auth login

# Sanity check — should list your org and email
flyctl auth whoami
```

---

## 1. Launch the app on Fly.io (does not deploy yet)

```bash
cd /Users/octayviaclemons/CascadeProjects/inventory_tracker/web

flyctl launch \
    --name harvest-hero-pantry \
    --region iad \
    --org personal \
    --copy-config \
    --no-deploy \
    --yes
```

> **Important — build-context rule.**
> Every subsequent `flyctl deploy`, `flyctl volumes …`, and
> `flyctl secrets …` command must be run **from the repo root**
> with `--config web/fly.toml` (or the Dockerfile can't see
> `database.py` / `auth.py` / `paths.py` in the root). Only
> `flyctl launch` runs from `web/` because it needs to write
> the fly.toml next to itself.

* `--name` fixes the default subdomain to `harvest-hero-pantry.fly.dev`.
  Changing this later means changing DNS too; pick once.
* `--region iad` is Ashburn, VA (US East). If your pantries are on the
  US West coast, use `sea` (Seattle) or `lax` (Los Angeles).
  [Full list](https://fly.io/docs/reference/regions/).
* `--copy-config` uses the `fly.toml` already in this folder.
* `--no-deploy` because we need to provision the volume and set the
  secret key before the first deploy, otherwise the app boots against
  an empty ephemeral filesystem and the admin bootstrap won't stick.

---

## 2. Create the persistent volume for the SQLite database

```bash
cd /Users/octayviaclemons/CascadeProjects/inventory_tracker

flyctl volumes create harvest_data \
    --config web/fly.toml \
    --size 1 \
    --region iad \
    --yes
```

* Same region as the app. **Do not change this later** without a
  data-migration plan; Fly.io machines can only mount volumes in
  their own region.
* 1 GB is way more than enough for a pantry's inventory database. If
  you ever need more, resize with `flyctl volumes extend`.

---

## 3. Set the session secret

Sessions signed with a random per-process key would log everyone out
on every deploy. Set a persistent one:

```bash
flyctl secrets set \
    --config web/fly.toml \
    HARVESTHERO_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

Verify it's stored (value is redacted):

```bash
flyctl secrets list --config web/fly.toml
```

---

## 4. First deploy

```bash
# From the REPO ROOT, not from web/.
cd /Users/octayviaclemons/CascadeProjects/inventory_tracker

flyctl deploy \
    --config web/fly.toml \
    --dockerfile web/Dockerfile
```

The `--config` and `--dockerfile` flags together make flyctl:
* use `web/fly.toml` for the app config
* use `web/Dockerfile` for the build recipe
* use the **repo root** as the Docker build context, so the
  `COPY . /app` line can see `database.py`, `auth.py`, `paths.py`,
  and the `web/` subdirectory in one go.

If you run `flyctl deploy` from inside `web/` without those flags,
the build context is `web/` and the Dockerfile fails at step [4/5]
with `Could not open requirements file /app/web/requirements.txt`.
That's the symptom of the wrong build context.

Takes 2–4 minutes: builds the Docker image, uploads it, boots a
machine, mounts the volume, starts gunicorn.

When it finishes:

```bash
flyctl status                                       # machine should be "started"
curl https://harvest-hero-pantry.fly.dev/healthz    # should return {"ok":true,...}
```

Open `https://harvest-hero-pantry.fly.dev/login` in your browser — you
should see the Harvest Hero login form.

---

## 5. Get the bootstrap admin password from the logs

The first-launch code auto-creates an `admin` user and prints the
random password to stdout, which Fly.io captures.

```bash
flyctl logs | grep -A2 "FIRST-LAUNCH ADMIN CREATED"
```

You'll see:

```
========================================================================
  HARVEST HERO -- FIRST-LAUNCH ADMIN CREATED
     username: admin
     password: <RANDOM_16-CHAR_STRING>
  Log in at your app URL and change this password immediately.
  This password will NEVER be shown again -- save it now.
========================================================================
```

**Write down that password.** It will not be printed again.

Log in at `https://harvest-hero-pantry.fly.dev/login` with
`admin` + that password. You should land on the placeholder dashboard.

Once you're in, note that Phase 1 will add a "Change password" flow.
For Phase 0, the admin password is what it is — treat this URL as
maintainer-only until Phase 1 ships.

---

## 6. Attach the custom domain

Tell Fly.io that harvestheropantry.com is yours:

```bash
flyctl certs create harvestheropantry.com
flyctl certs create www.harvestheropantry.com
```

Each command prints something like:

```
You are creating a certificate for harvestheropantry.com
We are using lets_encrypt for this certificate.

You can validate your ownership of harvestheropantry.com by:

1: Adding an A record to your DNS service which reads
    A @ 66.241.124.183

2: Adding an AAAA record to your DNS service which reads
    AAAA @ 2a09:8280:1::4:56ba:0
```

**Write down the two IPs.** You'll paste them into Cloudflare next.

Also get Fly.io's canonical IPs (in case the ones printed above
differ from your app's actual IPs):

```bash
flyctl ips list
```

---

## 7. Add DNS records in Cloudflare

1. Log in to https://dash.cloudflare.com
2. Click `harvestheropantry.com`
3. Left sidebar → **DNS** → **Records**
4. Click **Add record** and add each of the following:

| Type  | Name  | IPv4/IPv6 address                | Proxy status         |
|-------|-------|-----------------------------------|----------------------|
| A     | `@`   | (IPv4 printed by flyctl certs)    | **DNS only** (grey)  |
| AAAA  | `@`   | (IPv6 printed by flyctl certs)    | **DNS only** (grey)  |
| CNAME | `www` | `harvestheropantry.com`           | **DNS only** (grey)  |

**Important:** click the orange cloud icon on each record so it turns
grey ("DNS only"). Cloudflare's orange-cloud proxy interferes with
Fly.io's automatic TLS certificate provisioning. You can turn the
proxy back on later if you want Cloudflare's CDN in front of Fly.

Save. Cloudflare's DNS updates propagate in seconds.

---

## 8. Wait for the certificate

Fly.io will notice the DNS records and issue a Let's Encrypt cert
automatically. Watch progress:

```bash
flyctl certs show harvestheropantry.com
```

Look for:

```
Configured: true
Status:     Issued
```

Usually 1–5 minutes. Once it says `Issued`, open
`https://harvestheropantry.com/login` — you're on your production
domain with a valid HTTPS cert.

---

## 9. From now on

To ship any change:

```bash
git commit -a -m "..."
git push origin main

# From the REPO ROOT
cd /Users/octayviaclemons/CascadeProjects/inventory_tracker
flyctl deploy --config web/fly.toml --dockerfile web/Dockerfile
```

If you connected the Fly.io GitHub App to this repo (via the Fly
dashboard), the `git push` alone triggers a deploy — you can skip
the `flyctl deploy` line. Fly.io's own runner does the equivalent
`--config web/fly.toml --dockerfile web/Dockerfile` for you.

That's it. `flyctl deploy` rebuilds, uploads, and does a zero-downtime
rollout. The site is unreachable for a few seconds during the swap;
users hit refresh and everything's fine.

To roll back a bad deploy:

```bash
flyctl releases              # list recent releases
flyctl releases revert <n>   # rollback to release n
```

To open a shell inside the running app (e.g. to poke at the database):

```bash
flyctl ssh console
# now you're in a shell inside the container
cd /app
python3 -c "from database import Database; print(len(Database().get_all_items()))"
```

To view live logs:

```bash
flyctl logs
```

To take the app offline for maintenance:

```bash
flyctl scale count 0    # kill all machines
flyctl scale count 1    # bring one back
```

---

## Troubleshooting

**`flyctl launch` complains about the Dockerfile:** make sure you ran
it from inside `web/`, not from the repo root. The Dockerfile expects
the repo root as the build context and `web/` as `WORKDIR`.

**Deploy fails with "no permission to create volume":** you might be
on Fly's free tier with a volume already in another region. Delete
the old one with `flyctl volumes destroy <name>` or upgrade to their
paid plan (still only a few $/mo).

**Health check keeps failing:** `flyctl logs` will show the error. The
most common cause is a missing env var — check `flyctl secrets list`
and verify `HARVESTHERO_SECRET_KEY` is set.

**"Cannot connect to DB" or admin bootstrap never runs:** volume isn't
mounted. Check `fly.toml` has the `[[mounts]]` block and re-deploy.

**Cert never issues:** Cloudflare is still proxying (orange cloud).
Grey-cloud the A/AAAA records and wait another few minutes.

**Custom domain shows the wrong site:** DNS is still propagating in
some places. Use `dig harvestheropantry.com` to check; may take up to
an hour globally even though Cloudflare edge is instant.
