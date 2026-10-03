# H52 screen — partial run, killed by memory pressure (2026-10-03)

This directory holds the **partial** output of the first `scripts/run_wormfilter_screen.py` run: 5 of the
8 cells completed (35 of 56 rows) before the process died from memory pressure on a 3 GB sandbox (the
base and worm-extended prediction matrices were both held for every cell). No `summary.json` was
written, so **no gate was evaluated and no verdict exists** for these rows.

The rows are kept because they are the honest record of what ran, and because the four cells they cover
reproduced the stored H34 controls exactly (see the C0/C1 columns). The stage was re-run from scratch
after `run_cells` was changed to free `cell.Xtr`/`cell.Xq` before building the extended matrices; the
authoritative output is `evidence/wormfilter_screen/`.

Nothing here is slot evidence, and no weekly slot was used.
