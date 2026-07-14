const axios = require('axios');
const ALLOWED_DOMAINS = (process.env.PROXY_ALLOWED_DOMAINS || 'allanime.to,allanime.day,allmanga.to,gogoanime3.co,gogoanime.cl,gogoanimehd.io,animepahe.ru,nyaa.si').split(',');

function isAllowed(url) {
  try {
    const hostname = new URL(url).hostname;
    return ALLOWED_DOMAINS.some(d => hostname === d || hostname.endsWith('.' + d));
  } catch { return false; }
}

module.exports = async (req, res) => {
  const { url } = req.query;
  if (!url) return res.status(400).json({ error: 'Missing url param' });
  if (!isAllowed(url)) return res.status(403).json({ error: 'Domain not allowed' });
  
  res.setHeader('Access-Control-Allow-Origin', '*');
  
  try {
    const response = await axios.get(url, {
      timeout: 30000,
      responseType: 'stream',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://allmanga.to/',
        'Origin': 'https://allmanga.to',
        'Accept': 'video/mp4,*/*',
      },
      maxRedirects: 5,
    });

    if (response.headers['content-type']) {
      res.setHeader('Content-Type', response.headers['content-type']);
    }
    if (response.headers['content-length']) {
      res.setHeader('Content-Length', response.headers['content-length']);
    }

    response.data.pipe(res);
  } catch (e) {
    res.status(e.response?.status || 500).json({ error: e.message });
  }
};
