# `docs/manual` — the chemsim manual

A self-contained, 163-page explanation of this project for a reader who knows
physics and has never done any chemistry. It starts from what a molecule is and
works up to the stiff four-phase ODE, the Jacobian bound, and the coverage
audit.

**Output: [`chemsim-manual.pdf`](chemsim-manual.pdf)**

## Build

```bash
bash docs/manual/build.sh              # pandoc + xelatex, ~40 s
bash docs/manual/build.sh --figures    # regenerate the figures first (~2 min)
```

Needs `pandoc` and a LaTeX distribution with `xelatex`. The fonts are Cambria /
Calibri / Consolas / Cambria Math (Windows), set in `metadata.yaml`; on another
platform, change those four lines.

Only packages that ship with a normal MiKTeX install are used — `framed`,
`tikz`, `titlesec`, `fancyhdr`, `microtype` — because an on-the-fly package
download hangs a non-interactive shell.

⚠ **Do not add `mathtools` to `preamble.tex`.** Pandoc injects `-H` content
*after* its own `\usepackage{unicode-math}`, and mathtools loaded in that order
silently destroys `\underbrace` and `\overbrace`: they render as `|■{Z■}` tofu,
with **no "Missing character" warning anywhere in the log**. It shipped that way
in the first build. If you need a mathtools feature, it has to go in via a
pandoc template change, not via `-H`.

## Layout

| | |
|---|---|
| `chapters/*.md` | the source, one file per chapter, built in filename order |
| `figures/*.pdf` | generated; do not hand-edit |
| `make_figures.py` | the generator. **Prints `ENGINE` or `DRAWN` per figure.** |
| `preamble.tex` | page setup, the four callout environments, heading styles |
| `callouts.lua` | pandoc filter mapping `::: {.keypoint}` → the LaTeX environment |
| `metadata.yaml` | title, fonts, geometry |
| `build.sh` | the one command |

## ⚠ Half the figures are ENGINE OUTPUT, and that is the point

Wherever a figure *could* be computed by the real simulator, it is —
`make_figures.py` imports `chemsim` and runs it. The vapour-pressure curves, the
ethanol/water T-x-y diagram, the boiling plateau, the benzoic-acid solubility
curve, the oxygen-in-four-solvents chart and the lime-kiln equilibrium are all
outputs of `src/chemsim`, not illustrations of it.

Two of them double as assertions, and the generator prints both:

```
[ENGINE] boilplateau      (plateau 351.46 K; literature 351.4 K)
[ENGINE] solubility       (298 K: ideal 1347 g/L, UNIFAC 3.24 g/L, measured 3.44)
```

If a change to the engine moves those, the manual's figures move with it and the
printed comparison says so. The rest are analytic illustrations of a concept (a
Boltzmann tail, a double tangent) and print `DRAWN`.

## ⚠ The numbers in Part V go stale, and they go stale silently

Chapters 29–31 quote the coverage and playability headlines. Those come from
`data/catalog/COVERAGE_REPORT.md` and `data/catalog/PLAYABLE.md`, which are
**generated**, and this manual was written against the 2026-08-28 regeneration:

| | |
|---|---:|
| compounds / routes / steps | 1583 / 173 / 377 |
| distinct reaction classes | 240 |
| templates, and classes they cover | 47 → 59 |
| species-ready / template-ready / **BOTH** | 85 / 46 / **38** |
| playable from natural materials | 21 |

⚠ **`README.md` in the repository root is one regeneration behind the report**
(it says 41 / 31 and 51 of 229 classes) — the manual uses the generated files,
not the prose. Re-check both against the current report before quoting anything
from Chapter 29, and note that `data/catalog/README.md` carries a stale
"36 runnable, 12 playable" line from before the C-series.

## ⚠ Every figure has to be LOOKED AT, not just generated

Six figures were wrong in ways no build warning could report, and all six were
found only by rasterising a page and reading it:

| figure | what was wrong |
|---|---|
| `selectivity` | `argmin(abs(k1-k2))` marked the crossing at the **left edge** — on a log-spread quantity the smallest absolute difference is not the crossing. Now found by sign change; it moved from 350 K to the correct 522 K. |
| `boltzmann` | drawn on a linear axis, where $e^{-50/2.5}$ is flat zero and the whole point of the figure is invisible. Now log. |
| `competition` | legend on top of the tallest bar |
| `standardstate` | value label above the axes |
| `titration` | first annotation off the bottom-left corner |
| `detailed_balance` | "products" label lying on the curve |

`pdftoppm -png -r 95 -f N -l N chemsim-manual.pdf out` is the only review tool
that works here (no ghostscript, so ImageMagick cannot open a PDF).

## Where each chapter came from

The manual is largely a reorganisation of the project's own record. If a claim
in it looks surprising, the primary source is almost always one of:

- the module docstrings in `src/chemsim` — they carry the arguments, not just
  the descriptions;
- `MILESTONES.md`, which records every measurement and every refusal;
- the generated reports under `data/catalog/`;
- the scripts in `validation/`, each of which answers one question.
