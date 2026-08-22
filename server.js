#!/usr/bin/env node
/**
 * Live static server for the AAMS progress report.
 * Serves files from this directory, binds all interfaces, and
 * reloads the browser when HTML/CSS/JS on disk changes.
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const HOST = process.env.HOST || '0.0.0.0';
const PORT = Number(process.env.PORT) || 3000;
const ROOT = __dirname;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.map': 'application/json',
};

const clients = new Set();

const reloadSnippet = `
<script>
(function () {
  var es = new EventSource('/__live');
  es.onmessage = function () { location.reload(); };
})();
</script>
`;

function urlPath(url) {
  try {
    return decodeURIComponent((url || '/').split('?')[0]);
  } catch {
    return '/';
  }
}

function safeFile(url) {
  const rel = urlPath(url) === '/' ? 'index.html' : urlPath(url);
  const resolved = path.normalize(path.join(ROOT, rel));
  if (resolved !== ROOT && !resolved.startsWith(ROOT + path.sep)) return null;
  return resolved;
}

const server = http.createServer((req, res) => {
  if (urlPath(req.url) === '/__live') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'Access-Control-Allow-Origin': '*',
    });
    res.write('\n');
    clients.add(res);
    req.on('close', () => clients.delete(res));
    return;
  }

  let file = safeFile(req.url);
  if (!file) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('Forbidden');
    return;
  }

  if (fs.existsSync(file) && fs.statSync(file).isDirectory()) {
    file = path.join(file, 'index.html');
  }

  fs.readFile(file, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Not found');
      return;
    }

    const ext = path.extname(file).toLowerCase();
    const headers = {
      'Content-Type': MIME[ext] || 'application/octet-stream',
      'Cache-Control': 'no-store',
    };

    if (ext === '.html') {
      let html = data.toString('utf8');
      if (/<\/body>/i.test(html)) {
        html = html.replace(/<\/body>/i, reloadSnippet + '</body>');
      } else {
        html += reloadSnippet;
      }
      data = Buffer.from(html);
    }

    res.writeHead(200, headers);
    res.end(data);
  });
});

function broadcastReload() {
  for (const client of clients) {
    client.write('data: reload\n\n');
  }
}

let debounce;
function onChange(filename) {
  if (!filename) return;
  const name = String(filename);
  if (name.startsWith('.') || name.includes('node_modules') || name === 'server.js') return;
  clearTimeout(debounce);
  debounce = setTimeout(broadcastReload, 80);
}

try {
  fs.watch(ROOT, { recursive: true }, (_event, filename) => onChange(filename));
} catch {
  fs.watch(ROOT, (_event, filename) => onChange(filename));
}

server.listen(PORT, HOST, () => {
  console.log(`AAMS live server listening on http://${HOST}:${PORT}`);
});
