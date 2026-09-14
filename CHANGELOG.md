# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- CodeQL scanning (`python`, `javascript-typescript`) on push to main and PRs.
- Dependabot config for `pip`, `npm`, and `github-actions` ecosystems, weekly.
- Coverage floor in CI (`--fail-under=70`) on top of the existing test job.
- `commitizen` for Conventional Commits-based versioning/changelog automation.
- Multi-stage `Dockerfile` (gunicorn + whitenoise), `docker-compose.yml` for local
  parity (app + postgres + redis), an opt-in `mock-cloudflare` proxy for testing
  the prod HTTPS path locally, and `documentacao/DEPLOYMENT.md`.
- `GET /healthz/` health check endpoint.
- Cloudflare R2 (S3-compatible) media storage via `django-storages`, opt-in via
  `AWS_STORAGE_BUCKET_NAME` — falls back to local disk when unset.
- `documentacao/CONTRIBUTING.md` and `.github/PULL_REQUEST_TEMPLATE.md`.

### Changed

- Replaced `safety` with `pip-audit` as the dependency vulnerability scanner (dev
  dependency and CI step), removing `safety`'s transitive `nltk` dependency and
  its unpatched CVE.
- Bumped 8 dev/runtime dependencies to current majors after a full audit found 0
  vulnerabilities but significant staleness: `django-redis` 5→7, `isort` 5→9,
  `flake8` 6→7, `django-stubs` 4→6, `mypy` 1→2, `pre-commit` 3→4, `commitizen`
  3→4, `django-extra-checks` (confirmed unused). GitHub Actions bumped to their
  latest majors (`actions/checkout`, `setup-python`, `setup-node`, `setup-uv`,
  `codeql-action`).
- `Place.primary_image` and the map/favorites JSON APIs now read from prefetched
  querysets instead of issuing per-place queries in list/loop views.

### Fixed

- `PlaceAdmin` fieldsets referenced `Place` fields removed in a past migration,
  crashing the admin add/change page for places entirely.
- `NewsForm` didn't validate that an event's end date isn't before its start date.
- `place_detail_view` only checked `is_approved`, not `is_active`, when deciding
  whether a non-owner/non-moderator could view a place — an approved-but-
  deactivated place was visible to any logged-in user.

### Removed

- `static/css/components/carousel.css` — never linked from any template, and its
  selectors didn't match current landing-page markup anyway.

## [0.2.0] - 2026-09-13

### Added

- `.env.example` documenting required and optional environment variables.
- `documentacao/IMPROVEMENT_PLAN.md` tracking an in-progress polish/hardening plan.
- Production settings module (`config/settings/prod.py`) with SSL redirect, secure cookies, HSTS, and `SECURE_PROXY_SSL_HEADER` for running behind a reverse proxy/CDN (e.g. Cloudflare).
- Redis-backed cache option via `CACHE_URL`/`REDIS_URL`, for multi-process production deployments.
- ESLint config and an esbuild bundling pipeline for `static/js/`.

### Changed

- Dependency management migrated from Poetry to [uv](https://docs.astral.sh/uv/); the `Makefile` was removed in favor of `uv run`/`uv sync`.
- `config/settings.py` split into `config/settings/{base,dev,prod}.py`.
- Untracked `db.sqlite3` and `media/` from git; both are now ignored going forward.
- Rewrote `README.md` with real depth on functionality, architecture, and stack; updated the GitHub repo description to match.

### Fixed

- `PlaceReview` was missing its documented "one review per user per place" constraint at the database level; added `unique_together`.
- 5 dead/unused variables in `static/js/`; 3 form controls missing `aria-label`s.

### Removed

- `aula_exercicios/` (unrelated coursework, not part of the app).

### Security

- Bumped Pillow 11.3.0 → 12.3.0, fixing 18 known CVEs (heap out-of-bounds writes/reads, decompression-bomb DoS, an OS command injection in `WindowsViewer`).
- Bumped black 24.10.0 → 26.5.1, fixing an arbitrary-file-write CVE.

## [0.1.0] - 2026-09-13

### Added

- Initial Django remake of the original Marica-City project: tourist places
  with an admin approval workflow, multi-image uploads, reviews and ratings,
  favorites, news/events, and Google OAuth login.
