#!/bin/bash
# Pretty-print or emit raw Cookie header from stdin
# Usage:
#   cat cookie.txt | ./cookie-pretty.sh [--verbose] [--raw] [--add "key=value"]

set -e

VERBOSE=false
RAW=false
ADDITIONS=()

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
  --verbose)
    VERBOSE=true
    ;;
  --raw)
    RAW=true
    ;;
  --add)
    ADDITIONS+=("$2")
    shift
    ;;
  *)
    echo "Unknown argument: $1"
    exit 1
    ;;
  esac
  shift
done

log() {
  if $VERBOSE; then
    echo "[LOG] $1"
  fi
}

log "Reading cookie header from stdin..."

# Convert raw Cookie header to JSON
COOKIE_JSON=$(
  tr ';' '\n' |
    sed 's/^[[:space:]]*//' |
    awk -F= 'NF >= 2 {
    key = $1
    $1 = ""
    sub(/^=/, "", $0)
    gsub(/^ +| +$/, "", $0)
    gsub(/"/, "\\\"", $0)
    printf "\"%s\": \"%s\",\n", key, $0
  }' |
    sed '$s/,$//' |
    awk 'BEGIN { print "{" } { print } END { print "}" }'
)

log "Parsed JSON from Cookie header:"
$VERBOSE && echo "$COOKIE_JSON"

# Apply additions if any
for kv in "${ADDITIONS[@]}"; do
  KEY="${kv%%=*}"
  VALUE="${kv#*=}"
  log "Adding/updating: $KEY = $VALUE"
  COOKIE_JSON=$(echo "$COOKIE_JSON" | jq --arg k "$KEY" --arg v "$VALUE" '.[$k] = $v')
done

log "Final cookie data (JSON):"
$VERBOSE && echo "$COOKIE_JSON"

# Output: raw or pretty JSON
if $RAW; then
  echo "$COOKIE_JSON" | jq -r 'to_entries | map("\(.key)=\(.value)") | join("; ")'
else
  echo "$COOKIE_JSON" | jq .
fi
