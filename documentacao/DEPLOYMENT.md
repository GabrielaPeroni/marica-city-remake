# Deployment

Covers building the Docker image, required prod env vars, wiring Cloudflare in
front of it, and using `docker-compose.yml` for local dev/testing. The
deployment target (VPS/PaaS vs. Cloudflare Tunnel) is not decided yet — this
setup works with either, since Cloudflare only ever talks to the app over
plain HTTP and identifies itself via `X-Forwarded-Proto`.

## Image

Multi-stage `Dockerfile`: a `builder` stage installs deps with `uv sync
--locked --no-dev` into `/venv` and runs `collectstatic`, then a slim
`runtime` stage copies just the venv + app code and runs as a non-root user
(`app`). Static files are baked into the image at build time — no
`collectstatic` at container start.

```bash
docker build -t maricacity .
docker run --rm -p 8000:8000 --env-file .env \
  -e DJANGO_SETTINGS_MODULE=config.settings.prod \
  maricacity
```

The container serves on `0.0.0.0:8000` via `gunicorn config.wsgi:application`
and has a `HEALTHCHECK` hitting `GET /healthz/` (see below).

## Required env vars (prod)

Copy `.env.example` to `.env` and fill in real values. At minimum for prod:

- `SECRET_KEY`, `ALLOWED_HOSTS`, `GOOGLE_OAUTH_CLIENT_ID` — no defaults, required.
- `DB_ENGINE`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT` — point at
  a real Postgres instance (SQLite is dev-only).
- `CACHE_URL` or `REDIS_URL` — a Redis instance; without one, `LocMemCache` is
  used, which is not safe across multiple gunicorn workers.
- `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
  `SECURE_HSTS_*` — default to secure values already, only override if you
  know why.
- Media storage (Cloudflare R2, S3-compatible): `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`,
  optionally `AWS_S3_REGION_NAME` (default `auto`) and
  `AWS_S3_CUSTOM_DOMAIN`. Leaving `AWS_STORAGE_BUCKET_NAME` empty falls back
  to local `MEDIA_ROOT` — fine for a single-instance VPS with a persistent
  volume, but uploads will not survive a redeploy on most PaaS/containers.

Static files are always served by whitenoise (compressed + hashed filenames
in prod via `STORAGES["staticfiles"]`) — no separate nginx layer needed for
static assets regardless of which media backend you pick.

## Health check

`GET /healthz/` (`apps/core/views.health_view`, wired in `config/urls.py`) —
no auth, runs `SELECT 1` against the DB and returns `{"status": "ok"}` with a 200. Chosen over a no-op check so it also catches DB connectivity outages,
which is normally what "the app is unhealthy" means in practice for this
project. Used by the Dockerfile's `HEALTHCHECK` and should be pointed at by
whatever orchestrates the container (PaaS health check URL, VPS process
supervisor, uptime monitor).

## Wiring Cloudflare in front

Either approach works unchanged against the same Django app — `prod.py`
already trusts `X-Forwarded-Proto` from a reverse proxy
(`SECURE_PROXY_SSL_HEADER`) and redirects to HTTPS
(`SECURE_SSL_REDIRECT`). Nothing here is specific to one deployment target.

### Option A — Cloudflare as a plain proxy/CDN in front of a VPS/PaaS origin

1. Deploy the container to a VPS or PaaS (Fly.io, Railway, Render, a plain
   VPS with the Docker image, etc.) with a public origin address.
2. Point a DNS record at that origin in Cloudflare, with the proxy (orange
   cloud) enabled.
3. Set Cloudflare's SSL/TLS mode to **Full (strict)** if the origin serves
   its own valid cert, or **Full** if it's self-signed/Let's Encrypt behind a
   basic setup. Avoid **Flexible** — it terminates TLS at Cloudflare only and
   would make `SECURE_SSL_REDIRECT` loop, since the origin never sees HTTPS.
4. Cloudflare forwards `X-Forwarded-Proto: https` automatically; no
   Django-side config needed beyond what's already in `prod.py`.

### Option B — Cloudflare Tunnel (no public origin IP)

1. Run `cloudflared` alongside the container (same host, or as a sidecar
   container) and create a tunnel pointing at `http://app:8000` (or
   `localhost:8000` if run on the same host).
2. Route a public hostname to the tunnel in the Cloudflare dashboard/`cloudflared`
   config.
3. `cloudflared` sets `X-Forwarded-Proto: https` on requests it forwards, so
   `SECURE_PROXY_SSL_HEADER` works the same as in Option A.
4. No inbound ports need to be opened on the origin at all.

Switching between A and B later is purely infra — the Django app and its
settings never change.

## Local dev/testing with docker-compose

`docker-compose.yml` gives a full-stack local setup close to prod, as an
alternative to the plain `uv run manage.py runserver` + SQLite flow (which
still works unchanged — this is additive, not a replacement):

```bash
docker compose up --build
```

Brings up:

- `app` — the Django app built from `Dockerfile`, running under
  `config.settings.prod`, `.env`-configured, talking to `db`/`redis`.
- `db` — `postgres:15`, matching the version CI tests against.
- `redis` — `redis:7`, matching the Redis-ready cache config.

Run migrations/management commands against the compose stack with
`docker compose exec app python manage.py <command>` (adjust the venv path
if invoking directly, or use `docker compose run --rm app <command>`).

### Local mock Cloudflare vs. real Cloudflare

`docker-compose.yml` also has an **opt-in** `mock-cloudflare` service (Caddy)
behind the `mock-cloudflare` profile — it is not part of the default
`docker compose up`:

```bash
docker compose --profile mock-cloudflare up --build
```

This starts a Caddy reverse proxy in front of `app` that terminates TLS with
a self-signed cert (`tls internal`) and forwards `X-Forwarded-Proto: https`,
mimicking what Cloudflare's edge does to the origin. It lets you exercise the
full `SECURE_PROXY_SSL_HEADER`/`SECURE_SSL_REDIRECT` path — HTTPS termination
at the edge, plain HTTP to the app — entirely locally, without a Cloudflare
account or domain:

```bash
curl -k https://localhost:8443/healthz/
```

**This is a local stand-in, not a deployment option.** It exists purely so
the prod security settings are testable today, before the real Cloudflare
target (Option A or B above) is decided. Swapping in real Cloudflare later
means changing the infra in front of the app (DNS + proxy settings, or a
`cloudflared` tunnel) — the `mock-cloudflare` service and its config
(`deploy/mock-cloudflare/Caddyfile`) are not part of that path and are never
used in prod.
