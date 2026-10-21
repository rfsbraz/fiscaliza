# Deploy

Fiscaliza is a static site on Cloudflare Pages, project `fiscaliza`, uploaded with
`wrangler pages deploy` (direct upload, no Git integration). The production branch is `master`, at
`fiscaliza-ceg.pages.dev`; anything else is a preview at `<branch>.fiscaliza-ceg.pages.dev` (Pages
turns `/` and other characters in the branch name into `-`).

Deploys run in CI, in `.github/workflows/deploy.yml`, on my Homeberry runner. The workflow only
calls `deploy/pages.py`; everything a deploy does is in that script.

## When it deploys

| Trigger | Deploys |
|---|---|
| Push to `master` | production |
| Daily at 05:00 UTC | production, for the data refresh |
| Pull request from this repo | a preview on a Pages branch named after the PR's head branch |

Cron is UTC and doesn't follow summer time: 05:00 UTC is 06:00 in Lisbon in summer time and
05:00 in winter time. parlamento-aberto's nightly data sync starts at 06:15 UTC, so the daily
deploy picks up the data merged the day before.

Pull requests from forks don't deploy, and neither do Dependabot's: neither gets the repository
secrets.

There is one concurrency group for every trigger, with `cancel-in-progress: false`: a deploy
waits for the one before it to finish and is never cancelled halfway through an upload.

The workflow needs:

- the `CLOUDFLARE_API_TOKEN` secret, a Cloudflare API token with Pages: Edit on the account;
- `CLOUDFLARE_ACCOUNT_ID`, set in the workflow as plain env (an account id isn't a secret).

The project already exists. Nothing creates it, and nothing prints the token.

## Which data it builds

Every deploy builds the latest parlamento-aberto `main`. `deploy/pages.py` fetches `origin main`
in the parlamento-aberto clone it is given and builds that commit, so even a clone that is behind
gets the newest data. There is no pin.

`main` only moves forward, and data only reaches it through its data PR checks, so each deploy has
the same data as the one before it or newer, whatever triggered it. A daily run and a later push to
`master` can't put older data back in production. A fixed pin would make the daily run rebuild the
same data forever, and a push to `master` would take production back to the pin.

When parlamento-aberto starts publishing data releases, the rule becomes "the latest release",
which `fiscaliza_data sync` already downloads when it gets no `--tag`. It moves forward the same way.

## What a deploy runs

```bash
python deploy/pages.py deploy --parlamento-aberto ~/src/parlamento-aberto --branch my-preview
```

This runs, in order:

1. `git fetch origin main` in that clone, then `git worktree add --detach` of the commit it got, and
   `uv run python -m parlamento_aberto.release build` there (the same command as its release
   workflow), into a scratch folder.
2. `python -m fiscaliza_data sync --from-dir <release>` into a scratch DuckDB folder.
3. `python -m fiscaliza_data.export --out frontend/public/api` (the static export, see
   [STATIC_EXPORT.md](STATIC_EXPORT.md)).
4. `npm ci` and `npm run build` in `frontend/`.
5. The Pages step on `frontend/dist`: it deletes `404.html` and copies `deploy/_headers` in, and
   checks the Pages limits (fewer than 20,000 files, every file under 25 MiB).
6. `wrangler pages deploy dist --project-name fiscaliza --branch <branch>`.

The scratch folder and the parlamento-aberto worktree are removed at the end. CI clones
parlamento-aberto with `--depth 1 --no-checkout`, so its data is checked out once, by step 1.

Options:

- `--branch NAME` picks the preview branch (default `preview`).
- `--production` deploys `master`. `--branch master` without it is refused, and so is
  `--production` with `--release`.
- `--release DIR` takes a `release build` folder you already have, for a preview only: it can be
  older than what is live.
- `--export-jobs N` caps the export's processes (default: one per CPU the machine reports). CI
  uses 2, and the deploy step stops after 45 minutes; a deploy takes about 5 minutes on 8 cores.
- `--work DIR` keeps the scratch files in that folder instead of a temporary one.
- `--dry-run` fetches main, prints every command and runs nothing else.
- `WRANGLER` overrides the wrangler command. The default is `npx --yes wrangler@4.151.3`, pinned
  so CI and a local run use the same version. Wrangler 4 needs Node 22 or newer; the workflow sets
  up Node 22.
- `python deploy/pages.py prepare frontend/dist` runs only step 5.

Run by hand, wrangler uses whatever Cloudflare login the machine has (`wrangler whoami` shows it),
or `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` when they are set. The script never logs in
and never creates tokens.

## Deep links

The app routes in the browser. On Pages, a build without a top-level `404.html` is treated as a
single-page app: any path with no file of its own gets `index.html` with status 200. The Pages step
deletes `404.html` for that reason. The plain `npm run build` keeps writing it, because GitHub
Pages, S3 and nginx with `error_page` need it.

A data file that doesn't exist under `/api` then answers with `index.html` too. The frontend
reads anything that isn't JSON as not found.

## Headers

`deploy/_headers`, copied into the build:

| Path | Header |
|---|---|
| `/assets/*` | `Cache-Control: public, max-age=31536000, immutable` (Vite hashes these names) |
| `/`, `/index.html` | `Cache-Control: no-cache` |
| `/api/*` | `Cache-Control: public, max-age=300` (the data changes per deploy, the names don't) |
| everything | HSTS for a year with subdomains, no preload; `X-Content-Type-Options: nosniff`; `Referrer-Policy: strict-origin-when-cross-origin`; `X-Frame-Options: DENY`; a `Permissions-Policy` that turns off camera, microphone and location; the CSP below |

Deep links fall under Pages' own default for HTML, `public, max-age=0, must-revalidate`.
Pages joins the same header from every matching rule with a comma, so `Cache-Control` is never
set on `/*`.

The CSP: scripts, data and frames from the site itself only (`frame-ancestors 'none'`), styles
from the site and Google Fonts (`'unsafe-inline'` for the style attributes Recharts and
framer-motion set), fonts from `fonts.gstatic.com`, and images from the site, `data:`,
`app.parlamento.pt` (the deputy photos in `picture_url`) and `www.parlamento.pt` (the photos on the
party demographics). A new external image, font or script host needs a line here,
and `tests/test_pages_deploy.py` fails when the frontend or `PICTURE_URL` uses an image host the CSP
doesn't allow.

If the API files ever move to another origin (`VITE_API_BASE_URL`), add it to `connect-src`.

## Before the custom domain

- A production deploy from `master` checked on `fiscaliza-ceg.pages.dev`.
- The `fiscaliza.pt` custom domain added to the Pages project (Cloudflare adds the DNS record,
  since the zone is on Cloudflare).
