# Deploy

Fiscaliza is a static site on Cloudflare Pages, project `fiscaliza`, uploaded with
`wrangler pages deploy` (direct upload, no Git integration). The production branch is `master`, at
`fiscaliza-ceg.pages.dev`; anything else is a preview at `<branch>.fiscaliza-ceg.pages.dev` (Pages
turns `/` and other characters in the branch name into `-`).

Deploys run in CI, in `.github/workflows/deploy.yml`, on a GitHub-hosted runner
(`ubuntu-latest`). The workflow only calls `deploy/pages.py`; everything a deploy does is in that
script.

## When it deploys

| Trigger | Deploys |
|---|---|
| Push to `master` | production |
| Pull request from this repo that changes the site, or has the `preview` label | a preview on a Pages branch named after the PR's head branch |

There is no schedule: the data only changes when the pin moves, and moving the pin is a pull
request, which deploys production when it merges.

Pull requests from forks don't deploy, and neither do Dependabot's: neither gets the repository
secrets.

A deploy builds the whole site and uploads it, so a pull request only gets a preview when it needs
one. A short `Preview Needed` job diffs the PR against master and lets the deploy run when
something changed under `frontend/`, `fiscaliza_data/`, `app/` or `deploy/`, or in
`.github/workflows/deploy.yml` (`PREVIEW_PATHS` in the workflow). Anything else, such as docs or
tests, gets no deploy job.

To get a preview for any other pull request, add the `preview` label. Adding it starts a deploy
right away, and every later push to that PR deploys again until the label comes off. Adding any
other label starts nothing.

There is one concurrency group for every trigger, with `cancel-in-progress: false`: a deploy
waits for the one before it to finish and is never cancelled halfway through an upload. The group
is on the deploy job, so a pull request that needs no preview doesn't wait behind a running deploy
just to skip.

The workflow needs:

- the `CLOUDFLARE_API_TOKEN` secret, a Cloudflare API token with Pages: Edit on the account;
- `CLOUDFLARE_ACCOUNT_ID`, set in the workflow as plain env (an account id isn't a secret).

The project already exists. Nothing creates it, and nothing prints the token.

## The data pin

`deploy/data-pin` holds the parlamento-aberto commit the site is built from, and its release tag
when there is one. It is the only place the data version is set, and every deploy, production and
preview, builds exactly that commit.

Production is pinned because CI starts from an empty data folder each time: the sync's check that
no table lost more than 5% of its rows has nothing to compare against, so a bad commit on
parlamento-aberto `main` would go straight to production. Moving the pin is a small pull request of
its own, after checking the new data; its preview shows the new data before it merges.

When parlamento-aberto turns on data releases (`DATA_RELEASES`), the pin moves to a release tag.

## What a deploy runs

```bash
python deploy/pages.py deploy --parlamento-aberto ~/src/parlamento-aberto --branch my-preview
```

This runs, in order:

1. A fetch of the pinned SHA when the clone doesn't have it (one commit deep in a shallow clone),
   then `git worktree add --detach` of the pinned commit, and
   `uv run python -m parlamento_aberto.release build` there (the same command as its release
   workflow), into a scratch folder.
2. `python -m fiscaliza_data sync --from-dir <release>` into a scratch DuckDB folder.
3. `python -m fiscaliza_data.export --out frontend/public/api` (the static export, see
   [STATIC_EXPORT.md](STATIC_EXPORT.md)).
4. `npm ci` and `npm run build` in `frontend/`.
5. The Pages step on `frontend/dist`: it copies `deploy/_headers` and `deploy/_redirects` in, keeps
   the build's `404.html` (the app again), and checks the Pages limits (fewer than 20,000 files,
   every file under 25 MiB). `_redirects` answers the app's routes with the app and status 200.
   Any other path with no file gets `404.html` and status 404, and the app shows its "Página não
   encontrada" view. A new route in `frontend/src/App.jsx` needs a line in `_redirects`, and
   `tests/test_pages_deploy.py` checks that.
6. `wrangler pages deploy dist --project-name fiscaliza --branch <branch>`.

The scratch folder and the parlamento-aberto worktree are removed at the end. CI clones
parlamento-aberto with `--depth 1 --no-checkout`, so its data is checked out once, by step 1, and
fetches the pinned commit if `main` has moved past it.

Options:

- `--branch NAME` picks the preview branch (default `preview`).
- `--production` deploys `master`. `--branch master` without it is refused.
- `--release DIR` takes a `release build` folder you already have. Its `manifest.json` must name
  the pinned commit as `data_commit`, or the script stops.
- With no source and a `tag=` in the pin, the sync downloads that release from GitHub.
- `EXPORT_WORKERS` sets the export's processes. Without it the export uses the cgroup CPU limit
  (`/sys/fs/cgroup/cpu.max`), and without that the CPU count. Each process uses one DuckDB thread.
  CI leaves `EXPORT_WORKERS` unset, so the export uses the runner's CPUs. The deploy step stops
  after 80 minutes and the job after 90; a deploy normally takes a few minutes.
- `--work DIR` keeps the scratch files in that folder instead of a temporary one.
- `--dry-run` prints every command and runs nothing.
- `WRANGLER` overrides the wrangler command. The default is `npx --yes wrangler@4.151.3`, pinned
  so CI and a local run use the same version. Wrangler 4 needs Node 22 or newer; the workflow sets
  up Node 22.
- `python deploy/pages.py prepare frontend/dist` runs only step 5.

Run by hand, wrangler uses whatever Cloudflare login the machine has (`wrangler whoami` shows it),
or `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` when they are set. The script never logs in
and never creates tokens.

## Deep links

The app routes in the browser. `deploy/_redirects` rewrites each of the app's routes
(`/deputados`, `/deputados/*`, `/partidos`, `/partidos/*`, `/coligacoes/*`, `/agenda`) to `/`
with status 200, so a deep link loads the app. The rewrite goes to `/`, not `/index.html`, because
Pages turns `/index.html` into `/` and the rewrite would loop. `/` itself is `index.html`.

Every other path with no file, such as `/sobre` or `/sitemap.xml`, gets the top-level `404.html`
with status 404. That file is the app again, written by the build, and the app shows its "Página
não encontrada" view with `noindex`. `/robots.txt` is a real file from `frontend/public`. There's
no sitemap.

A data file that doesn't exist under `/api` also answers 404. The frontend reads anything that
isn't JSON as not found.

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
