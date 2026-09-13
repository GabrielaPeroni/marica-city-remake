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

### Changed

- Untracked `db.sqlite3` and `media/` from git; both are now ignored going forward.
- Added `.env.example` documenting required and optional environment variables.
- Replaced `safety` with `pip-audit` as the dependency vulnerability scanner (dev
  dependency and CI step), removing `safety`'s transitive `nltk` dependency and
  its unpatched CVE.

## [0.1.0] - 2026-09-13

### Added

- Initial Django remake of the original Marica-City project: tourist places
  with an admin approval workflow, multi-image uploads, reviews and ratings,
  favorites, news/events, and Google OAuth login.
