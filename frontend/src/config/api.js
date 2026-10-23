/**
 * API Configuration
 *
 * The site reads the static export (python -m fiscaliza_data.export), not a live API. The
 * export's folder is served at VITE_API_BASE_URL, set at build time (default /api on the
 * site's own origin). apiFetch keeps the shape of a fetch to the API: it maps the endpoint to
 * its JSON file and answers with a Response, so the pages are unchanged.
 * See docs/STATIC_EXPORT.md.
 */
import { createStaticApi } from './staticApi.js';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

/**
 * Helper function to build URLs under the export's folder
 * @param {string} path - A file path in the export (without leading slash)
 * @returns {string} - Complete URL
 */
export const buildApiUrl = (path) => {
  // Remove leading slash if present
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;
  return `${API_BASE_URL}/${cleanPath}`;
};

const staticApi = createStaticApi({
  load: async (path) => {
    const response = await fetch(buildApiUrl(path), { headers: { Accept: 'application/json' } });
    return { ok: response.ok, status: response.status, text: response.ok ? await response.text() : '' };
  },
});

/**
 * Answer an API request from the static export, with error handling
 * @param {string} endpoint - The API endpoint, with its query string
 * @returns {Promise<Response>} - The endpoint's JSON as a Response
 */
export const apiFetch = async (endpoint) => {
  const { status, body } = await staticApi.get(endpoint);
  const response = new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Não foi possível carregar os dados (erro ${status}).`);
  }

  return response;
};
