# Static export

Fiscaliza runs as a static site. The data release is synced into a DuckDB file, every answer the
frontend needs is rendered to a JSON file, and the built frontend plus those files go to any
static host. No server runs at request time.

## Build it

```bash
python -m fiscaliza_data sync                                   # the release, into $FISCALIZA_DATA_DIR
python -m fiscaliza_data.export --out frontend/public/api       # every answer, as JSON
cd frontend && npm ci && npm run build                          # dist/ with the files under dist/api
```

`dist/` is the whole site. The export can also be written straight to `dist/api` after the
build. `--jobs N` sets the processes for the deputy files (default: all cores); the full release
takes a few minutes. The export writes a new folder and swaps it in only when everything rendered,
so a failed run leaves the previous one in place.

For `npm run dev`, render into `frontend/public/api` (gitignored) and the dev server serves it at
`/api`. The frontend reads the files from `VITE_API_BASE_URL`, set at build time, default `/api`
on the site's own origin. If the files live on another origin, that host has to send CORS headers.

## Layout

Legislatures, parties and coalitions appear in paths in one form: accents dropped, lowercase,
and every run of other characters (slash, space) turned into one dash. XVII is `xvii`, PàF is
`paf`, MDP/CDE is `mdp-cde`, CDS-PP is `cds-pp`. The export stops if two names give the same path.
The browser applies the same rule (`frontend/src/config/staticApi.js`), and accepts a legislature
as a numeral or a number (`17`), like the API.

| Endpoint | File |
|---|---|
| `legislaturas`, `estatisticas`, `partidos`, `health`, `estatisticas/atividade` | `legislaturas.json`, `estatisticas.json`, `partidos.json`, `health.json`, `estatisticas/atividade.json` |
| `votacoes/recentes?limite=5` (and the default, 10) | `votacoes/recentes/5.json`, `votacoes/recentes/10.json` |
| `coligacoes?include_inactive=false` / `true` | `coligacoes.json` / `coligacoes-todas.json` |
| `coligacoes/{id}`, `/deputados`, `/partidos` (one page per list and run: `ad-2024`, `ad-acores-2025`, `CDU`) | `coligacoes/{slug}.json`, `coligacoes/{slug}/deputados.json`, `coligacoes/{slug}/partidos.json` |
| `deputados?page&per_page&active_only&search` | `deputados.json`: everyone, in the list's order; search, filter and paging run in the browser |
| `deputados/{id}/detalhes`, `/conflitos-interesse`, `/atividades`, `/voting-analytics`, `/attendance` | `deputados/{id}.json`: one file per person with all of it, for every legislature they served in; interventions are filtered, sorted and paged in the browser |
| `partidos/{sigla}/deputados` | `partidos/{slug}/deputados.json` |
| `partidos/{sigla}/voting-analytics[?legislatura]` | `partidos/{slug}/voting-analytics.json`, `partidos/{slug}/voting-analytics/{legislature slug}.json` |

One file per deputy keeps the count growing with people rather than people times legislatures:
about 3,400 files on the full release instead of about 20,000. `tests/test_static_export.py`
fails if a render reaches 20,000 files or any file reaches 25 MiB, and the export itself refuses
to swap in such a render. Those limits fit the common static hosts (Cloudflare Pages, for one,
allows 20,000 files per deployment and 25 MiB per file); object storage behind a CDN has none.

The deputy files are rendered 50 people at a time. Each question the deputy page asks runs once
for the whole batch (`app/data/deputy_rows.py`), not once per person and legislature, and the
Flask routes build the same answers from the same rows for one person.

Requests the frontend does not make (for example `estatisticas?legislatura=XVI`, or a
deputy's activities in a legislature they never served in) are not rendered and answer 404.

## Not rendered yet

The agenda for today and this week (`agenda/hoje`, `agenda/semana`, S13) waits on its
parlamento-aberto mart. The browser answers it 503 "not available" with the step that brings
it, and the page shows its notice. It will get a file per week, with "today" picked in the
browser in Europe/Lisbon time.

Attendance (`deputados/{id}/attendance`, S11) is the `attendance` field of each deputy's file:
one `DeputySection` in `DEPUTY_SECTIONS` (`fiscaliza_data/export.py`) and one entry in
`staticApi.js`. A new deputy endpoint is added the same way.

The party endpoints render once S6 (#79) and S7 (#81) are on master; the export picks their
services up on its own.

## Deep links

The app routes in the browser, so `/deputados/123` has no file of its own. The build writes
`index.html` again as `404.html`. Hosts that serve `404.html` for a missing path load the app on
any deep link: GitHub Pages, Cloudflare Pages, S3 or CloudFront with `404.html` as the error
document, nginx with `error_page 404 /404.html`. Those answer deep links with status 404 and
the app still renders. To answer them 200, use the host's own SPA rule instead: nginx
`try_files $uri /index.html` or a rewrite to `/index.html` on a CDN. For Cloudflare Pages,
`deploy/pages.py` writes one HTML file per app route with that route's head, which answers 200
and keeps a real 404 for every other path, and a `sitemap.xml` of the same routes (see
[DEPLOY.md](DEPLOY.md)).

A missing data file then comes back as `404.html` (or `index.html`) instead of JSON. The
frontend reads anything that is not JSON as not found, so this is safe.

To try a build locally without Flask: `npm run preview` in `frontend/`, or any static server
with an index.html fallback.
