# NS API Project

A small command-line tool that fetches live departure data from the Dutch
Railways (NS) Reisinformatie API for a given station and prints delay statistics
per train category.

This is a practice repository. The application itself is deliberately tiny; the
point of the repo is the surrounding machinery — layered code, unit tests that
never touch the network, a separate integration suite, and three GitHub Actions
workflows covering CI, live-API checks, and publishing.

```
$ uv run ns-api-project --station UT
IC    n=18  avg=  2.4m max= 11.0m cancelled=0 track_changes=2
SPR   n=12  avg=  0.8m max=  4.0m cancelled=1 track_changes=0
```

---

## Quick start

```bash
# 1. install dependencies (creates .venv from uv.lock)
uv sync --all-extras --dev

# 2. get an NS API key (see "Getting an NS API key" below) and export it
export NS_API_KEY="your-key-here"

# 3. run
uv run ns-api-project --station UT
```

Note the command is `ns-api-project` with **hyphens**. That name comes from
`[project.scripts]` in `pyproject.toml`; the Python package underneath is
`ns_api_project` with underscores. `uv run ns_api_project` fails with
`Failed to spawn: ns_api_project`.

### CLI options

| Option | Default | Notes |
| --- | --- | --- |
| `--station` | `UT` | NS station code, e.g. `UT`, `ASD`, `RTD`, `EHV`. |
| `--api-key` | — | Required. Falls back to the `NS_API_KEY` environment variable, which is the preferred way — it keeps the key out of your shell history. |

---

## Repository layout

```
.
├── .github/workflows/
│   ├── ci.yml               # lint + unit tests on every push and PR
│   ├── integration.yml      # live NS API tests, manual + weekly
│   └── release.yml          # build + publish to TestPyPI on a v* tag
├── src/ns_api_project/
│   ├── __init__.py          # package docstring only
│   ├── client.py            # HTTP layer — the only module that does I/O
│   ├── transform.py         # raw JSON  -> typed Departure records
│   ├── aggregate.py         # Departure records -> CategoryStats
│   └── cli.py               # Click entry point, wiring and output
├── tests/
│   ├── test_client.py       # HTTP mocked with respx
│   ├── test_transform.py    # pure parsing tests, fixed payload
│   └── test_integration.py  # live-API contract test, marked `integration`
├── pyproject.toml           # metadata, dependencies, pytest + coverage config
└── uv.lock                  # exact resolved dependency versions
```

### Why the layers

Each module depends only on the one above it, and only `client.py` touches the
network:

| Layer | Input | Output | Testable without network? |
| --- | --- | --- | --- |
| `client` | station code, API key | raw `dict` from the API | mocked with `respx` |
| `transform` | raw `dict` | `list[Departure]` | yes, pure functions |
| `aggregate` | `list[Departure]` | `list[CategoryStats]` | yes, pure functions |
| `cli` | CLI args | printed text | yes |

That split is why the unit suite runs in well under a second and needs no
secrets — the interesting logic (delay calculation, track-change detection,
grouping) lives in pure functions that take plain data.

### Design decisions worth knowing

- **`Departure` and `CategoryStats` are frozen dataclasses.** Records are built
  once during parsing and only read afterwards.
- **A missing `actualDateTime` yields a delay of `0.0`, not `None`.** Cancelled
  trains and trains without a realtime estimate have nothing to measure against;
  reporting a number keeps the aggregation simple. The `cancelled` flag is what
  distinguishes them.
- **`track_changed` requires both tracks to be known.** An unknown platform is
  not a platform change.
- **`parse_departures` raises `KeyError` on an unexpected payload shape.** A
  silent empty list would hide a breaking API change; the integration workflow
  exists precisely to surface that.
- **Stats are sorted by average delay, worst first**, so the first line of
  output is the category running least on time.

---

## Testing

```bash
uv run pytest                  # unit tests only, with coverage — the default
uv run pytest -m integration   # live-API tests only (needs NS_API_KEY)
uv run pytest --no-cov         # skip coverage while iterating locally
```

