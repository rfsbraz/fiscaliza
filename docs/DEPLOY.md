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
its own; its preview shows the new data before it merges. Most moves are automatic (see
[Automatic pin moves](#automatic-pin-moves)); I still move it by hand when a change needs new
figures checked first, as in #132.

Before moving it, build a release from the new commit and run `tests/test_release_pin.py` on it
with `FISCALIZA_RELEASE_DIR` set to that folder. The test checks the release was built from the
pin and holds the figures the pin move is for; update them in the same pull request.

When parlamento-aberto turns on data releases (`DATA_RELEASES`), the pin moves to a release tag.

## Automatic pin moves

When parlamento-aberto `main` changes, a pin PR opens here and merges itself once every check on
it is green (#133). This is my one exception to merging by hand, for pin PRs only. `master`
has no branch protection or required checks, so GitHub's auto-merge can't wait for CI; two
workflows do the job instead, and `deploy/pin_bump.py` holds the logic (tested in
`tests/test_pin_bump.py`).

1. parlamento-aberto's `fiscaliza-dispatch.yml` runs on every push to its `main` and sends a
   `repository_dispatch` here: event type `data-updated`, payload `{"sha": "<commit>"}`.
2. `data-pin-bump.yml` (`Pin Bump`) checks the SHA is a full commit on parlamento-aberto `main`.
   When the pin on `master` already has it, or it is older than the pin, it stops there and opens
   nothing. Otherwise it resets the branch `data/pin-bump` from `master`, writes the new pin and
   force-pushes that branch. That is the only branch anything force-pushes. Then it opens the pin
   PR, or updates the open one, so there is only ever one. The title is
   `chore(data): move the data pin to parlamento-aberto <short sha>`, and the body lists the old
   and new SHAs and the parlamento-aberto commits in between. A newer dispatch cancels a running
   one and replaces the PR's head.
3. The PR's CI and preview Deploy run as on any PR.
4. `data-pin-merge.yml` (`Pin Merge`) runs each time CI or Deploy finishes on `data/pin-bump`. It
   looks at every workflow run on the PR head: while one is still going it exits and waits for the
   next one to finish, so it never sits on a runner while CI runs. When all of them passed, and CI
   and Deploy are among them, it squash-merges the PR at that head. The push to `master` then
   deploys production.

Both workflows run on GitHub-hosted runners (`ubuntu-latest`), like CI and Deploy.

### Guard stops

`Pin Merge` doesn't merge, leaves the PR open with a comment saying why, and fails, when:

- a workflow on the PR head failed, was cancelled or timed out;
- the checks haven't finished 6 hours after the pin commit;
- the `schema_version` major in parlamento-aberto (`src/parlamento_aberto/models/schema.yml`)
  differs between the old and the new pin (`Pin Bump` comments on this one too, right away);
- the PR changes anything other than `deploy/data-pin`;
- GitHub refuses the merge, for example when `master` moved the pin itself and the PR conflicts.

A stopped head never merges later. I look at it and merge or close the PR by hand. The next
parlamento-aberto commit resets the branch and starts again.

### Secrets

| Repo | Secret | Token |
|---|---|---|
| `rfsbraz/parliament` | `PIN_BOT_TOKEN` | fine-grained token, repository access only `rfsbraz/parliament`, with Contents: read and write and Pull requests: read and write (Metadata: read comes with it) |
| `rfsbraz/parlamento-aberto` | `FISCALIZA_DISPATCH_TOKEN` | fine-grained token, repository access only `rfsbraz/parliament`, with Contents: read and write |

`PIN_BOT_TOKEN` pushes `data/pin-bump`, opens and edits the PR and merges it. A PR opened or merged
with `GITHUB_TOKEN` starts no workflows, so without it the PR would get no CI and the merge no
production Deploy. The workflows' own `GITHUB_TOKEN` does the reads (parlamento-aberto is public)
and posts the guard comments. Both workflows stop on their first step with an error naming
`PIN_BOT_TOKEN` when it is missing.

`FISCALIZA_DISPATCH_TOKEN` only sends the dispatch. GitHub asks for Contents: write on the target
repo for `POST /repos/{owner}/{repo}/dispatches`, so that is the smallest it can be. One token
with Contents and Pull requests read and write on `rfsbraz/parliament` would work for both,
stored under both names, but I keep two so each can be revoked alone. Neither goes anywhere but
the repo secrets.

If the push of `data/pin-bump` is ever refused because `master` changed a workflow file since the
branch was last pushed, close the pin PR and delete the branch; the next run recreates it.

### Manual run

Actions, `Data Pin Bump`, Run workflow, with a parlamento-aberto commit SHA (all 40 characters).
With the current pin it does nothing and opens no PR, which is the quickest check that the token
works. `gh workflow run data-pin-bump.yml -f sha=<sha>` does the same.

When parlamento-aberto turns on data releases, the dispatch moves to `release: published` and the
pin to the release tag (#57). Related: #132 (the last move by hand) and #128 (the methodology page
says the site only changes data version on purpose, which now means through a pin PR that passed
CI, not one I opened by hand).

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
(`/deputados`, `/deputados/*`, `/partidos`, `/partidos/*`, `/coligacoes/*`, `/agenda`,
`/metodologia`) to `/`
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
