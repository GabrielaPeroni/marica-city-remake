# MaricaCity — Master Improvement & Polish Plan

Status snapshot as of 2026-09-13 (branch `main`, clean).

## Status log

| PR                                                           | Status              | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------------------------------------------ | ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0 — uv migration (added mid-plan, not in original numbering) | **Merged**          | Poetry → uv, Makefile dropped per explicit request. `uv.lock` generated and verified: `uv run python manage.py test apps` passes 116/117 (see known issue below).                                                                                                                                                                                                                                                                                                                                                             |
| 1 — Repo hygiene                                             | **Merged**          | Verified independently: db.sqlite3/media untracked (kept on disk), `.env.example` cross-checked against every `config()` call in `config/settings.py`, `env/`/`htmlcov/` confirmed never tracked (not a guess).                                                                                                                                                                                                                                                                                                               |
| Hotfix — PlaceReview unique constraint                       | **Merged** (PR #4)  | Model was missing `unique_together` entirely despite CLAUDE.md documenting it — added it + migration. This is what was blocking CI on every other PR; all now pass 117/117.                                                                                                                                                                                                                                                                                                                                                   |
| Cleanup — remove aula_exercicios, rewrite README             | **Merged** (PR #6)  | Unrelated coursework removed; README rewritten with real depth on functionality/architecture/stack; GitHub repo description updated to match.                                                                                                                                                                                                                                                                                                                                                                                 |
| Security — Pillow 11.3.0 → 12.3.0                            | **Merged** (PR #7)  | Fixed 36 of 38 open Dependabot alerts (18 distinct CVEs).                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Security — black 24.10.0 → 26.5.1                            | **Merged** (PR #10) | Fixed the arbitrary-file-write CVE. Checked `black --check --diff` first: zero files reformatted, no churn. Only nltk remains open (no patch yet, transitive via `safety` dev tool — resolves once PR 3 swaps to `pip-audit`).                                                                                                                                                                                                                                                                                                |
| 2 — Settings hardening & environments                        | **Merged** (PR #9)  | Split `config/settings.py` into `base/dev/prod.py`. prod adds SSL redirect, secure cookies, HSTS, `SECURE_PROXY_SSL_HEADER` for Cloudflare, structured logging; Redis-ready cache via `CACHE_URL`/`REDIS_URL`. Verified: `check --deploy` under prod settings → 0 warnings (down from 6); 117/117 tests. Branch was cut before the Pillow fix merged and would have reverted it — caught during review, merged main in and relocked before shipping.                                                                          |
| 3 — CI expansion + versioning                                | Not started         | Depends on PR 1 (done), PR 2 (done)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 4 — Deployment setup                                         | Not started         | Depends on PR 2. Deployment target not yet decided by the user (VPS+Cloudflare-proxy vs Cloudflare Tunnel vs undecided) — build the Docker/storage setup generically until that's picked.                                                                                                                                                                                                                                                                                                                                     |
| 5 — Backend bug audit & fixes                                | Not started         | Depends on PR 2. Has a confirmed starting bug, see "Known issues" below.                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 6 — Test coverage increase                                   | Not started         | Depends on PR 3, PR 5                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 7 — Frontend build tooling & polish                          | **Merged**          | ESLint + esbuild + a11y pass, verified independently (`npm run lint:js` clean, `npm run build:js` bundles all 13 entries). Found (not fixed, out of this PR's scope): `static/css/components/carousel.css` is orphaned — never linked from any template, its selectors (`.featuredSwiper`, `.place-card`) don't even match current landing-page markup (`#featuredSwiper`, `.featured-swiper`). Safe to delete or needs reconciling with `landing.css`, which already duplicates `.place-card-img`/`.place-card-placeholder`. |
| 8 — Documentation overhaul                                   | Not started         | Depends on PR 2, PR 4                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |

## Known issues found during review

1. ~~Pre-existing test failure~~ — **Fixed** (PR #4, merged): `PlaceReview` had no `unique_together` constraint despite CLAUDE.md documenting one; added it + migration. This was blocking CI on every other open PR.
2. **Hero carousel placeholder images, a content bug not a CSS bug — still open:** `static/images/hero/hero_1.jpg`, `hero_2.jpg`, and `hero_3.jpg` (all ~25KB) are flat solid-color placeholder JPEGs, not real photography — confirmed by opening each directly in a browser (solid tan/blue/gold fills, no image detail). Only `static/images/hero/main.png` (4MB) is a real photo. This is why the landing page's hero carousel looks "unstyled" when it rotates to slides 2-4: the dark overlay renders correctly, but there's a flat color underneath instead of a photo. Needs real photography dropped into those three files — **not assigned to a numbered PR yet since it's a content/asset task, not code**; flagging here so whoever lands on frontend work (PR 7 follow-up or PR 8) replaces them.

## Findings from repo audit

**Repo hygiene**

- `db.sqlite3` is tracked in git (real data alongside code — should never be committed).
- `media/**` uploads (user images) are tracked in git — should be gitignored, uploads don't belong in version control.
- `env/` (a full legacy virtualenv, includes compiled `.exe`s) exists on disk untracked but sits in the repo root next to the Poetry-managed `.venv` convention described in CLAUDE.md — stale, confusing, should be deleted.
- No `.env.example` — `config/settings.py` reads ~10 required env vars via `python-decouple` with no documented template.
- `htmlcov/` (coverage HTML report) sits in the repo root, gitignored but not cleaned.
- No `CHANGELOG.md`, no version tag/release process — `pyproject.toml` is frozen at `0.1.0`.

**Backend / settings**

- Single `config/settings.py` for all environments — no dev/prod split.
- No production security hardening: missing `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`, `SECURE_PROXY_SSL_HEADER` (needed behind Cloudflare/any reverse proxy), `X_CONTENT_TYPE_OPTIONS`.
- `CACHES` is hardcoded to `LocMemCache` — breaks rate-limiting correctness under multi-process/multi-dyno deployment (the code already warns about this in a comment but doesn't act on it).
- No logging configuration (Django's default only logs to console under `DEBUG`; nothing reaches a file/service in prod).
- No error tracking (Sentry or similar).
- No `django-storages`/S3-compatible backend for `MEDIA_ROOT` — user uploads live on local disk, which doesn't survive redeploys on most PaaS/containers and won't work well behind Cloudflare unless paired with R2/S3.
- No WSGI/ASGI production server wiring (gunicorn/uvicorn), no `whitenoise` for static file serving.
- No health-check endpoint for uptime monitoring / container orchestration.

**CI/CD**

- `.github/workflows/pr-checks.yml` runs lint + tests only. No security scanning (`safety` is a listed dev dependency but never invoked in CI), no `pip-audit`/`bandit`, no CodeQL, no dependency review, no coverage threshold enforcement.
- No CD workflow — no path from a merged PR to a deployed environment.
- No release automation (tagging, changelog generation).

**Testing**

- Tests exist per-app (`apps/*/tests.py`) but are single flat files, not packages — hard to scale.
- No frontend tests (JS is vanilla, untested).
- No end-to-end/browser tests.

**Frontend**

- Vanilla JS served directly from `static/js/`, no bundler/minifier, no linting (no ESLint config), no type checking.
- No accessibility audit performed.
- Images under `static/images` are not optimized/compressed as a build step.

**Documentation**

- `documentacao/CRUD.md` and `documentacao/STRUCTURE.md` exist but CLAUDE.md's mandate to keep them in sync with code isn't enforced by any check.
- No `CONTRIBUTING.md`, no PR template.

## Proposed PR breakdown

Each PR is scoped to be independently reviewable and shippable. Suggested order accounts for dependencies (e.g., settings split must land before Docker/deploy work depends on it).

| #   | PR                                      | Scope                                                                                                                                                                                                                                                                                                                                  | Depends on |
| --- | --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| 1   | **Repo hygiene**                        | Untrack `db.sqlite3` and `media/**`, delete `env/`, add `.env.example`, clean `.gitignore`, add `CHANGELOG.md` (Keep a Changelog format) + bump to semver `0.1.0`→`0.2.0` going forward                                                                                                                                                | —          |
| 2   | **Settings hardening & environments**   | Split `config/settings.py` into `base.py` / `dev.py` / `prod.py`, add production security headers, logging config, `SECURE_PROXY_SSL_HEADER` for Cloudflare, structured settings for cache backend (Redis-ready)                                                                                                                       | PR 1       |
| 3   | **CI expansion + versioning**           | Add `safety`/`pip-audit` + CodeQL to CI, coverage threshold gate, add Dependabot config, adopt Conventional Commits + automate `CHANGELOG.md`/tag on merge to main                                                                                                                                                                     | PR 1       |
| 4   | **Deployment setup (Cloudflare-ready)** | `Dockerfile` (multi-stage, gunicorn + whitenoise), `docker-compose.yml` for local parity (Postgres + Redis), `django-storages` + S3-compatible backend wired for Cloudflare R2, health-check endpoint, deployment doc (CONTRIBUTING-style runbook for wiring behind Cloudflare Tunnel or as origin with Cloudflare proxy/CDN in front) | PR 2       |
| 5   | **Backend bug audit & fixes**           | Dedicated pass over `apps/*` models/views/forms for correctness bugs, race conditions (e.g. `PlaceImage.is_primary` save-override), missing validation, N+1 queries; write regression tests per fix                                                                                                                                    | PR 2       |
| 6   | **Test coverage increase**              | Convert `tests.py` files to `tests/` packages per app, backfill coverage on views/forms/permissions, add a coverage floor to CI (ties into PR 3)                                                                                                                                                                                       | PR 3, PR 5 |
| 7   | **Frontend build tooling & polish**     | Introduce a lightweight bundler (esbuild) for JS, add ESLint + Prettier enforcement (Prettier already partially configured), audit templates for accessibility (labels, alt text, contrast), optimize static images                                                                                                                    | —          |
| 8   | **Documentation overhaul**              | Refresh `documentacao/CRUD.md`/`STRUCTURE.md`, add `CONTRIBUTING.md`, PR template, architecture diagram, update `CLAUDE.md` for the new settings/deploy structure                                                                                                                                                                      | PR 2, PR 4 |

## Tooling/stack recommendations

- **Static/media storage:** `django-storages` + Cloudflare R2 (S3-compatible, no egress fees) — pairs naturally with a Cloudflare-fronted deployment.
- **Static file serving:** `whitenoise` — avoids needing a separate nginx layer for a project this size.
- **Cache/rate-limit backend for prod:** Redis (`django-redis`) — required once `LocMemCache` no longer suffices (already flagged in code comments).
- **Error tracking:** Sentry (`sentry-sdk`) — free tier is enough for this scale.
- **Process manager:** `gunicorn` (WSGI) behind Cloudflare; Django 5.2 also supports ASGI if websockets are ever needed.
- **Deployment target:** a small PaaS/VPS (Fly.io, Railway, Render, or a plain VPS) as origin, with Cloudflare in front (proxy/CDN + optionally Cloudflare Tunnel to avoid exposing the origin IP at all). Cloudflare Pages does not run a Django app directly — it only fits if the frontend were decoupled to a static/SPA build, which is out of scope here.
- **Dependency/security scanning:** `pip-audit` (actively maintained, better than `safety`'s free tier) + GitHub CodeQL + Dependabot.
- **Conventional commits + changelog automation:** `commitizen` (Python-native, works well with Poetry) for versioning + changelog generation, simpler to adopt here than `semantic-release` (Node-based).
- **JS bundling:** `esbuild` — near-zero config, fast, appropriate for the current vanilla-JS scale (no need for a full framework).

## Execution approach

Each PR above is scoped for a dedicated agent working in its own git worktree/branch, so work can proceed in parallel where there's no dependency conflict (e.g., PR 7 and PR 8 can run alongside the backend track). Findings from PR 5 (bug audit) will be reported back before fixes are applied broadly, since "bug fixes" found during audit may need prioritization input.
