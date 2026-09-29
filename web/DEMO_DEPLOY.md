# Isolated demonstration deployment

Do not deploy this database onto `harvest-hero-pantry`. The demo has a separate Fly app and a separate volume. Confirm Fly billing and get owner approval before provisioning. Do not push to `main` until the production deployment impact has been reviewed: `.github/workflows/fly-deploy.yml` automatically deploys web changes to production.

From the repository root, after authenticating with Fly and confirming the organization:

```sh
flyctl apps create harvest-hero-pantry-demo
flyctl volumes create demo_data --size 1 --region iad --app harvest-hero-pantry-demo
```

Set a fresh random `HARVESTHERO_SECRET_KEY` and a distinct strong `HARVESTHERO_BOOTSTRAP_PASSWORD` on the demo app through the Fly secrets manager **before the first deploy**. Neither value belongs in source, terminal transcripts, or screenshots. The bootstrap creates `admin` only if the users table is empty; the password is never logged. After first login, change this Admin password under Settings, then remove the bootstrap secret. The demo config already sets `HARVESTHERO_ENVIRONMENT=demo` and `HARVESTHERO_AUTH_MODE=local`.

```sh
flyctl deploy --config web/fly.demo.toml --dockerfile web/Dockerfile
flyctl status --app harvest-hero-pantry-demo
```

Before provisioning demonstration users, ensure the automatically bootstrapped admin password has been changed. Provision `demo_admin` and `demo_student` through the admin interface, give each user their temporary password privately, and ask each to rotate it under Settings after their first sign-in. Seed only the demo volume using the guarded seed tool: after `flyctl ssh console --app harvest-hero-pantry-demo`, run `cd /app` and `python -m web.tools.seed_demo_data`. The tool refuses to run unless the environment is explicitly `demo` and the data directory is set. Check the banner, sample inventory, login for both roles, and Student scan-in on the separate app before presenting it.

LDAP must be enabled only after IT confirms a reachable TLS-protected identity endpoint and the login implementation has been tested. The local demo accounts are not evidence that campus LDAP works.
