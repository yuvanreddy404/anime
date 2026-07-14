# Hacking ani-cli

Ani-cli is set up to scrape one platform - currently allanime. The modular provider system allows multiple streaming sources to be supported simultaneously.

## Provider Architecture

The provider system is a modular framework that allows the script to:

- **Discover** every available streaming source for a given episode
- **Fetch** stream metadata from all sources in parallel
- **Present** a unified selection menu with quality metadata
- **Fall back** if a chosen provider's stream fails

### Provider Modules

Each provider is a separate file in `providers/` that registers itself via:

```
provider_register <id> <display_name> <extract_regex> [fetch_type]
```

| Parameter     | Description                                    |
|---------------|------------------------------------------------|
| `id`          | Unique identifier (e.g. `wixmp`, `youtube`)    |
| `display_name`| Human-readable name (e.g. `WixMP`, `YouTube`)  |
| `extract_regex`| `sed` expression to extract source URL from `$resp` |
| `fetch_type`  | `"default"` (uses `get_links`) or custom type   |

Example provider module (`providers/wixmp.sh`):
```sh
provider_register "wixmp" "WixMP" "/Default :/p" "default"
```

### Adding a new provider

1. Create `providers/yourprovider.sh`
2. Add a single `provider_register` call with the appropriate extraction regex
3. If the provider needs custom fetch logic (like Filemoon's decryption), add it to the main script and set `fetch_type` to a unique name, then handle it in `provider_fetch_streams()`

### Provider System Files

| File | Purpose |
|------|---------|
| `providers/provider.sh` | Framework: registration, detection, caching, selection menu |
| `providers/wixmp.sh`    | WixMP (default HLS source) |
| `providers/youtube.sh`  | YouTube (web source) |
| `providers/sharepoint.sh`| SharePoint (web source) |
| `providers/mp4upload.sh` | Mp4Upload (direct MP4) |
| `providers/filemoon.sh` | Filemoon (encrypted HLS source) |

### User Flow

```
Search anime → select → choose episode
     ↓
Fetch all available providers in parallel
     ↓
Provider selection menu (fzf / bash select)
     ↓
Quality selection
     ↓
Play with chosen provider
     ↓
On failure: prompt to try another provider
```

### Environment Variables

| Variable | Effect |
|----------|--------|
| `ANI_DEBUG=1` | Print debug logs during provider fetching |

---

## Prerequisites

Here's the of skills you'll need and the guide will take for granted:
- basic shell scripting
- understanding of http(s) requests and proficiency with curl
- ability to read html and javascript on a basic level and search them
- writing regexes
You'll also need web browser with a debugger and environment that can run unmodified ani-cli

## The scraping process
The following flowchart demonstrates how ani-cli operates from a scraping standpoint:

![image](.assets/ani-cli-scraping-flow.png)

The steps to get to a link from a query is the following:
1. search with the site's search page for the query
2. extract IDs from response, user chooses one
3. extract episode numbers from an overview page, user chooses one
4. the provider system discovers and fetches every available streaming source for the selected episode
5. the user selects a provider from the menu
6. quality selection selects one stream that is played
From here 1-4 need to be changed to support another site. #Reverse-engineering will answer how.

## Reverse-engineering
Many sites have various protections against reverse-engineering.
The extension webapi-blocker can help you with bringing up the debugger that we'll use during this guide or to conceal the presence of a debugger.
These reverse-engineering protections are always evolving though so there's no silver bullet - you'll have to do your own research on how to get around them.

An adblocker can help with reducing traffic from the site, but beware of extensions that change the appearance of the site (eg. darkreader) because they can alter the html/css.

Once you have the pages (urls) that you're interested in, it's easier to inspect them from less/an editor.
The debugger's inspector can help you with finding what's what but finding patterns/urls is much easier in an editor.
Additionally the debugger doesn't always show you the html faithfully - I've experienced some escape sequences being rendered, capitalization changing - so be sure you see the response of the servers in raw format before you write your regexes.

### Core concepts
If you navigate the site normally from the browser, you'll see that each anime is represented with an URL that compromises from an ID (that identifies a series/season of series) and an episode number.
The series identifier is stored in the `id` variable by the script and the episode number in the `ep_no` number.

Each episode has an embedded player that contains the links to the videos to be played.
Your goal is to get these links along with the resolution (quality) of the streams.
The embedded player has a separate URL from the episode page, but you can always get there from the episode page (and in some cases just by knowing the id and the episode number).

### Provider extraction
The `fetch_episode_providers` function (in `providers/provider.sh`) queries the episode embed API and extracts source URLs into `$resp`. Each registered provider's extraction regex is tested against `$resp`. The providers that match are fetched in parallel.

### Searching
The search page is usually easy to find on these websites. The searching method varies.
Some sites will have you post a database query in plaintext, some just use a get request with a single variable.
Just try searching for a few series and see how the URL changes (most of the times the sites use a get request for this purpose).
If the site uses a POST request or a more roundabout way, use the debugger to analyze the traffic.

Once you figured out how searching works, you'll have to replicate it in the `search_anime` function.
The `curl` in this function is responsible for the search request, and the following `sed` regexes mold the response into many lines of `id\ttitle` format.
The reason for this is the `nth` function, see it for more details.
You'll have to change some variables in the process (eg. allanime_base) too.

If you have done everything correctly, you can run `ani-cli`, query your site of choice and select from the responses.
Then ani-cli should fail without a message.
If it fails with `No results found!` you have debugging to do.
Running ani-cli with `sh -x` is a good way to debug.

### Episode selection
Having completed the previous step, the `id` and `title` will contain the selected title and the corresponding id.

Now you'll have to look at the page where all the episodes of the series are listed.
This might be a series overview page (like with allanime) or there might not be such, but the episode pages have links to all episodes.

You'll have to edit the `episodes_list` function that downloads this list of urls.
You need to rewrite the web request and the following regexes to achieve a list of episode numbers separated by newlines and preferably sorted.
Again the `nth` function is used to offer a selection.

If you have done everything correctly, now you can search for a title, get its episodes listed and select an episode.
Then ani-cli should fail with `Episode not released!`

### Getting the player embed
After selecting an episode, the next step is to load its page and extract the embed(s).
In case you can get them without loading the episode page, the provider system calls `fetch_episode_providers()` which queries the embed API, extracts source URLs for each registered provider, and fetches stream links in parallel.

The first request is to get the episode page, then the following commands extract the embed players' links, one at a line with the format `sourcename : url`.
These are listed into `resp`.
From here each provider is extracted using its registered regex and fetched via `provider_fetch_streams()`.
Some sites (like allanime) have these urls not in plaintext but "encrypted". The `process_response` function handles this decryption.

### Extracting the media links

Once you have the embed player, it needs to be parsed for the media link.
This is done in the script with the `get_links` function.

Here first the embed player is first requested and loaded into `episode_link` the media links are extracted.
They need to be printed to the function's stdout in a format of `quality >link`.
The quality string needs to be extracted from the player along with the link and is supposed to be a numeric representation of the resolution.
Sometimes a resolution can't be determined, in this case have the regex match for whatever is in its place.

Each provider's output goes into a separate cache file (`$PROVIDER_CACHE_DIR/<provider_id>`). The provider menu reads these files to determine quality metadata and present the user with a choice. Quality selection then works as before from the full set of links.

## Other functionality
Assuming you completed all the necessary modifications, ani-cli should completely work for you now.
The UI and the history system works as long as you keep the structure of the original code and the format of the responses.

There might be cases that can't be covered by the current structure of ani-cli, but still it works for most sites as I've observed.

## UX Spec

There also exists a UX spec if you want to replicate the ani-cli user experience in a fresh codebase:
![image](.assets/ani-cli-ux-spec.png)
