# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Untracked `db.sqlite3` and `media/` from git; both are now ignored going forward.
- Added `.env.example` documenting required and optional environment variables.

## [0.1.0] - 2026-09-13

### Added

- Initial Django remake of the original Marica-City project: tourist places
  with an admin approval workflow, multi-image uploads, reviews and ratings,
  favorites, news/events, and Google OAuth login.
