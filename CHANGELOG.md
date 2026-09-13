# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
