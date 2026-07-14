const axios = require('axios');

const GOGOANIME_URLS = process.env.GOGOANIME_URL
  ? [process.env.GOGOANIME_URL]
  : ['https://gogoanime.cl', 'https://gogoanimehd.io', 'https://gogoanime.org'];

async function searchGogoanime(query) {
  for (const baseUrl of GOGOANIME_URLS) {
    try {
      const html = await axios.get(`${baseUrl}/search.html`, {
        params: { keyword: query },
        timeout: 10000,
        headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' }
      }).then(r => r.data);

      const $ = require('cheerio').load(html);
      const results = [];

      $('.last_episode a, .items a').each((_, el) => {
        const href = $(el).attr('href');
        const title = $(el).attr('title') || $(el).text().trim();
        const img = $(el).find('img').attr('src');
        if (href && title) {
          const slug = href.replace('/category/', '').replace('/', '');
          results.push({ id: slug, title, image: img || '', source: 'gogoanime' });
        }
      });

      if (results.length > 0) return results;
    } catch {}
  }
  return [];
}

module.exports = async (req, res) => {
  const { q } = req.query;
  if (!q) return res.status(400).json({ error: 'Missing query parameter q' });
  res.setHeader('Access-Control-Allow-Origin', '*');
  try {
    const results = await searchGogoanime(q);
    res.json({ results });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
