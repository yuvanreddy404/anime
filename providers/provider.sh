# shellcheck shell=sh
# Provider system for ani-cli
# This file is sourced by the main script and provides the provider framework

# shellcheck disable=SC2034
PROVIDER_LIST=""
PROVIDER_AVAILABLE=""
PROVIDER_CACHED=""
PROVIDER_CACHE_DIR=""
CURRENT_PROVIDER=""

provider_register() {
    id="$1"
    name="$2"
    extract="$3"
    fetch="${4:-default}"
    PROVIDER_LIST="$PROVIDER_LIST $id"
    eval "PROVIDER_NAME_${id}='${name}'"
    eval "PROVIDER_EXTRACT_${id}='${extract}'"
    eval "PROVIDER_FETCH_${id}='${fetch}'"
}

provider_get_name() {
    eval "printf '%s' \"\${PROVIDER_NAME_${1}}\""
}

provider_get_extract() {
    eval "printf '%s' \"\${PROVIDER_EXTRACT_${1}}\""
}

provider_get_fetch() {
    eval "printf '%s' \"\${PROVIDER_FETCH_${1}}\""
}

# shellcheck disable=SC2154,SC1090
provider_load_all() {
    for f in "$PROVIDER_DIR"/*.sh; do
        case "$f" in
            */provider.sh) continue ;;
            *) ;;
        esac
        [ -f "$f" ] && . "$f"
    done
}

debug_log() {
    [ "${debug_mode:-0}" = "1" ] && printf "\033[1;33m[DEBUG]\033[0m %s\n" "$*" >&2
}

