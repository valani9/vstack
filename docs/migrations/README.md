# Migration Guides

These guides cover upgrades between vstack releases. During the
`0.x` series, minor releases may include API-shape changes — these
guides name what changed and how to update.

Once vstack hits `1.0.0`, semantic versioning applies: minor
releases will be strictly additive and these guides will only be
needed for major version bumps.

| From → To       | Guide                                         |
|-----------------|-----------------------------------------------|
| 0.10 → 0.12     | [`v0.10_to_v0.12.md`](./v0.10_to_v0.12.md) — `diagnose()` API |
| 0.12 → 0.15     | [`v0.12_to_v0.15.md`](./v0.12_to_v0.15.md) — recipes catalog  |
| 0.15 → 0.18     | [`v0.15_to_v0.18.md`](./v0.15_to_v0.18.md) — FastAPI server   |
| 0.18 → 0.20     | [`v0.18_to_v0.20.md`](./v0.18_to_v0.20.md) — recipes CLI + dashboard |
| 0.20 → 0.22     | [`v0.20_to_v0.22.md`](./v0.20_to_v0.22.md) — WALKTHROUGHs + examples gallery |

## Versioning policy

- `0.x.y` releases: breaking changes permitted in minor bumps
  (`0.x` → `0.x+1`). Patch bumps (`0.x.y` → `0.x.y+1`) are
  non-breaking.
- `1.0.0` and later: SemVer. Breaking changes only on major.
  Deprecations warned for one minor release before removal.

## What counts as "breaking"

- Removal or rename of a public symbol (listed in `__all__`).
- Argument removal or required → required-with-default change.
- Wire-format breaking change (e.g., new required field in JSON).
- Behavioural change that flips a previously-correct test.

## What doesn't count

- Addition of new optional arguments.
- Addition of new patterns / recipes / CLI sub-commands.
- Addition of new fields with non-required defaults.
- Refactoring of internal modules (underscore-prefixed).
- Documentation, examples, walkthrough, or test additions.