The relevant configuration in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "integration: hits the live NS API, requires NS_API_KEY",
]
addopts = "--cov=src/ns_api_project --cov-report=term-missing -m 'not integration'"
```

- `markers` registers the custom `integration` marker, so `@pytest.mark.integration`
  does not raise `PytestUnknownMarkWarning` and shows up in `pytest --markers`.
- `addopts` is applied to every run: measure coverage of the package, print the
  uncovered line numbers in the terminal, and **deselect** integration tests.
- `-m integration` on the command line overrides the `-m` from `addopts`,
  because the last `-m` wins. That is how `integration.yml` flips the selection.

The payoff: `pytest` is fast, offline, deterministic, and identical locally and
in CI, while the live tests still exist and run on demand.

`tests/test_integration.py` holds a single contract test: it fetches live
Utrecht Centraal departures and asserts that `parse_departures` still finds the
fields it expects. It reads `os.environ["NS_API_KEY"]` directly, so it raises a
`KeyError` when the key is absent rather than passing silently.

> If every integration test is removed or unmarked, `pytest -m integration`
> collects nothing and exits with code 5 (`NO_TESTS_COLLECTED`), which fails the
> Integration workflow even though nothing is broken.

---

## GitHub Actions workflows

Three workflows, split by cost and by what they're allowed to touch.

### `ci.yml` — CI

**Runs on:** every push to `main`, every pull request.
**Needs secrets:** no.

Installs dependencies with uv against a matrix of Python 3.11 and 3.12 (the
versions permitted by `requires-python`), runs `ruff check`, then runs the unit
tests with coverage. Because `addopts` deselects the integration marker, this
workflow never calls the NS API. That means it is safe on pull requests from
forks (which cannot read secrets anyway) and it cannot fail because the NS API
is down or rate-limiting.

This is the workflow to require as a status check on `main`.

### `integration.yml` — Integration

**Runs on:** manual dispatch, plus a weekly schedule (Monday 06:00 UTC).
**Needs secrets:** `NS_API_KEY`.

Runs `uv run pytest -m integration`, so only the live-API tests. Kept out of CI
on purpose: it spends API quota, it needs a secret, and a broken NS API would
otherwise block unrelated pull requests. As a weekly canary it answers a
different question than CI does — not "is my code correct" but "does the API
still return what my parser expects".

Scheduled workflows in GitHub Actions always use UTC, and GitHub disables
schedules on repositories that see no activity for 60 days.

### `release.yml` — Release

**Runs on:** pushing a tag matching `v*`.
**Needs secrets:** none — it uses OIDC trusted publishing.

Builds the sdist and wheel with `uv build` and uploads them to **TestPyPI** with
`uv publish`. No API token is stored anywhere: `permissions: id-token: write`
lets the job request a short-lived OIDC token from GitHub, which TestPyPI
exchanges for an upload token after verifying that the repository, workflow
file, and environment name match its configured trusted publisher.

To cut a release:

```bash
# bump `version` in pyproject.toml first — nothing verifies the tag matches it
git tag v0.1.0
git push origin v0.1.0
```

To publish to real PyPI instead, drop the `--publish-url` flag (it defaults to
PyPI) and register a trusted publisher on pypi.org.

---

## GitHub settings you need to configure

None of the workflows work out of the box on a fresh clone. Set these up in the
repository on GitHub.

### 1. Actions must be enabled

**Settings → Actions → General → Actions permissions** → "Allow all actions and
reusable workflows". The workflows use a third-party action
(`astral-sh/setup-uv`), so a policy of "allow actions created by GitHub" alone
is not enough.

On the same page, **Workflow permissions** can stay on the default read-only
token — nothing here writes back to the repository.

### 2. `NS_API_KEY` repository secret

Required by `integration.yml`.

**Settings → Secrets and variables → Actions → New repository secret**
- Name: `NS_API_KEY`
- Value: your NS API subscription key

Notes:
- Use a *secret*, not a *variable*. Variables are visible in logs.
- Secrets are not available to workflows triggered by pull requests from forks.
  That's fine here, since the integration workflow only runs on dispatch and
  schedule.
- If the secret is missing, GitHub substitutes an empty string rather than
  failing the step, so the failure surfaces as a 401 from the NS API.

### 3. The `testpypi` environment

Required by `release.yml`, which declares `environment: testpypi`.

**Settings → Environments → New environment** → name it exactly `testpypi`.

The name must match both the workflow and the trusted publisher configured on
TestPyPI. Optionally add a **required reviewer** so a release pauses for manual
approval, and restrict the environment to tag or branch patterns.

### 4. TestPyPI trusted publisher

Configured on TestPyPI, not GitHub, but `release.yml` depends on it.

On https://test.pypi.org → your account → **Publishing** → add a pending
publisher with:

| Field | Value |
| --- | --- |
| PyPI project name | `ns-api-project` |
| Owner | your GitHub username or org |
| Repository name | `NS_API_PROJECT` |
| Workflow name | `release.yml` |
| Environment name | `testpypi` |

All five must match exactly, or the upload is rejected. This is what makes
`permissions: id-token: write` sufficient and an API token unnecessary.

### 5. Branch protection on `main` (recommended)

**Settings → Branches → Add branch ruleset** (or classic branch protection):
- Require a pull request before merging
- Require status checks to pass → select the CI matrix jobs (`test (3.11)`,
  `test (3.12)`). They only appear in the list after the workflow has run once.
- Require branches to be up to date before merging

### 6. Scheduled workflows and repository activity

GitHub disables `schedule` triggers on public repositories after 60 days with no
commits, emailing the owner first. If the weekly integration run goes quiet,
check **Actions → Integration** for a "this workflow was disabled" banner and
re-enable it there.

---

## Getting an NS API key

1. Register at https://apiportal.ns.nl.
2. Subscribe to the **Reisinformatie API** product.
3. Copy the primary subscription key.
4. Export it as `NS_API_KEY` locally, and add it as a repository secret on
   GitHub (step 2 above).

The key is sent as the `Ocp-Apim-Subscription-Key` header — the NS portal runs
on Azure API Management, which is where that header name comes from. Never
commit it: pass it via the environment rather than `--api-key`, so it stays out
of shell history and process listings.

---

## Local development

```bash
uv sync --all-extras --dev   # install, including dev tools
uv run ruff check .          # lint, the same command CI runs
uv run ruff format .         # format
uv run pytest                # unit tests + coverage
```

Dev dependencies: `pytest`, `pytest-cov` (coverage), `pytest-mock`, `respx`
(HTTP mocking for `httpx`), `ruff` (lint + format).

Dependencies are locked in `uv.lock`; commit it whenever you change
`pyproject.toml` so CI resolves the same versions you did.
