# Changelog

All notable changes to this project will be documented in this file.

## [4.14.1] - Unreleased

### Added
- Web UI mode (`--web`) with search autocomplete, episode browser, and torrent selection
- Nyaa.si BitTorrent streaming as fallback when allanime sources are unavailable
- Modular provider system supporting multiple streaming sources in parallel
- Scraper API (Vercel serverless) for proxying allanime GraphQL and Nyaa.si scraping

### Changed
- Refactored provider framework: providers register independently in `providers/` directory
- Provider fetching runs in parallel for faster results
- Better error handling and fallback to torrent streaming

### Fixed
- Subshell bug where `use_external_menu` assignments were lost in child processes
- History output interleaving when processing parallel history entries
- PID tracking for webtorrent process (replaced `pkill -f`)
- Open proxy endpoints now restrict to allowed domains
- Stack trace leakage in API error responses
- Shellcheck SC2086 quoting issues

### Security
- Added domain allowlist to proxy endpoints
- Tracked webtorrent PID instead of using `pkill -f`
- Removed stack trace exposure in production error responses

## [4.13.0] - Upstream

### Added
- Filemoon provider support
- Dmenu support for external menu

### Changed
- Updated allanime API key and encryption handling
- Switched API requests to POST to bypass Cloudflare

### Fixed
- IINA next button hanging
- Steam Deck compatibility
- macOS downloading
- Allowed extensions error