# Decode AllAnime hex-encoded slug (e.g. "--636c6f636b" -> "/clock")
# Strips leading "--", splits into hex pairs, converts each to a character
hex_to_string() {
    _hex="$1"
    _hex="${_hex#--}"
    [ -z "$_hex" ] && return 1
    printf '%s' "$_hex" | sed 's/../&\n/g' | sed '
        s/^79$/A/g;s/^7a$/B/g;s/^7b$/C/g;s/^7c$/D/g;s/^7d$/E/g;s/^7e$/F/g;s/^7f$/G/g
        s/^70$/H/g;s/^71$/I/g;s/^72$/J/g;s/^73$/K/g;s/^74$/L/g;s/^75$/M/g;s/^76$/N/g;s/^77$/O/g
        s/^68$/P/g;s/^69$/Q/g;s/^6a$/R/g;s/^6b$/S/g;s/^6c$/T/g;s/^6d$/U/g;s/^6e$/V/g;s/^6f$/W/g
        s/^60$/X/g;s/^61$/Y/g;s/^62$/Z/g
        s/^59$/a/g;s/^5a$/b/g;s/^5b$/c/g;s/^5c$/d/g;s/^5d$/e/g;s/^5e$/f/g;s/^5f$/g/g
        s/^50$/h/g;s/^51$/i/g;s/^52$/j/g;s/^53$/k/g;s/^54$/l/g;s/^55$/m/g;s/^56$/n/g;s/^57$/o/g
        s/^48$/p/g;s/^49$/q/g;s/^4a$/r/g;s/^4b$/s/g;s/^4c$/t/g;s/^4d$/u/g;s/^4e$/v/g;s/^4f$/w/g
        s/^40$/x/g;s/^41$/y/g;s/^42$/z/g
        s/^08$/0/g;s/^09$/1/g;s/^0a$/2/g;s/^0b$/3/g;s/^0c$/4/g;s/^0d$/5/g;s/^0e$/6/g;s/^0f$/7/g
        s/^00$/8/g;s/^01$/9/g
        s/^15$/-/g;s/^16$/./g;s/^67$/_/g;s/^46$/~/g;s/^02$/:/g
        s/^17$/\//g;s/^07$/?/g;s/^1b$/#/g;s/^63$/\[/g;s/^65$/\]/g;s/^78$/@/g
        s/^19$/!/g;s/^1c$/$/g;s/^1e$/\&/g;s/^10$/\(/g;s/^11$/\)/g
        s/^12$/*/g;s/^13$/+/g;s/^14$/,/g;s/^03$/;/g;s/^05$/=/g;s/^1d$/%/g
    ' | tr -d '\n' | sed 's|/clock|/clock.json|'
}

provider_extract_url() {
    extract_regex="$(provider_get_extract "$1")"
    [ -z "$extract_regex" ] && return 1
    url=$(printf "%s" "$resp" | sed -n "$extract_regex" | head -1 | cut -d':' -f2-)
    [ -n "$url" ]
}

# shellcheck disable=SC2154
provider_fetch_streams() {
    fetch_type="$(provider_get_fetch "$1")"
    # shellcheck disable=SC2312
    url=$(printf "%s" "$resp" | sed -n "$(provider_get_extract "$1")" | head -1 | cut -d':' -f2-)
    [ -z "$url" ] && return 1
    # Decode hex-encoded slug to actual path (e.g. "--636c6f636b" -> "/clock")
    decoded="$(hex_to_string "$url")" || decoded="$url"
    # shellcheck disable=SC2034
    provider_name="$(provider_get_name "$1")"
    if [ "$fetch_type" = "filemoon" ]; then
        get_filemoon_links "$decoded"
    else
        get_links "$decoded"
    fi
}

# shellcheck disable=SC2154
provider_get_links() {
    sort -g -r -s < "$PROVIDER_CACHE_DIR/$1" 2>/dev/null
}

# shellcheck disable=SC2154,SC2016
fetch_episode_providers() {
    episode_embed_gql='query ($showId: String!, $translationType: VaildTranslationTypeEnumType!, $episodeString: String!) { episode( showId: $showId translationType: $translationType episodeString: $episodeString ) { episodeString sourceUrls }}'

    query_hash="d405d0edd690624b66baba3068e0edc3ac90f1597d898a1ec8db4e5c43c00fec"
    query_vars="{\"showId\":\"$id\",\"translationType\":\"$mode\",\"episodeString\":\"$ep_no\"}"
    query_ext="{\"persistedQuery\":{\"version\":1,\"sha256Hash\":\"$query_hash\"}}"

    api_resp="$(curl -e "$allanime_refr" -sG -A "$agent" -H "Origin: ${allanime_refr}" "${allanime_api}/api" --data-urlencode "variables=${query_vars}" --data-urlencode "extensions=${query_ext}")"

    if [ -z "$api_resp" ] || ! printf "%s" "$api_resp" | grep -q "tobeparsed"; then
        api_resp="$(curl -e "$allanime_refr" -s -H "Content-Type: application/json" -X POST "${allanime_api}/api" --data "{\"variables\":{\"showId\":\"$id\",\"translationType\":\"$mode\",\"episodeString\":\"$ep_no\"},\"query\":\"$episode_embed_gql\"}" -A "$agent")"
    fi

    resp="$(process_response "$api_resp" | tr '{}' '\n' | sed 's|\\u002F|\/|g;s|\\||g' | sed -nE 's|.*sourceUrl":"([^"]*)".*sourceName":"([^"]*)".*|\2 :\1|p')"

    PROVIDER_AVAILABLE=""
    PROVIDER_CACHE_DIR="$(mktemp -d)"

    for p in $PROVIDER_LIST; do
        if provider_extract_url "$p"; then
            PROVIDER_AVAILABLE="$PROVIDER_AVAILABLE $p"
        fi
    done

    if [ -z "$PROVIDER_AVAILABLE" ]; then
        PROVIDER_CACHED="1"
        printf "\033[1;33mNo streaming providers available for this episode.\033[0m\n" >&2
        return 1
    fi

    debug_log "Fetching providers in parallel..."
    for p in $PROVIDER_AVAILABLE; do
        (
            # shellcheck disable=SC2034
            cache_dir="$PROVIDER_CACHE_DIR"
            # shellcheck disable=SC2312
            debug_log "$(provider_get_name "$p")..."
            provider_fetch_streams "$p" >"$PROVIDER_CACHE_DIR/$p" 2>/dev/null
            # shellcheck disable=SC2312
            debug_log "$(provider_get_name "$p")...Success"
        ) &
    done
    wait

    # Propagate m3u8 referrer from subshell (used by download function)
    if [ -f "$PROVIDER_CACHE_DIR/m3u8_refr" ]; then
        # shellcheck disable=SC2034
        m3u8_refr="$(sed 's/^m3u8_refr >//' "$PROVIDER_CACHE_DIR/m3u8_refr")"
    fi

    PROVIDER_CACHED="1"
}

provider_get_display() {
    p="$1"
    name="$(provider_get_name "$p")"
    links="$(provider_get_links "$p")"
    highest=$(printf "%s" "$links" | grep -E '^[0-9]+' | sort -rn | head -1 | cut -d'>' -f1)
    [ -z "$highest" ] && highest="?"
    fmt="HLS"
    [ "$(provider_get_fetch "$p")" = "default" ] && fmt="Auto" || true
    printf "%-12s %5s  %s" "$name" "${highest}p" "$fmt"
}

# shellcheck disable=SC2154
select_provider() {
    [ "$PROVIDER_CACHED" != "1" ] && fetch_episode_providers

    if [ -z "$PROVIDER_AVAILABLE" ]; then
        printf "\033[1;33mNo streaming providers available.\033[0m\n" >&2
        return 1
    fi

    provider_menu=""
    provider_menu_file="$(mktemp)"
    idx=1
    for p in $PROVIDER_AVAILABLE; do
        display="$(provider_get_display "$p")"
        printf "%s\t%s\t%s\n" "$idx" "$p" "$display" >> "$provider_menu_file"
        provider_menu="${provider_menu}${idx}	${p}	${display}
"
        idx=$((idx + 1))
    done

    printf "\n\033[1;36mAvailable providers:\033[0m\n"

    if command -v fzf >/dev/null && [ "$use_external_menu" = "0" ]; then
        selection="$(printf "%s" "$provider_menu" | nth "Select provider: ")"
        CURRENT_PROVIDER="$(printf "%s" "$selection" | cut -f1)"
    else
        printf "%s\n" "------------------------------------------------"
        printf "%-3s %-12s %5s  %s\n" "#" "Name" "Qual" "Type"
        printf "%s\n" "------------------------------------------------"
        while IFS='	' read -r idx id display_text; do
            printf "%-3s %s\n" "$idx" "$display_text"
        done < "$provider_menu_file"
        printf "%s\n" "------------------------------------------------"
        provider_names="$(cut -f3 < "$provider_menu_file")"
        provider_count=$(printf "%s" "$provider_names" | wc -l)
        PS3="Select provider (1-$provider_count): "
        # Use read instead of select for POSIX compliance
        while true; do
            printf "%s" "$PS3"
            read -r selected_idx
            case "$selected_idx" in
                ''|*[!0-9]*) continue ;;
                *) selected_name=$(printf "%s\n" "$provider_names" | sed -n "${selected_idx}p")
                   [ -n "$selected_name" ] && break ;;
            esac
        done
        CURRENT_PROVIDER="$(while IFS='	' read -r idx id display_text; do
            [ "$display_text" = "$selected_name" ] && printf "%s" "$id" && break
        done < "$provider_menu_file")"
    fi

    rm -f "$provider_menu_file"
    [ -z "$CURRENT_PROVIDER" ] && die "No provider selected!"
    printf "\033[1;32mSelected: %s\033[0m\n" "$(provider_get_name "$CURRENT_PROVIDER")" || true
}

# shellcheck disable=SC2154
resolve_provider_quality() {
    links="$(provider_get_links "$CURRENT_PROVIDER")"
    [ -z "$links" ] && return 1
    select_quality "$quality"
    [ -n "$episode" ]
}
