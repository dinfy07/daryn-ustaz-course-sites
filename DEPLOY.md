# Production release runbook

Read this file only after implementation and local verification are complete,
immediately before commit, push, and deployment. This runbook operates the
existing production resources; it never creates replacements.

## Current production targets

| Part | Existing target | Source/configuration |
| --- | --- | --- |
| Backend | Render service `daryn-ustaz-reviews` | GitHub `dinfy07/daryn-ustaz-course-sites`, branch `main`, root directory `backend`, Dockerfile `./Dockerfile`, health path `/health` |
| Database | Neon `daryn-ustaz-feedback` | Render environment variable `DATABASE_URL` |
| Frontend | 17 existing Cloudflare Pages projects | Manual direct upload of `dist/course-1` through `dist/course-16` and `dist/admin`; no Git connection |

The Render container runs Gunicorn with the Uvicorn worker and binds to
`${PORT:-10000}`. Required provider-side variable names are `DATABASE_URL`,
`ADMIN_PASSWORD`, and `ALLOWED_ORIGINS`. Never place their values in Git, shell
history, screenshots, or this document.

## 1. Release preflight

From the repository root:

```powershell
git remote -v
git branch --show-current
git status --short
git diff
```

The intended remote is
`https://github.com/dinfy07/daryn-ustaz-course-sites.git` and the production
branch is `main`. Stop if either differs, if a secret is present, or if unrelated
changes would be staged.

Run the relevant local checks before release. For the complete isolated test:

```powershell
.\start-local.ps1
.\.venv\Scripts\python.exe scripts\verify_local.py
.\stop-local.ps1
```

The verifier covers all 16 course sites, the admin page, API health, admin
authorization, and a temporary local review write/cleanup. It uses local SQLite,
not production Neon.

## 2. Build the static applications

Set the production API only in the current process and build once:

```powershell
$env:PUBLIC_API_URL = 'https://daryn-ustaz-reviews.onrender.com'
.\.venv\Scripts\python.exe build_sites.py
```

Confirm that the build contains exactly these 17 application directories:

```text
course-1   course-2   course-3   course-4
course-5   course-6   course-7   course-8
course-9   course-10  course-11  course-12
course-13  course-14  course-15  course-16
admin
```

Verify that every generated course `config.js` and the generated admin
`index.html` point to `https://daryn-ustaz-reviews.onrender.com`. Do not commit
`dist/`.

## 3. Commit and push

Stage only the reviewed task files; never use a blanket add while unrelated
changes are present. Then commit and push the existing branch:

```powershell
git add -- <reviewed-files>
git diff --cached
git commit -m "<concise description>"
git push origin main
```

A push to `main` is the backend release trigger for the existing Render service.
It does not publish any Cloudflare Pages application.

## 4. Verify the existing Render deployment

In Render, open `daryn-ustaz-reviews`; do not create a new service. Confirm the
deployment uses the pushed commit and finishes successfully. Check:

```powershell
Invoke-RestMethod 'https://daryn-ustaz-reviews.onrender.com/health'
```

The expected JSON is `{"status":"ok"}`. If the deploy fails, inspect that
service's logs and configuration first. Preserve the existing Neon connection
and never replace `DATABASE_URL` merely to retry a deploy.

## 5. Publish the existing Cloudflare Pages applications

Cloudflare project identifiers are provider-side settings and are not stored in
this repository. Before any upload, list the existing projects in the authorized
Cloudflare account or copy each exact identifier from **Workers & Pages**. Map
the 17 local application names above to the 17 existing projects. Do not infer a
project identifier from a course slug and do not create a missing project.

With the exact existing project identifier, deploy each changed output directory
using the same pushed commit hash:

```powershell
$commit = git rev-parse HEAD
npx.cmd wrangler pages deploy 'dist/course-1' --project-name '<existing-project-id>' --branch main --commit-hash $commit
npx.cmd wrangler pages deploy 'dist/admin' --project-name '<existing-admin-project-id>' --branch main --commit-hash $commit
```

Repeat the course command only for the affected `dist/course-N` directories, or
for all 16 when shared frontend assets changed. Publish `dist/admin` whenever
admin output changed. The placeholders must be replaced with identifiers read
from the existing Cloudflare account; they are deliberately not guessed here.

## 6. Live verification

After both providers finish:

1. Recheck the Render `/health` endpoint.
2. Open every deployed Pages URL and verify it loads without console/network
   errors.
3. Confirm each course reads its own slug and reviews from the production API.
4. Confirm the admin site authenticates and lists all 16 courses.
5. For a shared frontend change, sample both Russian and Kazakh sites and check
   all 17 Pages deployments are on the intended release.

Do not perform a production review write solely as a smoke test. If the task
explicitly requires a production write, use a clearly marked record and remove
it only after its exact ID is verified.

## Rollback

- Frontend: check out or rebuild the last known-good commit and redeploy its
  generated directory to the same Pages project. Do not delete/recreate the
  Pages project.
- Backend: use the existing Render service's known-good deployment or revert the
  faulty Git commit on `main`, then verify `/health` and the affected API flow.
- Database: stop before rollback if a release changed schema or data. Restore
  only from a verified Neon backup/branch appropriate to that exact change.
