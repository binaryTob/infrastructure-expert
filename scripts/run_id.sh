#!/usr/bin/env bash
# scripts/run_id.sh — derive a stable per-run id + reportes dir.
#
# Usage:
#   scripts/run_id.sh dir          # print and create reportes/<run-id>/, reuse if exists
#   scripts/run_id.sh id           # print run id only
#
# Run id format: <YYYYMMDD-HHMM>-<hostslug>. Reused for the lifetime of the run
# via the EVIDENCE_RUN_ID env var (set by the calling agent session).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

mode="${1:-dir}"
rid="${EVIDENCE_RUN_ID:-}"
if [[ -z "$rid" && -f "$ROOT/.run_id" ]]; then
  rid="$(cat "$ROOT/.run_id" 2>/dev/null)"
fi
if [[ -z "$rid" ]]; then
  host="$(python3 - "$ROOT/config/target.json" ssh.host 2>/dev/null <<'PY'
import json,sys,pathlib
try: d=json.loads(pathlib.Path(sys.argv[1]).read_text())
except Exception: sys.exit(0)
h=d.get("ssh",{}).get("host","host")
print(h)
PY
)"
  host="${host:-host}"
  slug="$(printf '%s' "$host" | tr -c 'A-Za-z0-9' '-' | tr -s '-' '-')"
  rid="$(date -u +%Y%m%d-%H%M)-${slug}"
fi

case "$mode" in
  id) printf '%s\n' "$rid" ;;
  dir) dir="$ROOT/reportes/$rid"; mkdir -p "$dir"; printf '%s\n' "$dir" ;;
  *) echo "usage: $0 dir|id" >&2; exit 4 ;;
esac
