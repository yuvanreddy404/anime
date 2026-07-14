const axios = require('axios');

const BROWSER = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';

const agent = new (require('https').Agent)({ keepAlive: true, rejectUnauthorized: false });

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');

  const target = 'https://api.allanime.day/api';

  try {
    const axiosConfig = {
      timeout: 20000,
      httpsAgent: agent,
      headers: {
        'User-Agent': BROWSER,
        'Origin': 'https://allmanga.to',
        'Referer': 'https://allmanga.to/',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
      },
      maxRedirects: 5,
      responseType: 'text',
      validateStatus: s => s < 500
    };

    if (req.method === 'POST') {
      axiosConfig.method = 'post';
      axiosConfig.data = req.body;
      axiosConfig.headers['Content-Type'] = 'application/json';
      const r = await axios(target, axiosConfig);
      res.status(r.status).setHeader('Content-Type', 'application/json');
      return res.send(r.data);
    }

    axiosConfig.method = 'get';
    axiosConfig.params = req.query;
    const r = await axios(target, axiosConfig);
    res.status(r.status).setHeader('Content-Type', 'application/json');
    res.send(r.data);
  } catch (e) {
    if (e.response) {
      res.status(e.response.status).send(e.response.data);
    } else {
      res.status(502).json({ error: e.message });
    }
  }
};
