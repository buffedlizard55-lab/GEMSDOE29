# 36 — Session-6 review intake (2026-10-03): repo audit, prompt disposition, one register defect

This session re-read the README charter + Core Values (`Maximize P(Win)`, `Own the Outcome`), the
newest dated knowledge files, and the registers, then dispositioned the standing brief item by item.
No experiment ran (no data in this checkout beyond the restored template — §3); no slot was touched.

## 1. Repo audit: what was verified working in THIS checkout

- **One-click TIF + note:** the landing page hero and the executive summary both lead with the
  recommended zero-outside download, paste-ready DrivenData note and content id
  (`docs/index.html`, `docs/executive-summary.html`, `registry/submissions.json`). Obvious on arrival:
  yes. Slot-approved: nothing — every card says `not slot-cleared · do not submit`, pinned by
  `tests/test_project_integrity.py`.
- **Format truth, re-verified here:** the 1.6 MB owner-mirror template restored via `gh api` and
  matched its pin (sha256 `2176d08e…`, 1,599,597 bytes). `scripts/check_submission.py` → exit 0,
  `ok_to_upload=true` for the lead file (33,739 dots, 5,167,373-px footprint, EPSG:32611, float32);
  `scripts/verify_downloads.py` → **7/7** registered downloads pass (receipt
  `evidence/format_checks/registered_downloads_recheck.json`, regenerated this session).
- **`[0, 1]` rejection, reproduced exactly:** strict whole-array `((a>=0)&(a<=1)).all()` is True for
  the `-zeros.tif` and False for the `-nan.tif` (rasterio 1.4.4) — the zero-outside recommendation
  (AGENTS.md rule 9) is the fix; the portal validator itself stays unverified.
- **Unit/site checks:** `pytest` no-data subset 39 passed (35 pre-existing + 4 new session-6 pins); `build_site.py --check` current;
  `check_site.py` OK (run again after this session's edits — §5).

## 2. Prompt disposition (where each ask landed)

| standing-brief ask | disposition |
|---|---|
| Multiscale worming across mag/grav as feature/filter | Already implemented in 4 formulations (H29/H31/H31b/H40), all failed frozen gates — closed with reasons, `knowledge/34` §4. No fifth retry. |
| Why D2.8/0.2600 won; can we beat 0.26 / 0.3195 | PhD-level analysis in `knowledge/34`: dotting = redundancy removal (73 % credit at 36 % budget); D2.8 is its family's measured ceiling; +0.06 gap needs new habitat mass, and no validated estimate of it exists. |
| 3–5 NEW hypotheses, ranked, with layers/signature/why-off-catalogue/difference + obtainability | v5 slate in `knowledge/35`: H50 range-front Smf (rank 1), H49 alteration corridors, H51 cross-family agreement, H48 vent/paleo alignments. Novelty grep-verified; H48's two zips named with pins + owner-side-fetch requirement. |
| Validate the top candidate on the holdout before any slot | Prereg-shaped validation plan for H50 on fresh draws 36/37 in `knowledge/35` §"Validation policy" — queued, not run (§3). No slot touched. |
| Easy-download submission TIF + executive-summary guide | Present and re-verified (§1). No change needed. |
| Unique name + short comment per submission | Present per download (`registry/submissions.json` → `optional_comment`). No change needed. |
| Download + organize competition data | Template restored + verified here; full restore documented (`download_competition_data.sh --group all` → `prepare_data.py` → feature builders). Organizer login still required for authenticated bytes — owner-side. |
| Put the prompt in the README; re-read every session | Session-6 intake section added to `README.md` (this brief restates the standing brief; the new deliverables are `knowledge/34`/`35`/`36`). Verbatim blocks untouched (pinned by test). |
| Three passes, then PR + merge, then remaining work | §5 + `README.md` session-6 section + this file's §4. |

## 3. Why the H50 validation did not run here (limitation, not deferral)

`data/` in this checkout holds only `manifest.json` + the restored template: the 419 MB feature stack,
labels, external layers and prepared caches are gitignored and were never restored here (session 5's
22/22 restore lived in that session's checkout). A frozen H50 screen additionally needs scikit-learn,
an H50 implementation + preregistration, and ~1,500 s on a bigger box. The honest order is therefore:
preregister → implement → restore data on the compute checkout → screen 36/37 → confirm 38/39. The
gate rule stands unchanged: no slot until a candidate beats the comparable holdout best (0.14479) and
passes fresh confirmation plus the exact-file audit.

## 4. Remaining work for the next session (priority order)

1. **Proxy-calibration study** (`knowledge/32` option 3, `knowledge/34` §6.1): score the 7 files in
   `docs/downloads/` on the primary proxy vs their reported-score ordering. No slot, no new data,
   answers whether the promotion rule can ever pass. Needs the full data restore (§3).
2. **H50 preregistration + screen** (`knowledge/35`): front extraction, Smf, mask, synthetic tests,
   frozen 5-arm design on draws 36/37. Confirm `registry/draw_ledger.json` still shows 36 free.
3. **Owner decision on the SGMC veto** (`IR-29-PROXY-VETO-PATTERN`): keep / demote-to-flag /
   calibrate-first. Until decided, H43/H41/H51-class results cannot promote no matter the primary.
4. **Owner-side fetches (all free, official, blocked here):** GDR 1391 paleo + Q-volcanics zips (pins
   in `data/manifest.json`), ComCat (H45), NWIS (H44), GeoDAWN LiDAR (H46), state-map polygons (H47).
5. **Fold-geometry robustness swap** (`knowledge/29` §4.3): re-partition quadrants to test whether any
   verdict depends on the shared fold geometry. Still the cheapest conclusion-level check.

Standing limitations (re-affirmed from `knowledge/29` §5): no organizer ground truth; all scores
unverified claims; owner-mirror bytes unauthenticated; this box is CPU-only with no data restore.

## 5. Three-pass record for session 6

- **Pass 1 (implement + verify):** wrote `knowledge/34` (D2.8/0.3195 analysis), `knowledge/35` (v5
  slate + H50 validation plan), `knowledge/36` (this record); fixed the stale H43 registry status
  (`IR-29-H43-REGISTRY-STALE`); registered the v5 slate (`registry/hypotheses_v5_2026-10-03.json`);
  appended the status-feed event; added the README intake section; restored + hash-verified the
  template; re-ran `check_submission.py`, `verify_downloads.py` (7/7), the no-data pytest subset,
  `build_site.py --check` and `check_site.py` — all green. Pass 3 widened pytest from the
  no-data subset to the full suite (179 passed, 2 env-skipped) after installing the missing
  scikit-learn/pandas wheels, and added a `ruff` run (clean).
- **Pass 2 (bugs, edge cases, wrong assumptions):** corrected the initial v5 draft's two collisions
  (2 m probes already screened by H29 B2; tilt already in the static block) by grep-backed exclusion;
  kept the frozen `hypotheses.json` id list/order/ranks intact (pinned by
  `test_hypothesis_slate_has_frozen_ranked_statuses`) by putting v5 in its own register file;
  preserved every check_site-required `status_feed` substring and the README verbatim blocks.
- **Pass 3 (recheck vs the brief):** one-click TIF + note ✓, submission guide ✓, `[0,1]` fix ✓,
  worming disposition ✓, D2.8/0.3195 analysis ✓, 4 ranked hypotheses + obtainability ✓, H50 validation
  plan with no-slot rule ✓, prompt-in-README ✓, line-by-line links ✓ (all claims cite a repo path or a
  `registry/sources.json` id), irregularities flagged ✓, PR + merge next.
