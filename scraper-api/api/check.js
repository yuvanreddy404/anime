const axios = require('axios');
const BROWSER = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';

async function check(url) {
  try {
    const res = await axios.get(url, { timeout: 10000, headers: { 'User-Agent': BROWSER }, maxRedirects: 5 });
    const html = res.data;
    const hasChallenge = html.includes('challenges.cloudflare') || html.includes('window.location.replace') || html.includes('fingerprint');
    const isBlocked = res.status >= 400 || res.data.length < 100;
    return { status: res.status, size: res.data.length, challenge: hasChallenge, blocked: isBlocked || hasChallenge };
  } catch (e) {
    return { status: e.response?.status || 'err', error: e.message, blocked: true };
  }
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const sites = [
    ['gogoanime3.co', 'https://gogoanime3.co/search.html?keyword=naruto'],
    ['animixplay.fun', 'https://animixplay.fun'],
    ['animesuge.to', 'https://animesuge.to/search?keyword=naruto'],
    ['kissanime.com.ru', 'https://kissanime.com.ru'],
    ['animepahe.ru', 'https://animepahe.ru/anime'],
    ['hianime.to', 'https://hianime.to/home'],
    ['9anime.pl', 'https://9anime.pl'],
    ['aniwave.to', 'https://aniwave.to/filter'],
    ['animefox.to', 'https://animefox.to'],
    ['membed.net', 'https://membed.net'],
  ];
  const results = {};
  for (const [name, u] of sites) {
    results[name] = await check(u);
  }
  res.json(results);
};
