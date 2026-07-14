const http = require('http');
const https = require('https');
const url = require('url');
const ALLOWED_DOMAINS = (process.env.PROXY_ALLOWED_DOMAINS || 'allanime.to,allanime.day,allmanga.to,gogoanime3.co,gogoanime.cl,gogoanimehd.io,animepahe.ru,nyaa.si').split(',');

function isAllowed(targetUrl) {
  return ALLOWED_DOMAINS.some(d => targetUrl.hostname === d || targetUrl.hostname.endsWith('.' + d));
}

module.exports = async (req, res) => {
  const { u } = req.query;
  if (!u) return res.status(400).json({ error: 'Missing u parameter' });

  const targetUrl = new url.URL(u);
  if (!isAllowed(targetUrl)) return res.status(403).json({ error: 'Domain not allowed' });

  res.setHeader('Access-Control-Allow-Origin', '*');

  const isHttps = targetUrl.protocol === 'https:';
  const client = isHttps ? https : http;

  const options = {
    hostname: targetUrl.hostname,
    port: targetUrl.port || (isHttps ? 443 : 80),
    path: targetUrl.pathname + targetUrl.search,
    method: req.method,
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
      'Referer': targetUrl.origin + '/',
      'Accept': '*/*',
      'Range': req.headers.range || '',
    },
    timeout: 25000,
  };

  try {
    const proxyReq = client.request(options, (proxyRes) => {
      const statusCode = proxyRes.statusCode || 500;
      const forwardHeaders = ['content-type', 'content-length', 'content-range', 'accept-ranges', 'cache-control', 'date', 'etag', 'last-modified', 'server', 'set-cookie'];
      for (const h of forwardHeaders) {
        const val = proxyRes.headers[h];
        if (val) res.setHeader(h, val);
      }

      res.statusCode = statusCode;

      if ([301, 302, 303, 307, 308].includes(statusCode)) {
        const redirectUrl = proxyRes.headers.location;
        if (redirectUrl) {
          res.setHeader('Location', redirectUrl);
        }
      }

      proxyRes.pipe(res);
    });

    proxyReq.on('error', (e) => {
      res.status(500).json({ error: e.message });
    });

    proxyReq.on('timeout', () => {
      proxyReq.destroy();
      res.status(504).json({ error: 'Proxy timeout' });
    });

    proxyReq.end();
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
