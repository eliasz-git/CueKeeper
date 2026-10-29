# Versioning — CueKeeper

## Scheme

We use [Semantic Versioning](https://semver.org/) (semver): `MAJOR.MINOR.PATCH`.

- **MAJOR** — breaking changes to saves, config, or core systems (rare pre-1.0).
- **MINOR** — new features, new endpoints, new UI sections, new cues behavior.
- **PATCH** — bug fixes, tuning, UI tweaks, docs.

Pre-1.0, `MAJOR` stays `0`. `MINOR` is the meaningful release number; `PATCH` is for small fixes between releases.

## Current version

`v0.1.0` — see `src/main.py` (`__version__`).

## When to bump

| Change | Bump | Example |
|--------|------|---------|
| New endpoint, UI section, or major feature | MINOR | `0.1.0` → `0.2.0` |
| Bug fix, tuning, balance, UI tweak | PATCH | `0.1.0` → `0.1.1` |
| Save-breaking change (`data.json` schema) | MAJOR | `0.x.x` → `1.0.0` |
| Docs / README only | none | no version change |

## Don't over-bump

Don't create a new version for every tiny edit. Group fixes into a single PATCH release, and only cut a release when there's something worth shipping (a new build, a public fix, or a milestone).

## Release process

1. Update `__version__` in `src/main.py`.
2. Sync `package.json` `version` to match.
3. Sync `README.md` and `ROADMAP.md` release references.
4. Run the checks: `ruff check src tests` and `pytest -q`.
5. Run `./build_release.sh <version> --skip-release` to build/tag (or skip the build for source-only releases).
6. Create the GitHub release and tag `v<version>`.
7. Update `CHANGELOG.md` if one exists.

## Version locations

The version lives in exactly one place in code:

- `src/main.py` — `__version__`

Everything else (`package.json`, release titles, build artifacts, tags) is derived from that constant. Do not add a second source of truth.

## Should we even have versions?

**Yes.** CueKeeper ships as a runnable server that operators deploy to show computers. Different show machines may run different versions, operators file bug reports, and everyone needs to know which version they're on. Remove versions only if you stop distributing the server entirely and go source-only.