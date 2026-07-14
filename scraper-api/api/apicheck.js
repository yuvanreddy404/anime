const axios = require('axios');
const BROWSER = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36';

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  try {
    const r = await axios.post('https://animixplay.fun/api/search', 
      { q: 'frieren' },
      { timeout: 15000, headers: { 'User-Agent': BROWSER, 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' } }
    );
    res.json({ status: r.status, data: r.data });
  } catch (e) {
    res.json({ error: e.message, status: e.response?.status, data: e.response?.data });
  }
};
