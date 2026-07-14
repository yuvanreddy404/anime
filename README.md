<p align=center>
<br>
<a href="http://makeapullrequest.com"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg"></a>
<a href="#macos"><img src="https://img.shields.io/badge/os-mac-brightgreen">
<a href="#linux"><img src="https://img.shields.io/badge/os-linux-brightgreen">
<br>
<h1 align="center">ani-cli</h1>
<h3 align="center">Browse, search, and watch anime. Terminal + Web UI.</h3>
</p>

This is a fork of [pystardust/ani-cli](https://github.com/pystardust/ani-cli) with a **web UI** and **Nyaa.si torrent streaming** via webtorrent.

**Why this fork?** The upstream ani-cli depends on allanime for video sources, which frequently breaks due to Cloudflare challenges and encryption changes. This fork adds Nyaa.si BitTorrent streaming as a fallback, plus a web interface for a more visual browsing experience.

## Features

- **Terminal mode** -- full upstream ani-cli experience (fzf-based search, episode selection, quality/player options, syncplay, downloads)
- **Web mode** (`--web`) -- browser-based UI with search autocomplete (thumbnails!), episode list, torrent selection table, and one-click playback
- **Nyaa.si torrent streaming** -- falls back to BitTorrent when allanime sources are unavailable. Searches Nyaa, lists results sorted by seeders, streams via webtorrent + mpv
- **Scraper API** -- deployable Vercel serverless functions that proxy allanime GraphQL and Nyaa.si HTML scraping (bypasses Cloudflare)

## Dependencies

- [webtorrent-cli](https://github.com/webtorrent/webtorrent-cli) -- BitTorrent streaming to mpv
- mpv -- video player
- Python 3 (for web mode)
- Standard upstream deps: `curl`, `grep`, `sed`, `fzf`, `openssl`, `ffmpeg`, `aria2c`, `yt-dlp`

**Install webtorrent-cli (macOS):**

```sh
brew install webtorrent-cli
```

**Install webtorrent-cli (other platforms):**

```sh
npm install -g webtorrent-cli
```

## Install

```sh
git clone https://github.com/yuvanreddy404/anime.git
cd anime
# Optional: install to PATH
sudo cp ani-cli /usr/local/bin/
```

## Usage

### Terminal mode (upstream)

```sh
./ani-cli "Blue Lock"
```

### Web mode

```sh
./ani-cli --web
```

Opens a local server at `http://127.0.0.1:8000/`. Search, browse episodes, select a torrent, and play -- mpv opens automatically via webtorrent.

### All flags

See `./ani-cli --help` for all upstream options (`-q` quality, `-d` download, `--dub`, `--vlc`, `--syncplay`, etc.)

## How It Works

```
User searches anime
  → allanime GraphQL (via Vercel proxy) returns show list + episodes
  → Nyaa.si (via Vercel proxy) returns torrents sorted by seeders
  → User selects a torrent → webtorrent download --mpv --port 8888
  → mpv opens, streaming begins
```

The Vercel scraper API proxies all scraping requests to bypass Cloudflare blocks. You can use the hosted instance or deploy your own.

## Deploy Your Own Scraper API

```sh
cd scraper-api
npm install
npx vercel --prod
```

Set the `SCRAPER` URL in `ani-server.py` and `ani-cli` to point to your deployment.

## License

GNU General Public License v3.0. See [LICENSE](./LICENSE).

Upstream: [pystardust/ani-cli](https://github.com/pystardust/ani-cli)
