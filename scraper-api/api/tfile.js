const axios = require('axios');

const BROWSER = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const { url } = req.query;
  if (!url) return res.status(400).json({ error: 'missing url' });

  try {
    const response = await axios.get(url, {
      responseType: 'arraybuffer',
      timeout: 20000,
      headers: { 'User-Agent': BROWSER, Referer: 'https://nyaa.si/' }
    });
    res.setHeader('Content-Type', 'application/x-bittorrent');
    res.send(Buffer.from(response.data));
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
