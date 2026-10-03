# Aborted first launch of the H41 confirmation stage (2026-10-03)

`scripts/run_h41_screen.py --confirm` was started from a shell that exited ~30 s later, which killed the
child before it fitted anything: `cells_confirm.jsonl` is empty (0 cells) and no summary was written. This
directory is retained instead of deleted so that the runner's refuse-to-overwrite guard was not bypassed and
the audit trail shows the attempt. The confirmation was then re-launched as a detached process; its evidence is
`evidence/h41_screen/design_confirm.json` (later timestamp) plus `cells_confirm.jsonl` and
`summary_confirm.json`.

No result is claimed here. `design_confirm.json` in this directory records the clean tree at the time of the
aborted launch (git `5e50c081`) and the same frozen gates, draws and arm plan as the re-run; the only
difference between the two design files is the recorded git revision and the module hashes that go with it.
