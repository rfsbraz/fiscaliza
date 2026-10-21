# Deploy

Fiscaliza is a static site on Cloudflare Pages, project `fiscaliza`, uploaded with
`wrangler pages deploy` (direct upload, no Git integration). The production branch is `master`;
anything else is a preview at `<branch>.fiscaliza.pages.dev`.

## The data pin

`deploy/data-pin` holds the parlamento-aberto commit the site is built from, and its release tag
when there is one. It is the only place the data version is set. Moving it is a reviewed commit
of its own, after checking the new data.

## Deploy a preview

```bash
python deploy/pages.py deploy --parlamento-aberto ~/src/parlamento-aberto
```

This runs, in order:

1. `git worktree add --detach` of the pinned commit in that checkout, and
   `uv run python -m parlamento_aberto.release build` there (the same command as its release
   workflow), into a scratch folder.
2. `python -m fiscaliza_data sync --from-dir <release>` into a scratch DuckDB folder.
3. `python -m fiscaliza_data.export --out frontend/public/api` (the static export, see
   [STATIC_EXPORT.md](STATIC_EXPORT.md)).
4. `npm ci` and `npm run build` in `frontend/`.
5. The Pages step on `frontend/dist`: it deletes `404.html` and copies `deploy/_headers` in, and
   checks the Pages limits (fewer than 20,000 files, every file under 25 MiB).
6. `wrangler pages deploy dist --project-name fiscaliza --branch preview`.

The scratch folder and the parlamento-aberto worktree are removed at the end.

Other ways in:

- `--release DIR` takes a `release build` folder you already have. Its `manifest.json` must name
  the pinned commit as `data_commit`, or the script stops.
- With no source and a `tag=` in the pin, the sync downloads that release from GitHub.
- `--branch NAME` deploys another preview branch.
- `--dry-run` prints every command and runs nothing.
- `WRANGLER` overrides the wrangler command (default `npx --yes wrangler@4`, which needs
  Node 22 or newer).
- `python deploy/pages.py prepare frontend/dist` runs only step 5.

Wrangler uses whatever Cloudflare login the machine already has (`wrangler whoami` shows it).
The script never logs in and never creates tokens.

## Production

```bash
python deploy/pages.py deploy --parlamento-aberto ~/src/parlamento-aberto --production
```

Production is the `master` branch on Pages and only deploys with `--production`. `--branch master`
without it is refused.

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
framer-motion set), fonts from `fonts.gstatic.com`, and images from the site, `data:` and
`www.parlamento.pt` (deputy photos). A new external image, font or script host needs a line here,
and `tests/test_pages_deploy.py` fails when the frontend adds an image host the CSP doesn't allow.

If the API files ever move to another origin (`VITE_API_BASE_URL`), add it to `connect-src`.

## Before production

- #68, #79, #81 and #91 merged, and this deploy run from `master`.
- A preview checked on `preview.fiscaliza.pages.dev`.
- The `fiscaliza.pt` custom domain added to the Pages project (Cloudflare adds the DNS record,
  since the zone is on Cloudflare).
