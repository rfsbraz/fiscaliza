// Answers a list of API requests from a static export, the way the browser does.
// Usage: node scripts/static-answers.mjs <export dir>  < requests.json  > answers.json
// Used by tests/test_static_export.py to compare the static answers with Flask.
import { readFile } from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { createStaticApi } from '../src/config/staticApi.js';

const root = process.argv[2];
const requests = JSON.parse(readFileSync(0, 'utf8'));
const api = createStaticApi({
  load: async (file) => {
    try {
      return { ok: true, status: 200, text: await readFile(path.join(root, file), 'utf8') };
    } catch {
      return { ok: false, status: 404, text: '' };
    }
  },
});
const answers = [];
for (const request of requests) answers.push(await api.get(request));
process.stdout.write(JSON.stringify(answers));
