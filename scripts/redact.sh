#!/usr/bin/env bash
# Thin shim -> scripts/redact.py. Reads stdin (or a file arg), writes redacted stdout.
# Accepts (ignores) -s/--stream for backward compatibility.
here="$(dirname "${BASH_SOURCE[0]}")"
args=()
for a in "$@"; do case "$a" in -s|--stream) ;; *) args+=("$a");; esac; done
exec python3 "$here/redact.py" "${args[@]}"
