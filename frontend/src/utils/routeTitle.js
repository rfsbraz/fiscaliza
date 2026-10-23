// The tab title after a client-side navigation. deploy/pages.py writes each route's own title
// into the HTML served for it, so the page loaded first already has the right one. The app
// doesn't set titles per route, so every other route goes back to the site title from
// index.html; a page with its own title (Metodologia, NotFound) sets it after this runs.
export const SITE_TITLE = 'Fiscaliza - Transparência Parlamentar';

export const routeTitle = (landing, path) => (path === landing.path ? landing.title : SITE_TITLE);
