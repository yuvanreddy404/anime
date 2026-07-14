const axios = require('axios');
const cheerio = require('cheerio');

const GOGOANIME_URLS = process.env.GOGOANIME_URL
  ? [process.env.GOGOANIME_URL]
  : ['https://gogoanime.cl', 'https://gogoanimehd.io', 'https://gogoanime.org'];

async function extractSources(animeId, epNum) {
  for (const baseUrl of GOGOANIME_URLS) {
    try {
      const pageUrl = `${baseUrl}/${animeId}-episode-${epNum}`;
      const html = await axios.get(pageUrl, {
        timeout: 15000,
        headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' }
      }).then(r => r.data);

      const $ = cheerio.load(html);
      const sources = [];

      $('a[data-video], .anime_muti_link a, #list-server a').each((_, el) => {
        const videoUrl = $(el).attr('data-video') ||
          $(el).attr('data-target') || $(el).attr('href');
        const server = $(el).text().trim() || $(el).attr('title') || '';
        if (videoUrl) {
          sources.push({
            server: server.replace(/choose this server/i, '').trim() || 'unknown',
            url: videoUrl.startsWith('http') ? videoUrl : `${baseUrl}${videoUrl}`,
            quality: ''
          });
        }
      });

      if (sources.length > 0) return sources;
    } catch {}
  }
  return [];
}

module.exports = async (req, res) => {
  const { id, ep } = req.query;
  if (!id || !ep) return res.status(400).json({ error: 'Missing id or ep parameter' });
  res.setHeader('Access-Control-Allow-Origin', '*');
  try {
    const sources = await extractSources(id, ep);
    res.json({ sources });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
