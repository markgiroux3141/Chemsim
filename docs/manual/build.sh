#!/usr/bin/env bash
# Build the manual. Requires pandoc and xelatex (MiKTeX) on PATH.
#
#     bash docs/manual/build.sh              # figures are NOT regenerated
#     bash docs/manual/build.sh --figures    # regenerate them first (~2 min)
#
# Output: docs/manual/chemsim-manual.pdf
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

if [[ "${1:-}" == "--figures" ]]; then
  echo "==> regenerating figures"
  PYTHONIOENCODING=utf-8 python make_figures.py
fi

CHAPTERS=$(ls chapters/*.md | sort)
echo "==> chapters:"
for c in $CHAPTERS; do echo "      $c"; done

echo "==> pandoc"
pandoc metadata.yaml $CHAPTERS \
  -o chemsim-manual.pdf \
  --pdf-engine=xelatex \
  --top-level-division=chapter \
  --toc --toc-depth=2 \
  --number-sections \
  --lua-filter=callouts.lua \
  -H preamble.tex \
  --resource-path=.

echo "==> wrote $HERE/chemsim-manual.pdf"
