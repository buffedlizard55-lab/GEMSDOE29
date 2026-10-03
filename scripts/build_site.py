#!/usr/bin/env python3
"""Render GitHub Pages from hash-pinned registries and experiment evidence."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def J(p):
    return json.loads((ROOT / p).read_text())


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


CSS = """
:root{--bg:#0f1419;--card:#171e26;--tx:#e6edf3;--mut:#8b98a5;--acc:#4aa3df;--ok:#3fb950;--warn:#d29922;--bad:#f85149;--bd:#2d3640}
@media(prefers-color-scheme:light){:root{--bg:#f6f8fa;--card:#fff;--tx:#1f2328;--mut:#59636e;--bd:#d0d7de;--acc:#0969da;--ok:#1a7f37;--warn:#9a6700;--bad:#cf222e}}
*{box-sizing:border-box}body{margin:0;font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--tx)}
main{max-width:1060px;margin:0 auto;padding:16px}nav{display:flex;gap:14px;flex-wrap:wrap;padding:10px 0;border-bottom:1px solid var(--bd);margin-bottom:18px}
nav a{color:var(--acc);text-decoration:none;font-weight:600}h1{font-size:26px;margin:.2em 0}h2{font-size:20px;margin-top:1.4em;border-bottom:1px solid var(--bd);padding-bottom:6px}h3{font-size:16px;margin-top:1.2em}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:16px;margin:14px 0}
.dl{display:inline-block;background:var(--acc);color:#fff!important;font-size:18px;font-weight:700;padding:14px 22px;border-radius:10px;text-decoration:none}
.dl:hover{filter:brightness(1.1)}table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{border:1px solid var(--bd);padding:6px 9px;text-align:left;vertical-align:top}th{background:var(--card)}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:700}
.b-ok{background:rgba(63,185,80,.15);color:var(--ok)}.b-warn{background:rgba(210,153,34,.15);color:var(--warn)}.b-bad{background:rgba(248,81,73,.15);color:var(--bad)}
code,pre{background:rgba(127,127,127,.12);border-radius:6px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px}
pre{padding:10px;overflow:auto}code{padding:1px 5px}a{color:var(--acc)}
.mut{color:var(--mut);font-size:13px}.num{font-variant-numeric:tabular-nums}footer{margin:34px 0;color:var(--mut);font-size:12.5px}
"""


def nav_for(root: bool) -> str:
    if root:
        home, pref = "index.html", "docs/"
    else:
        home, pref = "../index.html", ""
    links = [(home, "Home"), (pref + "executive-summary.html", "Executive summary &amp; submission guide"),
             (pref + "research.html", "Research &amp; method"), (pref + "sources.html", "Sources, scores &amp; flags")]
    return "<nav>" + "".join(f'<a href="{h}">{txt}</a>' for h, txt in links) + "</nav>"


def page(title, body, root: bool = False):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body><main>
{nav_for(root)}
<h1>{esc(title)}</h1>
{body}
<footer>GEMSDOE29 · figures are rendered from the repo's JSON registries/evidence ·
competition: DrivenData #306 DOE GEMS · owner-reported scores are labelled and are not organizer receipts.</footer>
</main></body></html>"""


def badge(text, kind):
    return f'<span class="badge b-{kind}">{esc(text)}</span>'


def status_kind(s):
    s = s.lower()
    if "not passed" in s or "fail" in s or "blocked" in s or "do not" in s or "refuted" in s:
        return "bad"
    if "gate passed" in s or "slot-candidate" in s or "ok" == s:
        return "ok"
    if "research artifact" in s or "unverified" in s or "open" in s or "medium" in s or "info" in s:
        return "warn"
    if "high" in s or "critical" in s:
        return "bad"
    if "fixed" in s or "read" in s or "sibling-verified" in s:
        return "ok"
    return "warn"


def fmt_px(n):
    return f"{n:,}"


def main() -> None:
    manifest = J("data/manifest.json")
    live = J("registry/live_scores.json")
    srcs = J("registry/sources.json")
    source_by_key = {item["key"]: item for item in srcs["sources"]}
    problem_facts = source_by_key["dd_problem"]["facts"]
    home_facts = source_by_key["dd_home"]["facts"]
    rules_facts = source_by_key["rules_pdf"]["facts"]
    leaderboard_key = next(k for k in live if k.startswith("leaderboard_public_"))
    leaderboard = live[leaderboard_key]
    leader = min(leaderboard, key=lambda row: row["rank"])
    leaderboard_source = source_by_key["dd_leaderboard"]
    group_scores = live["group_submissions"]
    ref_score_row = next(row for row in group_scores if row["project"] == "GEMSDOE25")
    d15_score_row = next(row for row in group_scores if row["project"] == "GEMSDOE24")
    parent_score_row = next(row for row in group_scores if row["project"] == "19GEMSDOE")
    reported_ref_score = float(ref_score_row["score"])
    ref_rank_rows = [row for row in leaderboard if row["public_dti"] == reported_ref_score]
    reported_ref_rank = min((row["rank"] for row in ref_rank_rows), default=None)
    irr = J("registry/irregularities.json")
    hyp = J("registry/hypotheses_next.json")
    gate = J("evidence/h29_gate.json") if (ROOT / "evidence/h29_gate.json").exists() else {}
    hold = J("evidence/h29_holdout.json") if (ROOT / "evidence/h29_holdout.json").exists() else {}
    worm = J("evidence/worming_receipt.json") if (ROOT / "evidence/worming_receipt.json").exists() else {}
    ledger_path = ROOT / "registry/artifact_ledger.json"
    ledger = J("registry/artifact_ledger.json") if ledger_path.exists() else {"artifacts": {}}
    arts = ledger.get("artifacts", {})
    wr = arts.get("WORMRANK", {})
    files_dir = ROOT / "docs" / "downloads"

    def fmeta(stem, suffix="-nan.tif"):
        p = files_dir / f"{stem}{suffix}"
        receipt_path = files_dir / f"checks-{stem}.json"
        if not p.is_file() or not receipt_path.is_file():
            return None
        receipt = json.loads(receipt_path.read_text())
        recorded = receipt.get("files", {}).get(p.name)
        if not isinstance(recorded, dict) or not recorded.get("sha256"):
            return None
        # Use the build receipt as the site metadata source, but refuse to link a file that has
        # drifted from that immutable checksum. The independent verifier records format checks.
        import hashlib
        h = hashlib.sha256()
        with p.open("rb") as f:
            while chunk := f.read(1 << 20):
                h.update(chunk)
        if h.hexdigest() != recorded["sha256"]:
            return None
        return {"name": p.name, "bytes": recorded["bytes"], "sha256": recorded["sha256"],
                "local_format_verified": receipt.get("local_format_verified") is True,
                "grid": receipt.get("grid", {}), "format": receipt.get("format", {})}

    m_nan = fmeta(wr.get("stem", ""), "-nan.tif")
    m_zip = fmeta(wr.get("stem", ""), "-nan.zip")
    m_zero = fmeta(wr.get("stem", ""), "-zeros.tif")
    ref_art = arts.get("REFD28", {})
    m_ref = fmeta(ref_art.get("stem", ""), "-nan.tif")
    gate_pass = (gate.get("A2") or {}).get("PASS") is True
    gate_txt = ("FROZEN A2 GATE PASSED on catalogue proxy — eligible for owner review only; not live-score evidence"
                if gate_pass else
                "FROZEN A2 GATE NOT PASSED on catalogue proxy — research artifact only; no weekly slot is recommended")
    gate_kind = "ok" if gate_pass else "bad"
    local_format_verified = bool(m_nan and m_nan["local_format_verified"])
    download_heading = ("Locally format-verified GeoTIFF" if local_format_verified else
                        "GeoTIFF — local format checks absent or failed")
    artifact_grid = m_nan.get("grid", {}) if m_nan else {}
    artifact_format = m_nan.get("format", {}) if m_nan else {}
    pixel_size = artifact_grid.get("pixel_size_m", [])
    if len(pixel_size) == 2:
        resolution_text = f"{pixel_size[0]:g}×{pixel_size[1]:g} m"
    else:
        resolution_text = "resolution not recorded"
    grid_text = (f"{esc(artifact_grid.get('crs', 'CRS not recorded'))} · "
                 f"{fmt_px(artifact_grid.get('width', 0))}×{fmt_px(artifact_grid.get('height', 0))} · "
                 f"{esc(resolution_text)}")
    in_range = artifact_format.get("inside_value_range", [])
    range_text = (f"[{in_range[0]:g},{in_range[1]:g}]" if len(in_range) == 2 else "declared range unknown")
    outside_text = esc(artifact_format.get("outside", "outside convention not recorded"))
    band_text = (f"{artifact_format.get('bands')}-band {esc(artifact_format.get('dtype', 'unknown'))}"
                 if artifact_format.get("bands") is not None else "band format not recorded")
    download_format_detail = (
        f"finite {range_text} values inside the pinned template footprint, {outside_text} outside."
        if local_format_verified else
        "format acceptance is not currently established; review the linked receipt before use."
    )
    format_status_text = ("passed local format checks" if local_format_verified else
                          "does not currently have a passing local format receipt")
    official_metric = problem_facts["metric"]
    official_format = problem_facts["submission_format"]
    support_m = float(official_metric["support_distance_m"])
    fp_weight = float(official_metric["false_positive_weight"])
    fn_weight = float(official_metric["false_negative_weight"])
    ref_spacing_px = float(ref_score_row.get("spacing_px", ref_art.get("spacing_px", 0.0)))
    d15_spacing_px = float(d15_score_row.get("spacing_px", 0.0))
    grid_for_spacing = (m_ref or m_nan or {}).get("grid", {})
    spacing_resolution = grid_for_spacing.get("pixel_size_m", [None])[0]
    spacing_m = ref_spacing_px * float(spacing_resolution) if spacing_resolution else None
    ref_pixels = int(ref_art.get("px", ref_score_row.get("positive_pixels", 0)))
    parent_pixels = int(parent_score_row.get("positive_pixels", 0))
    d15_pixels = int(d15_score_row.get("positive_pixels", 0))
    ref_score_text = f"{reported_ref_score:.4f}"
    leader_score_text = f"{float(leader['public_dti']):.4f}"
    d15_delta_text = f"{reported_ref_score - float(d15_score_row['score']):+.4f}"
    pixel_resolution = (float(spacing_resolution) if spacing_resolution else
                        float(problem_facts["submission_format"]["pixel_size_m"]))
    competition_end = datetime.fromisoformat(home_facts["competition_end_utc"].replace("Z", "+00:00"))
    competition_end_text = competition_end.strftime("%Y-%m-%d %H:%M UTC")
    public_read_date = leaderboard_source.get("accessed", "date not recorded")
    reported_ref_position = (f"rank {reported_ref_rank}" if reported_ref_rank is not None else
                             "rank not reconciled")

    dl_block = ""
    if m_nan:
        dl_block = f"""
<div class="card" id="download">
<h2 style="margin-top:0">⬇ {esc(download_heading)}</h2>
<p><a class="dl" href="docs/downloads/{m_nan['name']}">Download {m_nan['name']}</a></p>
<p class="mut">{m_nan['bytes']:,} bytes · SHA-256 <code>{m_nan['sha256'][:16]}…</code> ·
{fmt_px(wr.get('px', 0))} emitted pixels · {esc(band_text)} · {grid_text} ·
{esc(download_format_detail)} Local checks do not guarantee portal acceptance; the template is an owner mirror,
not organizer-authenticated.</p>
<p>{badge(wr.get('status', 'missing status label'), status_kind(wr.get('status', 'missing')))}
{badge(gate_txt, gate_kind)}</p>
<p><b>Paste into the DrivenData <i>Note</i> field:</b></p><pre>{esc(wr.get('note', '—'))}</pre>
<p class="mut">Unique artifact name: <b>{esc(m_nan['name'].removesuffix('.tif'))}</b>.
The short portal Note shown above is limited to {artifact_format.get('note_max_characters', 'an unspecified number of')} characters. Fallbacks: <a href="docs/downloads/{m_zip['name'] if m_zip else '—'}">.zip</a> ·
<a href="docs/downloads/{m_zero['name'] if m_zero else '—'}">zero-outside TIFF</a>.
Full local receipts: <a href="docs/downloads/checks-{esc(wr.get('stem', ''))}.json">checks JSON</a>.</p>
<p><a href="docs/executive-summary.html">→ Step-by-step submission guide</a> · reference D{ref_spacing_px:g}:
<a href="docs/downloads/{esc(ref_art.get('stem', '—'))}-nan.tif">download owner-mirror mask reproduction</a>
(owner-reported {ref_score_text}; {esc(reported_ref_position)}; do not resubmit the duplicate).</p>
</div>"""

    lb_rows = "".join(f"<tr><td class='num'>{r['rank']}</td><td>{esc(r['team'])}</td>"
                      f"<td class='num'>{r['public_dti']}</td><td class='num'>{r['submissions']}</td></tr>"
                      for r in leaderboard)
    score_rows = "".join(
        f"<tr><td>{esc(s['project'])}</td><td><code>{esc(s['file'])}</code></td>"
        f"<td class='num'>{s['score']}</td><td>{esc(s.get('status', ''))}</td></tr>"
        for s in live["group_submissions"][:10])

    d28_reduction_pct = 100.0 * (1.0 - ref_pixels / parent_pixels) if parent_pixels else None
    d15_reduction_pct = 100.0 * (1.0 - d15_pixels / parent_pixels) if parent_pixels else None
    spacing_text = f"{ref_spacing_px:g} px"
    spacing_m_text = f" (~{spacing_m:g} m)" if spacing_m is not None else ""
    idx_body = f"""
<p class="mut">{badge(f'Competition end date: {competition_end_text}', 'warn')}
{badge(f"{rules_facts['automated_scoring_submissions_per_week']} automated-scoring submissions per week (official DOE/NLR rules)", 'warn')}
{badge(f'{ref_score_text} score-to-file association is owner-reported; no organizer receipt is available here', 'warn')}
{badge(f"Public leaderboard #{leader['rank']}: {leader['team']} {leader_score_text} (read {public_read_date})", 'bad')}</p>
{dl_block}
<h2>What is known about the reported {ref_score_text} raster?</h2>
<div class="card"><p>The local deterministic <code>dot_thin(H19-5, {ref_spacing_px:g})</code> reconstruction has
{fmt_px(ref_pixels)} positive pixels and matches the owner-mirrored D{ref_spacing_px:g} pixel mask exactly. The GeoTIFF bytes differ.
This verifies mask reproduction, <b>not</b> the score-to-file association. The {ref_score_text} score remains owner-reported;
it appears at {esc(reported_ref_position)} in the public leaderboard, but no organizer receipt ties that mirror to the score.</p>
<p><b>Plausible mechanism, not causal proof:</b> the registered minimum spacing is {spacing_text}{spacing_m_text}; the locally
pinned template resolution is {pixel_resolution:g} m and the official metric's linear distance-support radius is
{support_m:g} m. Its false-positive and false-negative weights are {fp_weight:g} and {fn_weight:g}, respectively.
The metric grants distance-weighted credit near mapped faults while penalizing prediction mass farther away. A sparse subset
can plausibly remove redundant or remote pixels while retaining enough nearby line coverage; a spacing near the support scale
makes that trade-off worth testing, but does not guarantee good alignment or score.</p>
<p>For context, the owner-reported H19-5 parent has {fmt_px(parent_pixels)} pixels / score {float(parent_score_row['score']):.4f}.
The D{d15_spacing_px:g} and D{ref_spacing_px:g} variants have {fmt_px(d15_pixels)} and {fmt_px(ref_pixels)} pixels, with reported scores
{float(d15_score_row['score']):.4f} and {ref_score_text} (difference {d15_delta_text}). D{ref_spacing_px:g} is about
{d28_reduction_pct:.1f}% fewer pixels than the parent (D1.5: {d15_reduction_pct:.1f}%). These within-family public-score
claims are consistent with geometric budget calibration being important, but they do not prove why any score changed.
The local comparison and provenance qualifications are in the manifest, score registry, and reproduction test.</p></div>
<h2>This session's corrected science and gate</h2>
{gate_table(gate, hold)}
<p>H29-5 persistent-corridor × deformation/seismicity screen failed against the best same-fold controls in both registered
screen draws. Confirmation was skipped under the preregistered compute-saving rule. No candidate passed and no weekly slot
is recommended; proxy values are not live/private leaderboard evidence.</p>
<h2>Public leaderboard (read once, {esc(public_read_date)})</h2>
<table><tr><th>Rank</th><th>Team</th><th>Public DTI</th><th>Subs</th></tr>{lb_rows}</table>
<h2>Group score ledger (reported claims; first 10 of {len(live['group_submissions'])})</h2>
<table><tr><th>Project</th><th>Submission</th><th>Reported score</th><th>Verification</th></tr>{score_rows}</table>
<p><a href="docs/sources.html">Full score ledger, data provenance and irregularities →</a></p>
<h2>Flagged for review ({len(irr['irregularities'])} items)</h2>
{irregularities_table(irr)}
<p>Repo contract: the owner's full brief and core values remain in <a href="https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/README.md"><code>README.md</code></a>.</p>
"""
    (ROOT / "index.html").write_text(page("GEMSDOE29 — DOE GEMS fault research", idx_body, root=True))

    exec_body = f"""
<h2 style="border:0">Submission steps</h2>
<ol>
<li>Download the TIFF from the <a href="../index.html#download">home-page download card</a>; the exact unique name,
short portal note, ZIP alternative and local receipts are shown there.</li>
<li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData My Submissions</a>
while logged in as the enrolled team. This agent does not access the portal.</li>
<li>Attach the single-band GeoTIFF or ZIP (which must contain exactly one GeoTIFF); paste the note exactly as shown.</li>
<li>Check the competition response yourself. This repo makes no claim about organizer acceptance or score.</li>
</ol>
<p>DOE/NLR rules: {rules_facts['automated_scoring_submissions_per_week']} automated-scoring submissions per week; the Initial Prize Round uses a private set; a single final
submission is selected across prize phases. Finalists must provide code/assets and documentation; generative-AI use must
be disclosed in the narrative. See the official PDF link on the Sources page.</p>
<h2>Local format verification and its limits</h2>
<div class="card"><p>The owner reported a past “Predicted values must be in range [0, 1]” error. Sibling byte-forensics
attributed one prior failing raster to NaN inside its asserted footprint; this is not an organizer validator specification.
The current local checker verifies against the pinned, owner-mirrored template:</p>
<ul>
<li>{official_format['bands']}-band {esc(official_format['dtype'])}; exact CRS, dimensions and geotransform match;</li>
<li>all template-footprint values are finite and in [{official_format['minimum']:g},{official_format['maximum']:g}];</li>
<li>NaN-outside and zero-outside TIFF variants follow their declared convention;</li>
<li>ZIP has exactly one GeoTIFF and is read back and compared with the NaN TIFF;</li>
<li>file hashes match build-time receipts.</li>
</ul><p>These checks reduce the known range-error risk but cannot guarantee portal acceptance. The source template is not
organizer-authenticated; the private validator is not public; no upload was made.</p></div>
<h2>Current artifact status</h2>
<div class="card">{badge(gate_txt, gate_kind)}
<p>WORMRANK {esc(format_status_text)} and is a research artifact. Its corrected A2 catalogue-proxy gate failed; it is not recommended
for a weekly submission slot. The selected H29-5 corridor candidate failed its screen against the best same-fold controls;
confirmation was not run under the frozen compute-saving rule, and it was not packaged as a submission.</p></div>
<h2>Reference: owner-reported D{ref_spacing_px:g} score</h2>
<p><a href="downloads/{esc(ref_art.get('stem', '—'))}-nan.tif">Download the locally reproduced D{ref_spacing_px:g} mask</a>.
Its {fmt_px(ref_pixels)} pixels exactly reproduce the pinned owner mirror. The associated {ref_score_text} score is
owner-reported; resubmitting an identical mask would be a duplicate, not a new experiment.</p>
"""
    (ROOT / "docs" / "executive-summary.html").write_text(page("How to submit — GEMSDOE29", exec_body))

    res_body = research_body(worm, gate, hold, hyp)
    (ROOT / "docs" / "research.html").write_text(page("Research & method — GEMSDOE29", res_body))

    src_body = sources_body(srcs, manifest, live, irr)
    (ROOT / "docs" / "sources.html").write_text(page("Sources & verification — GEMSDOE29", src_body))
    print("site written: index.html + docs/{executive-summary,research,sources}.html")


def gate_table(gate, hold):
    if not gate:
        return "<div class='card'>Gate results pending — run scripts/run_holdout_screen.py.</div>"
    first_gate = next((g for g in gate.values() if isinstance(g, dict)), {})
    threshold = first_gate.get("threshold_mean_delta")
    min_positive = first_gate.get("min_positive_folds")
    expected_folds = first_gate.get("expected_folds")
    screens = first_gate.get("screen_draws", [])
    confirmations = first_gate.get("confirmation_draws", [])
    if None not in (threshold, min_positive, expected_folds):
        criterion = (f"≥{float(threshold):+.3f} mean; ≥{min_positive}/{expected_folds} positive folds "
                     f"on each screen draw {screens}; ≥1 passing confirmation from {confirmations}")
    else:
        criterion = "gate criteria not recorded"
    rows = ""
    for arm, g in gate.items():
        if not isinstance(g, dict):
            continue
        parts = []
        for key, value in g.get("per_draw", {}).items():
            draw = key.removeprefix("draw")
            mean = value.get("mean_delta")
            if mean is None:
                text = f"draw{draw}: not run"
            else:
                n = value.get("n_folds", 0)
                expected = g.get("expected_folds", "not recorded")
                completeness = (f"{value.get('positive_folds', 0)}/{expected} positive" if value.get("complete")
                               else f"partial {n}/{expected} folds")
                text = f"draw{draw}: {mean:+.4f} ({completeness})"
            parts.append(text)
        cells = " · ".join(parts)
        verdict = g.get("PASS")
        vtxt = "PASS" if verdict is True else ("FAIL" if verdict is False else "INCOMPLETE")
        confirm = g.get("confirm_draw")
        if confirm is None and hold.get("confirmation_status", "").startswith("not_run"):
            confirm = "not run (screen failed)"
        rows += (f"<tr><td><b>{esc(arm)}</b></td><td>{esc(cells)}</td>"
                 f"<td>{esc(confirm or 'none')}</td>"
                 f"<td>{badge(vtxt, 'ok' if verdict is True else 'bad' if verdict is False else 'warn')}</td></tr>")
    n_rows = len(hold.get("rows", [])) if hold else 0
    run_mode = esc(hold.get("run_mode", "not recorded")) if hold else "not recorded"
    return (f"<div class='card'><table><tr><th>arm</th><th>mean paired quadrant ΔDTI (catalogue proxy)</th>"
            f"<th>confirming draw</th><th>gate ({esc(criterion)})</th></tr>"
            f"{rows}</table><p class='mut'>Mode: {run_mode}; {n_rows} fold/draw rows. Proxy truth is built from the public catalogue and is structurally blind to faults absent from it. Read the limitations and historical correction note alongside these numbers.</p></div>")


def _planning_range(h):
    delta = h.get("planning_holdout_delta_dti")
    if delta is None:
        return "not estimable"
    return f"{delta[0]:+.3f} to {delta[1]:+.3f} (planning prior only)"


def research_body(worm, gate, hold, hyp):
    if worm:
        m, g = worm.get("magnetic", {}), worm.get("gravity", {})
        la = worm.get("line_audit_magnetic", {})
        xc = worm.get("uc_crosscheck", {})
        ladder = m.get("ladder_m", [])
        max_height = max(ladder) if ladder else "not recorded"
        persistence_bounds = worm.get("constants", {}).get("persistence_bounds", [0, 1])
        strength_bounds = worm.get("constants", {}).get("strength_ratio_bounds", [0, 2])
        persistence_definition = worm.get("constants", {}).get(
            "persistence_definition", "definition not recorded")
        uc_height = xc.get("height_m", "not recorded")
        uc_layer = xc.get("reference_layer", "reference layer not recorded")
        worm_cards = f"""
<h2>Upward-continuation ladder — measurements on pinned owner-mirror rasters</h2>
<table><tr><th>field</th><th>level-0 p95 edges</th><th>full ladder ({max_height} m)</th>
<th>level-0-only</th><th>mean P</th><th>max P</th></tr>
<tr><td>rtp (magnetic)</td><td class='num'>{fmt_px(m.get('n_edges_level0', 0))}</td>
<td class='num'>{m.get('frac_edges_full_ladder', 0):.1%}</td>
<td class='num'>{m.get('frac_edges_level0_only', 0):.1%}</td>
<td class='num'>{m.get('mean_persistence', 0):.3f}</td><td>{m.get('max_persistence', 0):.1f}</td></tr>
<tr><td>iso_grav_anom</td><td class='num'>{fmt_px(g.get('n_edges_level0', 0))}</td>
<td class='num'>{g.get('frac_edges_full_ladder', 0):.1%}</td>
<td class='num'>{g.get('frac_edges_level0_only', 0):.1%}</td>
<td class='num'>{g.get('mean_persistence', 0):.3f}</td><td>{g.get('max_persistence', 0):.1f}</td></tr></table>
<p>Normalized P uses <code>{esc(persistence_definition)}</code>, bounded
[{persistence_bounds[0]:g},{persistence_bounds[1]:g}]. Strength retention is a separate
[{strength_bounds[0]:g},{strength_bounds[1]:g}] raster. Neither is a unique depth estimate nor proof that an edge is a fault.</p>
<div class='card'><p><b>Operator comparison:</b> our TMI continuation to {uc_height} m has Spearman
{xc.get('spearman_hgm_ours_vs_contractor_up150', float('nan')):.3f} rank agreement with the owner-mirrored,
u8-quantised contractor-labelled <code>{esc(uc_layer)}</code> grid's gradient ({fmt_px(xc.get('n_sampled_pixels', 0))}
sampled pixels). This is a soft operator check, not data authentication.</p>
<p><b>Strike summary only (not a spectral line-artifact test):</b> mean magnetic persistence is E–W
{la.get('mean_persist_ew_strike', 0):.3f}, other {la.get('mean_persist_other', 0):.3f}, N–S
{la.get('mean_persist_ns_strike', 0):.3f}, over {fmt_px(la.get('n_ew', 0))}/{fmt_px(la.get('n_other', 0))}/{fmt_px(la.get('n_ns', 0))}
edges. E–W edges are more persistent on average in this implementation; that does not show they are or are not flight-line
artifacts. A measured spectral notch is a separate untested hypothesis (H29-3).</p>
<p><b>Parent-emission orthogonality:</b> see the reproducibility test and H29 result for the current counted fraction;
this is why persistence was tested as a rank/feature rather than assumed to be a hard filter.</p></div>"""
    else:
        worm_cards = "<div class='card'>Worming receipt missing — run scripts/run_worming.py.</div>"

    arm_rows = ""
    for r in hold.get("rows", []):
        a, b = r.get("A", {}), r.get("B", {})
        b3 = b.get("B3", {})
        arm_rows += (f"<tr><td>{r['draw']}</td><td>{esc(r['name'])}</td><td class='num'>{r['n_hidden']:,}</td>"
                     + "".join(f"<td class='num'>{a.get(k, {}).get('paired_delta', 0):+.4f}</td>" for k in ("A1", "A2"))
                     + "".join(f"<td class='num'>{b.get(k, {}).get('paired_delta', 0):+.4f}</td>" for k in ("B1", "B2"))
                     + f"<td class='num'>{b3.get('paired_delta_best_control', float('nan')):+.4f}</td></tr>")

    hyp_rows = "".join(
        f"<tr><td>{h['rank']}</td><td><b>{esc(h['id'])}</b> {esc(h['name'])}</td>"
        f"<td>{esc(', '.join(h['layers']))}</td><td>{esc(h['signature'])}</td>"
        f"<td>{esc(h['why_unmapped'])}</td><td>{esc(h['difference_from_repo'])}</td>"
        f"<td>{esc(_planning_range(h))}<br>{esc(h['cost'])}</td>"
        f"<td>{esc(h['data_availability'])}</td></tr>" for h in hyp["hypotheses"])
    candidate_status = hold.get("gate", {}).get("H29-5", {}) if hold else {}
    candidate_verdict = candidate_status.get("PASS")
    candidate_text = ("PASS — eligible for owner review only" if candidate_verdict is True else
                      "FAIL — not submission-eligible on this proxy" if candidate_verdict is False else
                      "incomplete / no result")
    confirm_status = hold.get("confirmation_status", "not recorded") if hold else "not recorded"
    return f"""
<h2>Worming: scale persistence is a structural cue, not a fault verdict</h2>
<p>Fourier upward continuation smooths potential fields by a physically motivated scale operator. This implementation
takes horizontal-gradient-modulus maxima at fixed heights and links nearby maxima between adjacent ladder levels.
Tracks that persist may be consistent with broader/deeper source contrasts, but persistence is also affected by amplitude,
source geometry, interference and processing; it is neither a unique depth inversion nor proof of a fault. See the corrected
Hornby DOI and operational caveats in <a href="sources.html">Sources</a>.</p>
{worm_cards}
<h2>Pre-registered spatial holdout results</h2>
{gate_table(gate, hold)}
<p><b>H29-5 status:</b> {esc(candidate_text)}. Confirmation status: {esc(confirm_status)}. The screen compares the new
persistence × strain/seismicity head to the best same-fold/same-draw pre-existing control; no leaderboard score is inferred.</p>
<table><tr><th>draw</th><th>fold</th><th>hidden px</th><th>ΔA1</th><th>ΔA2</th><th>ΔB1</th><th>ΔB2</th><th>H29-5 Δ vs best control</th></tr>
{arm_rows or '<tr><td colspan=8>pending</td></tr>'}</table>
<h2>Preregistered geological hypotheses (planning priors, not score predictions)</h2>
<table><tr><th># / hypothesis</th><th>layers</th><th>target signature</th><th>why it could detect an unmapped fault</th><th>difference from prior work</th><th>holdout ΔDTI prior / cost</th><th>data availability</th></tr>{hyp_rows}</table>
<h2>Interpretation for the leaderboard goal</h2>
<div class="card"><p>There is no evidence from this run that the new H29-5 head improves over the strongest existing control on the
catalogue proxy. That failure makes it ineligible for a submission slot under the frozen gate; it does not disprove the
geological mechanism or predict private-set performance. The 0.2600 association remains owner-reported. Further candidate
work should be preregistered, tested spatially, and treated as proxy evidence only; a live score requires a manual portal
submission and must be recorded separately.</p></div>
"""


def sources_body(srcs, manifest, live, irr):
    source_rows = "".join(
        f"<tr><td><a href='{esc(s['url'])}'>{esc(s['url'])}</a></td><td>{esc(s.get('accessed', '—'))}</td>"
        f"<td>{badge(s.get('status', ''), status_kind(s.get('status', '')))}</td><td>{esc(s.get('claims', '—'))}</td></tr>"
        for s in srcs["sources"])
    manifest_rows = "".join(
        f"<tr><td><code>{esc(f['path'])}</code></td><td class='num'>{f['bytes']:,}</td>"
        f"<td><code>{f['sha256'][:20]}…</code></td><td>{esc(f['what'])}</td></tr>"
        for f in manifest["files"])
    all_scores = "".join(
        f"<tr><td>{esc(s['project'])}</td><td><code>{esc(s['file'])}</code></td>"
        f"<td class='num'>{s['score']}</td><td>{esc(s.get('status', s.get('parent', s.get('note', ''))))}</td></tr>"
        for s in live["group_submissions"])
    return f"""
<h2 style="border:0">Official sources and claims</h2>
<table><tr><th>source</th><th>accessed (UTC)</th><th>state</th><th>what the source says</th></tr>{source_rows}</table>
<h2>Input data provenance (hash-pinned owner mirrors — NOT organizer-authenticated)</h2>
<p class="mut">{esc(manifest['note'])}</p>
<table><tr><th>path</th><th>bytes</th><th>SHA-256</th><th>content</th></tr>{manifest_rows}</table>
<h3>Blocked external files</h3>
<ul>{''.join(f"<li><code>{esc(b['key'])}</code> — <a href='{esc(b['url'])}'>{esc(b['url'])}</a> — {esc(b['reason'])}</li>" for b in manifest['blocked_this_session'])}</ul>
<h2>Score ledger (reported claims and verification state)</h2>
<p class="mut">{esc(live['verification_note'])}</p>
<table><tr><th>project</th><th>submission</th><th>reported score</th><th>verification / parent</th></tr>{all_scores}</table>
<h2>Irregularities register</h2>{irregularities_table(irr)}
"""


def irregularities_table(irr):
    return ("<table><tr><th>ID</th><th>severity</th><th>state</th><th>finding → action</th></tr>" + "".join(
        f"<tr><td><code>{esc(i['id'])}</code></td><td>{badge(i['sev'], status_kind(i['sev']))}</td>"
        f"<td>{esc(i['status'])}</td><td>{esc(i['finding'])}<br><span class='mut'>→ {esc(i['action'])}</span></td></tr>"
        for i in irr["irregularities"]) + "</table>")


if __name__ == "__main__":
    main()
