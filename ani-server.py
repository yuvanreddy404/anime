#!/usr/bin/env python3
import http.server
import json
import subprocess
import urllib.request
import urllib.parse
import webbrowser
import os
import signal
import sys
import re

PORT = 8000
SCRAPER = "https://scraper-api-puce.vercel.app/api"

WEBTORRENT_PROC = None

ALLANIME_GQL = """query($search:SearchInput $limit:Int $page:Int $translationType:VaildTranslationTypeEnumType $countryOrigin:VaildCountryOriginEnumType){
  shows(search:$search limit:$limit page:$page translationType:$translationType countryOrigin:$countryOrigin){
    edges{_id name englishName availableEpisodes thumbnail __typename}
  }
}"""

EPISODES_GQL = """query($showId:String!){show(_id:$showId){_id availableEpisodesDetail}}"""


def search_allanime(q):
    data = json.dumps({
        "variables": {
            "search": {"allowAdult": False, "allowUnknown": False, "query": q},
            "limit": 40, "page": 1, "translationType": "sub", "countryOrigin": "ALL"
        }, "query": ALLANIME_GQL
    }).encode()
    req = urllib.request.Request(f"{SCRAPER}/allanime", data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read())
    edges = result.get("data", {}).get("shows", {}).get("edges", [])
    out = []
    for e in edges:
        eps = e.get("availableEpisodes", {})
        total = eps.get("sub", 0) or eps.get("dub", 0) or 0
        show_type = "Movie" if total == 1 else "Season"
        out.append({
            "id": e["_id"],
            "name": e.get("englishName") or e["name"],
            "englishName": e.get("englishName") or "",
            "thumbnail": e.get("thumbnail", ""),
            "episodes": total,
            "type": show_type
        })
    return out


def episodes_list(show_id):
    data = json.dumps({"variables": {"showId": show_id}, "query": EPISODES_GQL}).encode()
    req = urllib.request.Request(f"{SCRAPER}/allanime", data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read())
    detail = result.get("data", {}).get("show", {}).get("availableEpisodesDetail", {})
    eps = detail.get("sub", []) or detail.get("dub", []) or []
    return sorted(eps)


def search_nyaa(q):
    # strip parenthetical, vs, etc for better matching
    q = re.sub(r'\s*\(.*?\)|\s+vs\s+.*|\s+:\s+.*|\s+-\s+.*', '', q).strip()
    url = f"{SCRAPER}/nyaa?q={urllib.parse.quote(q)}"
    resp = urllib.request.urlopen(url, timeout=15)
    data = json.loads(resp.read())
    results = sorted(data.get("results", []), key=lambda x: -x.get("seeders", 0))
    return results[:40]


def kill_webtorrent():
    global WEBTORRENT_PROC
    if WEBTORRENT_PROC is not None:
        try:
            WEBTORRENT_PROC.kill()
            WEBTORRENT_PROC.wait(timeout=5)
        except Exception:
            try:
                os.kill(WEBTORRENT_PROC.pid, 9)
            except Exception:
                pass
        WEBTORRENT_PROC = None
    r = subprocess.run(["lsof", "-ti", ":8888"], capture_output=True, text=True)
    for pid in r.stdout.strip().split() or []:
        try:
            os.kill(int(pid), 15)
        except Exception:
            pass


