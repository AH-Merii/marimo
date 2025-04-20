#!/bin/bash
# Usage:
#   ./connect-ws.sh --url <url> --cookie "<cookie string>" [--verbose] < headers.txt

set -e

URL=""
COOKIE=""
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
  --url)
    URL="$2"
    shift
    ;;
  --cookie)
    COOKIE="$2"
    shift
    ;;
  --verbose)
    VERBOSE=true
    ;;
  *)
    echo "Unknown argument: $1"
    exit 1
    ;;
  esac
  shift
done

# Basic validation
if [[ -z "$URL" ]]; then
  echo "Error: --url is required"
  exit 1
fi

if [[ -z "$COOKIE" ]]; then
  echo "Error: --cookie is required"
  exit 1
fi

log() {
  if $VERBOSE; then
    echo "[LOG] $1"
  fi
}

log "Starting WebSocket connection to: $URL"

# Read headers from stdin
HEADER_ARGS=()
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ -z "$line" ]] && continue
  log "Adding header: $line"
  HEADER_ARGS+=("--header=$line")
done

log "Using cookie: $(echo "$COOKIE" | cut -c1-80)..."
HEADER_ARGS+=("--header=Cookie: $COOKIE")

# Verbose for websocat
if $VERBOSE; then
  HEADER_ARGS+=("-v")
fi

log "Launching websocat..."
websocat "${HEADER_ARGS[@]}" "$URL"
