# Repository operating rules

## Scope

This repository is the single project for all Daryn Ustaz course sites, the
admin site, and the reviews API. Do not create a second repository, Cloudflare
Pages application, Render service, or Neon database unless the user explicitly
requests a separate production resource.

## Release-document gate

Do not open or read `DEPLOY.md` during initial repository discovery or ordinary
development. First finish the requested implementation and complete the
relevant local verification. Only then, immediately before the
commit -> push -> deploy sequence, read `DEPLOY.md` in full and follow it.

## Production architecture

- `build_sites.py` builds 16 course applications (`course-1` through
  `course-16`) and the `admin` application into `dist/`.
- Those 17 static applications are published manually to the existing
  Cloudflare Pages projects. Pages is not connected to Git, so a Git push does
  not publish the frontend.
- `backend/` is the Docker context for the existing Render service
  `daryn-ustaz-reviews`. The service tracks `main` and auto-deploys pushed
  backend changes.
- The production API uses the existing Neon database named
  `daryn-ustaz-feedback` through `DATABASE_URL`.

## Development and verification

- Keep secrets in the ignored root `.env` or provider dashboards. Never print,
  commit, copy into documentation, or replace secret values.
- Preserve unrelated working-tree changes. Inspect `git status --short` and
  `git diff` before editing and before staging.
- Create the virtual environment with `python -m venv .venv`, then install with
  `.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt`.
- For the isolated local stack, create the read-only Neon snapshot with
  `.\.venv\Scripts\python.exe scripts\snapshot_neon.py`, start with
  `.\start-local.ps1`, verify with
  `.\.venv\Scripts\python.exe scripts\verify_local.py`, and stop with
  `.\stop-local.ps1`.
- A frontend-only build uses the API supplied in the process environment:
  `$env:PUBLIC_API_URL='<api-url>'; .\.venv\Scripts\python.exe build_sites.py`.
  `dist/` is generated and ignored; do not commit it.
- At minimum, run
  `.\.venv\Scripts\python.exe -m compileall -q build_sites.py backend scripts`
  for Python changes. Use the complete local verification for behavior changes.
- Local checks must use the SQLite snapshot. Do not write test data to Neon.

## Change discipline

- The existing Render service is the only backend deployment target. Do not
  create a replacement service because a deploy is slow or unhealthy.
- Do not change the production database schema or data unless the task
  explicitly requires it and a backup/rollback path has been verified.
- Keep `PUBLIC_API_URL` configurable. Do not hard-code a local API into a
  production Pages build.
- Stage only files that belong to the current task. A release is not complete
  until both the affected target and its live health/behavior are verified.