def play_magnet(url, torrent_url=None):
    kill_webtorrent()
    download_url = url
    if torrent_url:
        try:
            m = re.search(r'urn:btih:([a-fA-F0-9]+)', url)
            if m:
                ih = m.group(1).lower()
                local = f"/tmp/{ih}.torrent"
                if not os.path.exists(local):
                    resp = urllib.request.urlopen(
                        f"{SCRAPER}/tfile?url={urllib.parse.quote(torrent_url)}", timeout=10
                    )
                    with open(local, "wb") as f:
                        f.write(resp.read())
                if os.path.exists(local):
                    download_url = local
        except Exception:
            pass
    global WEBTORRENT_PROC
    log = open("/tmp/webtorrent.log", "w")
    WEBTORRENT_PROC = subprocess.Popen(
        ["webtorrent", "download", download_url, "--mpv", "--port", "8888"],
        stdout=log, stderr=log
    )


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(HTML.encode())
            return

        if parsed.path == "/api/search":
            q = params.get("q", [""])[0]
            if not q:
                self._json({"error": "missing q"})
                return
            try:
                results = search_allanime(q)
                self._json(results)
            except Exception as e:
                self._json({"error": str(e)})
            return

        if parsed.path == "/api/episodes":
            show_id = params.get("id", [""])[0]
            if not show_id:
                self._json({"error": "missing id"})
                return
            try:
                eps = episodes_list(show_id)
                self._json(eps)
            except Exception as e:
                self._json({"error": str(e)})
            return

        if parsed.path == "/api/nyaa":
            q = params.get("q", [""])[0]
            if not q:
                self._json({"error": "missing q"})
                return
            try:
                results = search_nyaa(q)
                self._json(results)
            except Exception as e:
                self._json({"error": str(e)})
            return

        if parsed.path == "/api/play":
            url = params.get("url", [""])[0]
            if not url:
                self._json({"error": "missing url"})
                return
            turl = params.get("torrent", [""])[0] or None
            try:
                play_magnet(url, turl)
                self._json({"status": "ok"})
            except Exception as e:
                self._json({"error": str(e)})
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"404")

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, fmt, *args):
        return


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ani-cli web</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d0d12;color:#e0e0e0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh}
.container{max-width:900px;margin:0 auto;padding:20px}
header{text-align:center;padding:40px 0 30px}
header h1{font-size:2rem;font-weight:700;background:linear-gradient(135deg,#ff6b6b,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
header p{color:#666;margin-top:6px;font-size:.9rem}
.search-wrap{position:relative;margin-bottom:30px}
.search-wrap input{width:100%;padding:14px 18px;border:1px solid #2a2a3a;border-radius:12px;background:#1a1a25;color:#e0e0e0;font-size:1rem;outline:none;transition:border-color .2s}
.search-wrap input:focus{border-color:#a855f7}
.search-wrap input::placeholder{color:#555}
.suggestions{position:absolute;top:100%;left:0;right:0;background:#1a1a25;border:1px solid #2a2a3a;border-radius:12px;margin-top:6px;max-height:360px;overflow-y:auto;display:none;z-index:50;box-shadow:0 8px 32px rgba(0,0,0,.4)}
.suggestions.show{display:block}
.sug-item{display:flex;align-items:center;gap:12px;padding:10px 14px;cursor:pointer;transition:background .15s;border-bottom:1px solid #2a2a3a}
.sug-item:last-child{border-bottom:none}
.sug-item:hover{background:#2a2a3a}
.sug-item img{width:36px;height:50px;object-fit:cover;border-radius:6px;background:#2a2a3a}
.sug-item .sug-name{font-size:.85rem;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sug-item .sug-meta{font-size:.75rem;color:#666;margin-top:2px}
.loading{text-align:center;padding:40px;color:#555}
.loading .spinner{width:32px;height:32px;border:3px solid #2a2a3a;border-top-color:#a855f7;border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 12px}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes pulse{0%,100%{opacity:.4}50%{opacity:1}}
.error{text-align:center;padding:30px;color:#ff6b6b}
.results{display:flex;flex-direction:column;gap:10px}
.card{background:#1a1a25;border:1px solid #2a2a3a;border-radius:12px;padding:16px 20px;cursor:pointer;transition:all .2s}
.card:hover{border-color:#a855f7;background:#1e1e2e;transform:translateY(-1px)}
.card h3{font-size:1rem;font-weight:600;margin-bottom:4px}
.card .meta{font-size:.8rem;color:#888;display:flex;gap:12px}
.card .meta span{padding:2px 8px;border-radius:6px;background:#2a2a3a}
.card .episodes{font-size:.75rem;color:#666;margin-top:6px}
.episodes-grid{display:flex;flex-wrap:wrap;gap:6px;margin-top:20px}
.ep-btn{padding:8px 14px;border:1px solid #2a2a3a;border-radius:8px;background:#1a1a25;color:#e0e0e0;cursor:pointer;font-size:.85rem;transition:all .2s}
.ep-btn:hover{border-color:#a855f7;background:#2a2a3a}
.ep-btn.active{border-color:#a855f7;background:#a855f722}
.back-btn{display:inline-flex;align-items:center;gap:6px;color:#a855f7;cursor:pointer;font-size:.85rem;margin-bottom:16px;border:none;background:none;padding:0}
.back-btn:hover{text-decoration:underline}
.torrent-table{width:100%;border-collapse:collapse;margin-top:16px;font-size:.85rem}
.torrent-table th{text-align:left;padding:10px 12px;color:#888;border-bottom:1px solid #2a2a3a;font-weight:500}
.torrent-table td{padding:10px 12px;border-bottom:1px solid #1a1a25}
.torrent-table tr{cursor:pointer;transition:background .15s}
.torrent-table tr:hover{background:#2a2a3a}
.torrent-table tr:last-child td{border-bottom:none}
.seed{color:#4ade80;font-weight:600}
.size{color:#888}
.section-title{font-size:1rem;font-weight:600;margin-bottom:4px;color:#ccc}
.section-sub{font-size:.8rem;color:#666;margin-bottom:16px}
.hidden{display:none!important}
.overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(13,13,18,.92);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:100;backdrop-filter:blur(8px)}
.overlay .spinner-lg{width:48px;height:48px;border:3px solid #2a2a3a;border-top-color:#a855f7;border-radius:50%;animation:spin .8s linear infinite}
.overlay .status-text{color:#c084fc;font-size:1.1rem;margin-top:20px;animation:pulse 1.5s ease-in-out infinite}
.overlay .status-sub{color:#666;font-size:.85rem;margin-top:8px}
.overlay .cancel-btn{margin-top:24px;padding:8px 20px;border:1px solid #333;border-radius:8px;background:transparent;color:#888;cursor:pointer;font-size:.85rem;transition:all .2s}
.overlay .cancel-btn:hover{border-color:#ff6b6b;color:#ff6b6b}
@media(max-width:600px){
  .container{padding:12px}
  header h1{font-size:1.5rem}
}
</style>
</head>
<body>
<div class="container" id="app">
  <header>
    <h1>ani-cli</h1>
    <p>search &bull; select &bull; stream</p>
  </header>

  <div class="search-wrap">
    <input id="searchInput" type="text" placeholder="Search anime..." autofocus>
    <div id="suggestions" class="suggestions"></div>
  </div>

  <div id="content"></div>
</div>

<div id="playOverlay" class="overlay hidden">
  <div class="spinner-lg"></div>
  <div class="status-text" id="overlayStatus">Starting stream...</div>
  <div class="status-sub" id="overlaySub">Connecting to peers</div>
  <button class="cancel-btn" onclick="hideOverlay()">Cancel</button>
</div>

<script>
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const content = $('#content');
const searchInput = $('#searchInput');
let current = 'search';
let animeData = null;
let sugTimer = null;

searchInput.addEventListener('input', function() {
  clearTimeout(sugTimer);
  var q = this.value.trim();
  if (q.length < 2) { hideSuggestions(); return; }
  sugTimer = setTimeout(function() { fetchSuggestions(q); }, 250);
});

searchInput.addEventListener('keydown', function(e) {
  if (e.key === 'Enter') { hideSuggestions(); search(this.value.trim()); }
});

document.addEventListener('click', function(e) {
  if (!e.target.closest('.search-wrap')) hideSuggestions();
});

function fetchSuggestions(q) {
  fetch('/api/search?q=' + encodeURIComponent(q))
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.error || !data.length) { hideSuggestions(); return; }
      showSuggestions(data.slice(0, 8));
    })
    .catch(function() { hideSuggestions(); });
}

function showSuggestions(items) {
  var el = $('#suggestions');
  var html = '';
  items.forEach(function(a) {
    var thumb = a.thumbnail || '';
    var eps = a.episodes || 0;
    html += '<div class="sug-item" onclick="hideSuggestions();showEpisodes(\'' + a.id + '\',\'' + escHtml(a.name) + '\')">'
      + '<img src="' + thumb + '" alt="" loading="lazy" onerror="this.style.display=\'none\'">'
      + '<div><div class="sug-name">' + escHtml(a.name) + '</div>'
      + '<div class="sug-meta">' + eps + ' episodes</div></div></div>';
  });
  el.innerHTML = html;
  el.classList.add('show');
}

function hideSuggestions() {
  $('#suggestions').classList.remove('show');
}

function search(q) {
  if (!q) return;
  current = 'search';
  content.innerHTML = '<div class="loading"><div class="spinner"></div>Searching...</div>';
  fetch('/api/search?q=' + encodeURIComponent(q))
    .then(r => r.json())
    .then(data => {
      if (data.error) { showError(data.error); return; }
      if (!data.length) { content.innerHTML = '<div class="error">No results</div>'; return; }
      renderResults(data);
    })
    .catch(e => showError(e.message));
}

function renderResults(results) {
  let html = '<div class="results">';
  results.forEach(a => {
    html += `<div class="card" onclick="showEpisodes('${a.id}','${escHtml(a.name)}')">
      <h3>${escHtml(a.name)}</h3>
      <div class="meta">
        <span>${a.type}</span>
        <span>${a.episodes} ep</span>
      </div>
    </div>`;
  });
  html += '</div>';
  content.innerHTML = html;
}

function showEpisodes(id, name) {
  current = 'episodes';
  animeData = {id, name};
  content.innerHTML = `<button class="back-btn" onclick="goBack()">← Back to search</button>
    <div class="section-title">${escHtml(name)}</div>
    <div class="section-sub">Select episode</div>
    <div class="loading"><div class="spinner"></div>Loading episodes...</div>`;

  fetch('/api/episodes?id=' + id)
    .then(r => r.json())
    .then(eps => {
      if (eps.error) { showError(eps.error); return; }
      if (!eps.length) { showError('No episodes'); return; }
      let html = '<div class="episodes-grid">';
      eps.forEach(ep => {
        html += `<button class="ep-btn" onclick="searchTorrents(${ep},'${escHtml(name)}')">${ep}</button>`;
      });
      html += '</div>';
      content.innerHTML = `<button class="back-btn" onclick="goBack()">← Back to search</button>
        <div class="section-title">${escHtml(name)}</div>
        <div class="section-sub">Select episode</div>` + html;
    })
    .catch(e => showError(e.message));
}

function searchTorrents(ep, name) {
  current = 'torrents';
  content.innerHTML = `<button class="back-btn" onclick="showEpisodes('${animeData.id}','${escHtml(name)}')">← Back to episodes</button>
    <div class="section-title">${escHtml(name)} — Episode ${ep}</div>
    <div class="section-sub">Searching Nyaa.si torrents...</div>
    <div class="loading"><div class="spinner"></div></div>`;

  fetch('/api/nyaa?q=' + encodeURIComponent(name))
    .then(r => r.json())
    .then(data => {
      if (data.error) { showError(data.error); return; }
      if (!data.length) { showError('No torrents found'); return; }
      renderTorrents(data);
    })
    .catch(e => showError(e.message));
}

function renderTorrents(results) {
  let html = `<table class="torrent-table">
    <thead><tr><th>Torrent</th><th>Size</th><th>S</th><th>L</th></tr></thead><tbody>`;
  results.forEach(t => {
    html += `<tr onclick="play('${escHtml(t.magnet)}','${escHtml(t.title)}','${escHtml(t.torrent||'')}')">
      <td style="max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(t.title)}</td>
      <td class="size">${t.size||'?'}</td>
      <td class="seed">${t.seeders}</td>
      <td style="color:#888">${t.leechers}</td>
    </tr>`;
  });
  html += '</tbody></table>';
  content.innerHTML = `<button class="back-btn" onclick="showEpisodes('${animeData.id}','${escHtml(animeData.name)}')">← Back</button>
    <div class="section-title">Select torrent</div>
    <div class="section-sub">Click a row to start streaming</div>` + html;
}

function showOverlay(msg, sub) {
  const o = $('#playOverlay');
  o.classList.remove('hidden');
  $('#overlayStatus').textContent = msg || 'Starting stream...';
  $('#overlaySub').textContent = sub || '';
}
function hideOverlay() {
  $('#playOverlay').classList.add('hidden');
}

function play(url, title, turl) {
  showOverlay('Starting stream...', title);
  var btn = document.querySelector('.cancel-btn');
  btn.textContent = 'Waiting for peers...';
  var params = {url: url};
  if (turl) params.torrent = turl;
  fetch('/api/play?' + new URLSearchParams(params))
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.error) {
        showOverlay('Error: ' + data.error, '');
        return;
      }
      showOverlay('▶ Playing in mpv', title);
      btn.textContent = 'Done';
    })
    .catch(function(e) {
      showOverlay('Error: ' + e.message, '');
    });
}

function goBack() {
  content.innerHTML = '';
  searchInput.value = '';
  searchInput.focus();
  current = 'search';
}

function showError(msg) {
  content.innerHTML = '<div class="error">' + escHtml(msg) + '</div>';
}

function escHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
</script>
</body>
</html>"""


def main():
    import os, subprocess
    result = subprocess.run(["lsof", "-ti", f":{PORT}"], capture_output=True, text=True)
    for pid in result.stdout.strip().split() if result.stdout.strip() else []:
        try:
            os.kill(int(pid), 15)
        except (OSError, ValueError):
            pass
    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"\033[1;36m  ani-cli web UI\033[0m")
    print(f"  Open: \033[1;34m{url}\033[0m")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
