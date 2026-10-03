#!/usr/bin/env bash
# One entry point for "get the competition inputs into data/", resolving the prompt's reference to a
# download script. This wrapper NEVER contacts DrivenData: the organizer pages may not be fetched
# programmatically (AGENTS.md rule 3, knowledge/03). It only restores the hash-pinned owner mirrors that
# this repository is allowed to read, through the two existing Python restorers.
#
#   bash scripts/download_competition_data.sh              # restore the H31-group set (what the current
#                                                           # screens, caches and checkers expect)
#   bash scripts/download_competition_data.sh --group core  # restore data/manifest.json into data/bridge
#   bash scripts/download_competition_data.sh --verify      # hash-verify an existing restore, fetch nothing
#
# Fetch order inside each restorer (verified by reading the source, 2026-10-03): local refs directory ->
# owner mirror via `gh api` -> raw.githubusercontent.com. In this sandbox only api.github.com completes TLS,
# so the plain-HTTP-free `gh api` path is the one that works; see IR-29-SANDBOX-NET.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"
GROUP="h31"
MODE="restore"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --group) GROUP="${2:?--group needs core, h31 or all}"; shift 2 ;;
    --group=*) GROUP="${1#*=}"; shift ;;
    --verify) MODE="verify"; shift ;;
    -h|--help) sed -n '2,17p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "unknown argument: $1 (see --help)" >&2; exit 2 ;;
  esac
done

case "$GROUP" in core|h31|all) ;; *) echo "--group must be core, h31 or all" >&2; exit 2 ;; esac

cd "$ROOT"
if [[ ! -d data ]]; then mkdir -p data; fi

run() { echo "+ $*"; "$@"; }

if [[ "$MODE" == "verify" ]]; then
  if [[ "$GROUP" == "core" || "$GROUP" == "all" ]]; then run "$PY" scripts/restore_data.py --verify; fi
  if [[ "$GROUP" == "h31" || "$GROUP" == "all" ]]; then run "$PY" scripts/restore_h31_data.py --group all --verify; fi
  echo "(verify mode never downloads; a nonzero exit means a pinned file is missing or hash-wrong)"
else
  if [[ "$GROUP" == "core" ]]; then run "$PY" scripts/restore_data.py; fi
  if [[ "$GROUP" == "h31" ]]; then run "$PY" scripts/restore_h31_data.py --group all; fi
  if [[ "$GROUP" == "all" ]]; then
    run "$PY" scripts/restore_data.py
    run "$PY" scripts/restore_h31_data.py --group all
  fi
fi

TEMPLATE="$("$PY" -c 'import sys; sys.path.insert(0, "src"); from gems29.paths import template_path; print(template_path())')"
if [[ -f "$TEMPLATE" ]]; then
  echo "template resolved for the local checker: ${TEMPLATE#"$ROOT"/}"
else
  echo "WARNING: no submission template found (expected data/bridge/sample_submission.tif or data/sample_submission.tif)" >&2
  exit 1
fi

echo
echo "Next steps (regenerable caches; nothing here talks to the organizer):"
echo "  python scripts/prepare_data.py          # footprint/label/band caches (19 bands)"
echo "  python scripts/build_features.py         # 64-column static block -> data/work/static_ABCD.npy"
echo "  python scripts/build_addons.py             # S/G/E/H27 add-ons -> data/work/addons.npy"
echo "  GEMS_DATA_DIR=\$PWD/data python scripts/check_submission.py docs/downloads/<candidate.tif> --receipt evidence/format_checks/<candidate.json>"
