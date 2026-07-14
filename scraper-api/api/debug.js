const axios = require('axios');
module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const { url } = req.query;
  if (!url) return res.json({ error: 'need url param' });
  try {
    const r = await axios.get(url, {
      timeout: 15000,
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' },
      maxRedirects: 5
    });
    res.json({
      status: r.status,
      headers: r.headers,
      body: r.data.substring(0, 2000)
    });
  } catch (e) {
    res.json({ error: e.message, code: e.code, status: e.response?.status });
  }
};
