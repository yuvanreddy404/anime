const axios = require('axios');
const cheerio = require('cheerio');

const GOGO_BASE = process.env.GOGO_ANIME_URL || 'https://gogoanime3.co';
const ALLANIME_RELAY = process.env.ALLANIME_RELAY || 'https://relay-azure-six.vercel.app';
const BROWSER = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';

// Follow gogoanime JS challenge redirect chain
async function gogoFetch(path, params = {}) {
  const http = axios.create({ timeout: 15000, maxRedirects: 0, validateStatus: s => s < 400, headers: { 'User-Agent': BROWSER, Referer: GOGO_BASE } });
  try {
    const res = await http.get(`${GOGO_BASE}${path}`, { params });
    const html = res.data;
    // Check for JS redirect challenge
    const m = html.match(/window\.location\.replace\('([^']+)'/);
    if (m) {
      // Follow the redirect to the challenged URL
      const r2 = await axios.get(m[1], { timeout: 15000, headers: { 'User-Agent': BROWSER, Referer: GOGO_BASE } });
      return r2.data;
    }
    return html;
  } catch (e) {
    // Try direct fallback
    const direct = await axios.get(`${GOGO_BASE}${path}`, { params, timeout: 15000, headers: { 'User-Agent': BROWSER, Referer: GOGO_BASE } });
    return direct.data;
  }
}

// ---- gogoanime ----

async function gogoSearch(query) {
  try {
    const html = await gogoFetch('/search.html', { keyword: query });
    const $ = cheerio.load(html);
    const results = [];
    $('.items a').each((_, el) => {
      const href = $(el).attr('href');
      const title = $(el).attr('title') || '';
      if (href && title) {
        results.push({ id: href.replace('/category/', '').replace(/^\/+/, ''), title, source: 'gogo', image: $(el).find('img').attr('src') || '' });
      }
    });
    if (results.length) return results;
  } catch {}
  return [];
}

async function gogoEpisodes(animeId) {
  try {
    const html = await gogoFetch(`/category/${animeId}`);
    const $ = cheerio.load(html);
    const eps = [];
    $('#episode_page a').each((_, el) => {
      const start = $(el).attr('ep_start');
      if (start) eps.push({ num: parseInt(start), id: start });
    });
    if (eps.length) return eps.sort((a, b) => a.num - b.num);
  } catch {}
  return [];
}

async function gogoSources(animeId, epNum) {
  try {
    const html = await gogoFetch(`/${animeId}-episode-${epNum}`);
    const $ = cheerio.load(html);
    const sources = [];
    $('a[data-video]').each((_, el) => {
      sources.push({ server: $(el).text().trim() || 'unknown', url: $(el).attr('data-video'), quality: '' });
    });
    if (sources.length) return sources;
  } catch {}
  return [];
}

// ---- allanime (via relay) ----

async function allanimeSearch(query) {
  try {
    const { data } = await axios.post(`${ALLANIME_RELAY}/a/api`, {
      query: 'query ($search: SearchInput!) { shows(search: $search) { edges { _id name availableEpisodesDetail } } }',
      variables: { search: { allowAdult: false, allowUnknown: false, query } }
    }, { timeout: 10000, headers: { 'User-Agent': BROWSER } });
    const edges = data?.data?.shows?.edges || [];
    const results = [];
    for (const e of edges) {
      const aed = e.availableEpisodesDetail || {};
      if (Object.values(aed).some(v => v && v.length > 0)) {
        results.push({ id: e._id, title: e.name, source: 'allanime', image: '' });
      }
    }
    return results.slice(0, 10);
  } catch {}
  return [];
}

async function allanimeEpisodes(showId) {
  try {
    const { data } = await axios.post(`${ALLANIME_RELAY}/a/api`, {
      query: 'query ($showId: String!) { show(_id: $showId) { availableEpisodesDetail } }',
      variables: { showId }
    }, { timeout: 10000, headers: { 'User-Agent': BROWSER } });
    const aed = data?.data?.show?.availableEpisodesDetail || {};
    const allEps = [...(aed.sub || []), ...(aed.dub || []), ...(aed.raw || [])];
    return allEps.map(s => ({ num: parseInt(s.replace(/\D/g, '') || '0'), id: s })).sort((a, b) => a.num - b.num);
  } catch {}
  return [];
}

// ---- main handler ----

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const { q, id, ep } = req.query;

  try {
    if (q) {
      let r = await gogoSearch(q);
      if (!r.length) r = await allanimeSearch(q);
      return res.json({ results: r });
    }
    if (id && ep) {
      let r = await gogoSources(id, ep);
      return res.json({ sources: r });
    }
    if (id) {
      let r = await gogoEpisodes(id);
      if (!r.length) r = await allanimeEpisodes(id);
      return res.json({ episodes: r });
    }
    res.status(400).json({ error: 'Use q=query, id=anime&ep=N, or id=anime' });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
