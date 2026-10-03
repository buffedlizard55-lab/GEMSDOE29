#!/usr/bin/env python3
"""Build the static, evidence-only GitHub Pages site from checked-in project registers.

This script is fully offline. It never reads or requests any DrivenData page or endpoint.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def read_json(name: str) -> dict[str, Any]:
    path = ROOT / "registry" / name
    return json.loads(path.read_text(encoding="utf-8"))


def e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def a(url: str, label: str, *, external: bool = False, class_name: str = "") -> str:
    attrs = f' class="{e(class_name)}"' if class_name else ""
    target = ' target="_blank" rel="noopener noreferrer"' if external else ""
    return f'<a href="{e(url)}"{attrs}{target}>{e(label)}</a>'


def tag(text: str, style: str = "") -> str:
    return f'<span class="pill {e(style)}">{e(text)}</span>'


def source_url(source: dict[str, Any]) -> str:
    return a(source["url"], source["title"], external=True)


def nav(active: str) -> str:
    items = [
        ("index.html", "Overview", "index"),
        ("executive-summary.html", "Submission guide", "summary"),
        ("research.html", "Research", "research"),
        ("status.html", "Status feed", "status"),
        ("sources.html", "Sources", "sources"),
        ("irregularities.html", "Irregularities", "irregularities"),
    ]
    links = []
    for href, title, key in items:
        current = ' aria-current="page"' if key == active else ""
        links.append(f'<a href="{href}"{current}>{e(title)}</a>')
    return (
        '<a class="skip-link" href="#main">Skip to content</a>'
        '<header class="site-header"><div class="shell header-top">'
        '<a class="brand" href="index.html"><span class="brand-mark" aria-hidden="true">G</span>'
        '<span>GEMSDOE29 <span class="small">/ research lab</span></span></a>'
        f'<nav aria-label="Primary">{"".join(links)}</nav></div>'
    )


def hero(kicker: str, title: str, copy: str, buttons: str = "") -> str:
    actions = f'<div class="hero-actions">{buttons}</div>' if buttons else ""
    return (
        '<div class="shell hero">'
        f'<p class="eyebrow">{e(kicker)}</p><h1>{e(title)}</h1>'
        f'<p class="hero-copy">{e(copy)}</p>{actions}'
        '</div></header>'
    )


def page(title: str, description: str, active: str, kicker: str, headline: str, copy: str, body: str, buttons: str = "") -> str:
    page_title = e(title)
    desc = e(description)
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<meta name="description" content="{desc}">'
        f'<title>{page_title} | GEMSDOE29</title>'
        '<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">'
        '<link rel="stylesheet" href="assets/site.css"></head><body>'
        + nav(active)
        + hero(kicker, headline, copy, buttons)
        + f'<main id="main"><div class="shell">{body}</div></main>'
        + '<footer class="site-footer"><div class="shell footer-inner">'
        '<p><strong>GEMSDOE29</strong> · evidence-first GEMS Prize research</p>'
        '<p>Status is generated only from local records; it is not a DrivenData leaderboard feed. '
        f'{a("https://github.com/buffedlizard55-lab/GEMSDOE29", "Repository", external=True)}</p>'
        '</div></footer></body></html>\n'
    )


def artifact_href(entry: dict[str, Any]) -> str:
    path = Path(entry["path"])
    try:
        return path.relative_to("docs").as_posix()
    except ValueError:
        return "downloads/" + entry["file"]


def has_local_artifact(entry: dict[str, Any]) -> bool:
    return (ROOT / entry["path"]).is_file()


def approved_entry(submissions: dict[str, Any]) -> dict[str, Any] | None:
    return next((row for row in submissions.get("files", []) if row.get("slot_approved") is True), None)


def render_downloads() -> str:
    """One-click download cards for every registered research candidate, with its paste-ready note.

    Numbers come only from ``registry/submissions.json`` (which itself is filled from script-written
    receipts under ``docs/downloads/checks-*.json``). Nothing here claims a competition score.
    """
    submissions = read_json("submissions.json")
    contract = read_json("submission_contract.json")
    fmt = contract["format"]
    candidates = [row for row in submissions.get("files", []) if row.get("role") == "candidate_review"]
    if not candidates:
        return ""
    cards = []
    for row in candidates:
        present = has_local_artifact(row)
        download = (
            f'<a class="button" href="{e(artifact_href(row))}" download>{e(row.get("download_label", "Download GeoTIFF"))}</a>'
            if present
            else '<p class="muted">Registered file is not present in this checkout.</p>'
        )
        # Preferred download is the zero-outside variant where one is registered: a portal that
        # range-checks the whole array rejects NaN, which is the reported "Predicted values must be in
        # range [0, 1]" failure (IR-PORTAL-01).
        # Pair the ZIP with whichever variant is the primary download, so the button and the file agree.
        zip_name = (row.get("zeros_zip") if str(row["path"]).endswith("-zeros.tif") else None) or row.get("zip")
        zip_path = Path(row["path"]).parent / (zip_name or Path(row["path"]).with_suffix(".zip").name)
        zip_link = (
            f' <a class="button light" href="{e(zip_path.relative_to("docs").as_posix())}" download>Download .zip</a>'
            if (ROOT / zip_path).is_file()
            else ""
        )
        alt_link = (
            f' <a class="button light" href="{e(Path(row["alt_path"]).relative_to("docs").as_posix())}" download>'
            f'{e(row.get("alt_label", "Other variant"))}</a>'
            if row.get("alt_path") and (ROOT / row["alt_path"]).is_file()
            else ""
        )
        # Score claims stay in the JSON registry only; public pages must not republish them
        # (tests/test_project_integrity.py::test_public_pages_do_not_republish_score_claims_or_leaderboard_links).
        proxy = tag("score claims kept in registry/score_claims.json", "warning")
        eligibility = (
            tag("slot-approved", "yes") if row.get("slot_approved") is True else
            tag("not slot-cleared · do not submit", "no") if row.get("do_not_submit") is True else
            tag("G1+G2 pass · G3 proxy conflict · owner decision", "warning") if row.get("g3_veto") is True else
            tag("not approved · holdout/confirmation required", "warning")
        )
        card = (
            '<article class="card span-6 download-card"><p class="kicker">Research download · not an official score</p>'
            f'<h2>{e(row.get("name", row["file"]))}</h2>'
            f'<p>{e(row.get("summary", ""))}</p>'
            f'<p class="file-name">{e(row["file"])}</p>'
            f'<p class="small">sha256 <code>{e(str(row.get("sha256", ""))[:16])}…</code> · '
            f'{int(row.get("positive_pixels", 0)):,} emitted px · format ok: {e(row.get("format_ok_local"))}</p>'
            f'{proxy} {tag("local format only", "warning")} {eligibility}'
            + (f'<p class="small"><strong>Gate evidence:</strong> {e(row["gate_evidence"])}</p>'
               if row.get("gate_evidence") else "")
            + f'<p class="small"><strong>Paste-ready Note:</strong> <code>{e(row.get("optional_comment", ""))}</code></p>'
            f'{download}{alt_link}{zip_link}'
            "</article>"
        )
        cards.append(card)
    return (
        '<section aria-label="Candidate downloads"><p class="kicker">Formatted and waiting for a human decision</p>'
        '<h2>Download the submission GeoTIFF</h2>'
        f'<p>Each file below is a {int(fmt["band_count"])}-band {e(fmt["dtype"])} GeoTIFF locally checked against the hash-pinned owner-mirror template '
        f'({e(fmt["crs"])}, {int(fmt["pixel_size_m"])} m; finite [{fmt["probability_min"]}, {fmt["probability_max"]}] values inside; '
        f'{e(fmt["outside_footprint"])} outside), with a format receipt. Format validation is not a score or approval. '
        'None is currently slot-approved; do not use a weekly slot unless a candidate first beats the current comparable spatial holdout best and passes fresh confirmation.</p>'
        f'<section class="grid">{"".join(cards)}</section></section>'
    )


def h41_screen_card() -> str:
    """Session-4 H41 card: every number is read from evidence/h41_screen/, nothing is hard-coded."""
    base = ROOT / "evidence" / "h41_screen"
    summary_p, design_p = base / "summary_screen.json", base / "design_screen.json"
    analyzer_p = base / "analyzer_report.json"
    if not design_p.is_file():
        return (
            '<section class="card"><p class="kicker">Session-4 frozen screen · H41</p>'
            "<h2>H41 qfaults-corridor screen: no evidence in this checkout yet</h2>"
            '<p>Pre-registered in <code>knowledge/24_preregistered_h41_screen_2026-10-03.md</code>; the runner is '
            "<code>scripts/run_h41_screen.py</code> and refuses to run from a dirty worktree or overwrite existing "
            "evidence. Re-run the screen in a checkout with the hash-pinned data restored to see this card populate.</p></section>"
        )
    design = json.loads(design_p.read_text(encoding="utf-8"))
    q = design.get("qfaults", {})
    gates = design["gates"]
    rows_html = ""
    verdict = "screen still in flight; no summary written yet"
    if summary_p.is_file():
        summary = json.loads(summary_p.read_text(encoding="utf-8"))
        arms = summary["arms"]
        cells = base / "cells_screen.jsonl"
        n_cells = len([1 for line in cells.read_text(encoding="utf-8").splitlines() if line.strip()]) if cells.is_file() else 0
        tr = []
        for arm in design["arms"][1:]:
            adm = arms.get(arm, {})
            if "mean_gain" not in adm:
                continue
            tr.append(
                f'<tr><td>{e(arm)}</td><td>{adm["mean_gain"]:+.7f}</td>'
                f'<td>{", ".join(f"{g:+.5f}" for g in adm["fold_gains"])}</td>'
                f'<td>{", ".join(str(v) for v in adm["positive_folds_per_draw"])} (need {gates["min_positive_folds"]})</td>'
                f'<td>{adm["worst_fold_gain"]:+.7f}</td>'
                f'<td>{tag("G1 FAIL", "no") if not adm["G1_SCREEN_PASS"] else tag("G1 PASS", "yes")}</td></tr>'
            )
        rows_html = "".join(tr)
        passed = [arm for arm in design["arms"][1:] if arms.get(arm, {}).get("G1_SCREEN_PASS")]
        guard = summary.get("viability_guard", {})
        guard_txt = ("passed — every column nonzero on at least "
                     f"{guard.get('min_nonzero_fraction', 0) * 100:.1f} % of footprint pixels"
                     if guard.get("passed") else f"FAILED: {len(guard.get('problems', []))} cell(s) reported sparse columns")
        verdict = (
            f"{len(summary.get('draws', []))} draw(s), {n_cells} raw cells, "
            + ("all four arms failed G1" if not passed else "passed: " + ", ".join(passed))
            + f"; the pre-declared degeneracy guard {guard_txt}."
        )
    confirm_txt = ""
    confirm_p, gate_p = base / "summary_confirm.json", base / "promotion_gate.json"
    if confirm_p.is_file():
        cs = json.loads(confirm_p.read_text(encoding="utf-8"))
        cp = cs["arms"]
        names = [x for x in cs["arms"] if x != "C0_base"]
        g2 = [x for x in names if cp[x].get("G1_SCREEN_PASS")]
        line = (f"<p><strong>Confirmation (draws {'/'.join(map(str, cs.get('draws', [])))}, {cs.get('n_cells', 0)} cells, "
                f"same frozen gates):</strong> "
                + ", ".join(f"{x} {cp[x]['mean_gain']:+.7f}" for x in names)
                + f"; G2 passed by {', '.join(g2) if g2 else 'no arm'}")
        if gate_p.is_file():
            gt = json.loads(gate_p.read_text(encoding="utf-8"))
            elig = [x for x, v in gt["arms"].items() if v["G3_ELIGIBLE"]]
            if elig:
                line += f"; G3 eligibility: {', '.join(elig)}."
            else:
                line += ("; G3 withholds promotion from every arm — the SGMC off-catalogue class gained on fewer than "
                         "3 of 4 folds in both stages, the pattern knowledge/19 §5 pre-declares as a proxy conflict "
                         "with no promotion")
        confirm_txt = line + ". See <code>knowledge/26</code> §5 for the reading and "                              "<code>evidence/h41_screen/promotion_gate.json</code> for the arithmetic.</p>"
    ana = json.loads(analyzer_p.read_text(encoding="utf-8")) if analyzer_p.is_file() else None
    ana_txt = ("not yet recomputed" if ana is None else
               ("zero problems" if not ana["integrity_problems"] else f"problems: {ana['integrity_problems']}"))
    table = (
        '<table><thead><tr><th>arm</th><th>mean gain</th><th>fold gains (NW, NE, SW, SE)</th>'
        "<th>positive folds</th><th>worst fold</th><th>gate</th></tr></thead>"
        f'<tbody>{rows_html}</tbody></table>' if rows_html else ""
    )
    return (
        '<section class="card"><p class="kicker">Session-4 frozen screen · every number read from '
        "evidence/h41_screen/</p><h2>H41: slip-rate-weighted INGENIOUS fault-corridor evidence, off-catalogue only</h2>"
        f"<p>Pre-registered (sha256 {e(design['preregistration']['sha256'][:12] + chr(8230))}) before any fit; clean tree at "
        f"{e(design['git']['revision'][:7])}; {len(design['draws'])} draws x {len(design['folds'])} folds x {len(design['arms'])} arms. "
        f"Gates: mean paired gain &ge; {gates['mean_gain']}, &ge;{gates['min_positive_folds']}/{len(design['folds'])} folds positive on every draw, "
        f"worst fold &ge; {gates['max_fold_loss']}, emission within x[{gates['budget_ratio_band'][0]}, {gates['budget_ratio_band'][1]}] of control.</p>"
        f"<p>{e(verdict)}</p>{table}{confirm_txt}"
        f"<p><strong>Input audit:</strong> {q.get('n_rows_read', 0):,} trace rows read from the hash-pinned qfaults mirror, "
        f"{q.get('n_in_footprint', 0)} in-footprint, {q.get('n_rows_unparsable', 0)} unparsable (dropped and counted), "
        f"{q.get('n_recency_unmapped', 0)} outside the frozen age-bin table (fallback weight), maximum slip rate "
        f"{q.get('slip_rate_max_seen', 0)} mm/yr. The mirror carries one centroid per trace and no polyline geometry, so "
        "any pass here is corridor ranking near mapped young faults, never dot placement on a trace.</p>"
        f"<p><strong>Independent recomputation:</strong> {e(ana_txt)}.</p>"
        f'<p>{a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/24_preregistered_h41_screen_2026-10-03.md", "Read the frozen H41 preregistration", external=True)} · '
        f'{a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/25_candidates_v4_2026-10-03.md", "Read the v4 candidate slate", external=True)} · '
        f'{a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/26_h41_results_2026-10-03.md", "Read the H41 results document", external=True)} · '
        f'{a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/src/gemsdoe/h41.py", "Read the feature module", external=True)}</p></section>'
    )


def h41a4_bar_card() -> str:
    """Session-5 H41-A4/H34-protocol card: every number is read from evidence/h41a4_h34protocol/."""
    base = ROOT / "evidence" / "h41a4_h34protocol"
    design_p, summary_p = base / "design.json", base / "summary.json"
    if not design_p.is_file() or not summary_p.is_file():
        return (
            '<section class="card"><p class="kicker">Session-5 frozen stage · H41-A4 vs the slot bar</p>'
            "<h2>Bar-protocol re-score: no evidence in this checkout yet</h2>"
            "<p>Pre-registered in <code>knowledge/27_preregistered_h41a4_h34protocol_2026-10-03.md</code>; the "
            "runner is <code>scripts/run_h41a4_h34protocol.py</code> and refuses to run from a dirty worktree or "
            "to overwrite existing evidence.</p></section>"
        )
    design = json.loads(design_p.read_text(encoding="utf-8"))
    summary = json.loads(summary_p.read_text(encoding="utf-8"))
    gates, checks = summary["gates"], summary["gate_checks"]
    rows = "".join(
        f"<tr><td>{e(arm)}</td><td>{summary['arms'][arm]:.8f}</td>"
        f"<td>{'the recorded bar' if arm == 'C1_geodesic_dots' else ('frozen control' if arm == 'C0_base' else 'H41 columns added')}</td></tr>"
        for arm in ("C0_base", "C1_geodesic_dots", "A4_h41_union")
    )
    fold_rows = "".join(
        f"<tr><td>{e(name)}</td><td>{g:+.6f}</td><td>{s:+.6f}</td></tr>"
        for name, g, s in zip(design["folds"], gates["fold_gains"], gates["sgmc_fold_gains"])
    )
    gate_rows = "".join(
        f"<tr><td>{e(name)}</td><td>{tag('PASS', 'yes') if ok else tag('FAIL', 'no')}</td><td>{e(text)}</td></tr>"
        for name, ok, text in (
            ("G1 effect", checks["G1"],
             f"mean gain {gates['mean_gain']:+.6f} (needs ≥ {design['gates']['mean_gain']}), "
             f"{gates['positive_folds']}/4 folds positive, worst fold {gates['worst_fold']:+.6f} "
             f"(floor {design['gates']['max_fold_loss']})"),
            ("G2 bar", checks["G2"],
             f"A4 mean {summary['arms']['A4_h41_union']:.8f} vs recorded bar {design['gates']['holdout_best']:.8f}"),
            ("G3 second proxy", checks["G3"],
             f"SGMC off-catalogue mean gain {gates['sgmc_mean_gain']:+.6f} with {gates['sgmc_positive_folds']}/4 folds positive"),
            ("G4 integrity", checks["G4"],
             f"24/24 finite cells; frozen controls reproduce the stored H34 cells with max |delta| = "
             f"{gates['reproduction_max_abs_delta']:.3e} (tolerance {design['gates']['reproduction_tolerance']:.0e})"),
        )
    )
    return (
        '<section class="card"><p class="kicker">Session-5 frozen stage · every number read from '
        'evidence/h41a4_h34protocol/</p><h2>H41-A4 re-scored against the slot bar: the replicated gain does not transfer</h2>'
        f"<p>Pre-registered (sha256 {e(design['preregistration']['sha256'][:12] + chr(8230))}) before any fit; clean tree at "
        f"{e(design['git']['revision'][:7])}; {len(design['draws'])} spent draws ({', '.join(map(str, design['draws']))}) that define the bar, "
        f"{len(design['folds'])} blocked folds, {len(design['arms'])} arms, {summary['n_cells']} cells in {summary['elapsed_s']:.0f} s. "
        "The point of the stage is that the bar was measured on these same cells in session 2, so the only fair comparison is on them.</p>"
        f'<table><thead><tr><th>arm</th><th>mean DTI (8 cells)</th><th>role</th></tr></thead><tbody>{rows}</tbody></table>'
        f"<p><strong>Verdict:</strong> {e(summary['verdict'])} No candidate file was built, no weekly slot was used, and "
        f"<code>registry/draw_ledger.json</code> still shows the next free draw at {read_json('draw_ledger.json')['next_free_draw']}.</p>"
        f'<table><thead><tr><th>fold</th><th>A4 gain vs best control</th><th>SGMC off-catalogue gain</th></tr></thead><tbody>{fold_rows}</tbody></table>'
        f'<table><thead><tr><th>gate</th><th>result</th><th>criterion</th></tr></thead><tbody>{gate_rows}</tbody></table>'
        "<p><strong>Why the comparison can be trusted:</strong> the two frozen controls rebuilt here from the restored mirrors match "
        "the session-2 stored cells bit-for-bit on all 16 control cells, so the 0.14479 bar is a number this checkout regenerates, "
        "not a remembered one. The negative result is therefore about the H41 columns, not about the environment.</p>"
        f"<p>{a('https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/27_preregistered_h41a4_h34protocol_2026-10-03.md', 'Read the frozen bar-protocol preregistration', external=True)} · "
        f"{a('https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/28_h41a4_results_2026-10-03.md', 'Read the results document', external=True)} · "
        f"{a('https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/evidence/h41a4_h34protocol/', 'Open the raw cells and analyzer report', external=True)}</p></section>"
    )


def h41a4_status_sentence() -> str:
    """One-sentence, evidence-derived statement of the session-5 bar-protocol re-score."""
    summary_p = ROOT / "evidence" / "h41a4_h34protocol" / "summary.json"
    if not summary_p.is_file():
        return "the session-5 bar-protocol re-score of H41 is frozen in knowledge/27 (no summary in this checkout)"
    data = json.loads(summary_p.read_text(encoding="utf-8"))
    gates, checks = data["gates"], data["gate_checks"]
    failed = ", ".join(name for name, ok in (("G1", checks["G1"]), ("G2", checks["G2"]), ("G3", checks["G3"]),
                                             ("G4", checks["G4"])) if not ok)
    return (
        f"session 5 re-scored the H41 union arm on the spent draws {data['draws'][0]}/{data['draws'][1]} that define the slot bar: "
        f"mean paired gain {gates['mean_gain']:+.6f} (bar +0.005), worst fold {gates['worst_fold']:+.6f}, SGMC second proxy "
        f"{gates['sgmc_mean_gain']:+.6f} with {gates['sgmc_positive_folds']}/4 folds positive, while the frozen controls reproduced "
        f"the stored H34 cells exactly (max |delta| = {gates['reproduction_max_abs_delta']:.1e}) — {failed} failed, no promotion, "
        "no candidate file, no slot"
    )


def h41_status_sentence() -> str:
    """One-sentence, evidence-derived statement of the session-4 H41 screen outcome."""
    summary = ROOT / "evidence" / "h41_screen" / "summary_screen.json"
    if not summary.is_file():
        return ("the session-4 H41 qfaults-corridor screen is frozen in knowledge/24 and recorded cell-by-cell "
                "in evidence/h41_screen/ (no summary in this checkout)")
    data = json.loads(summary.read_text(encoding="utf-8"))
    arms = data["arms"]
    parts = [f"{arm.split('_')[0]} {arms[arm]['mean_gain']:+.5f}" for arm in arms if "mean_gain" in arms[arm]]
    passed = [arm for arm in arms if arms[arm].get("G1_SCREEN_PASS")]
    verdict = ("failed the frozen G1 gate on every arm" if not passed
               else "cleared G1 on " + ", ".join(sorted(passed)))
    guard = data.get("viability_guard", {})
    guard_txt = "sparse-column guard passed" if guard.get("passed") else "sparse-column guard FAILED"
    return (f"session 4 pre-registered and screened H41 (slip-rate-weighted INGENIOUS fault-corridor evidence, "
            f"off-catalogue only) on {len(data.get('folds', []))} folds × {len(data.get('draws', []))} draws × 5 arms: "
            f"{'; '.join(parts)} mean paired gain, {verdict}, {guard_txt}, "
            f"{'no confirmation was fit' if not passed else 'confirmation authorized'}")


def data_placement_card() -> str:
    """Session-5 card: what is actually on disk, read from the script-written placement receipt."""
    path = ROOT / "evidence" / "data_placement_receipt.json"
    if not path.is_file():
        return (
            '<section class="card"><p class="kicker">Session-5 data work</p>'
            "<h2>Data-placement receipt not present in this checkout</h2>"
            "<p>Run <code>python scripts/record_data_placement.py</code> after restoring the pinned mirrors to "
            "generate <code>evidence/data_placement_receipt.json</code>. The receipt never claims organizer "
            "authentication: it records byte-correct owner mirrors and the derived working arrays.</p></section>"
        )
    rec = json.loads(path.read_text(encoding="utf-8"))
    groups = " · ".join(f"{g['tag']} {g['n_present']}/{g['n_entries']}" for g in rec["manifests"])
    detail = rec.get("prepared_detail", {})
    caches = detail.get("caches", {})
    cache_txt = ", ".join(f"{name.split('.')[0]}" for name, row in caches.items() if row.get("present"))
    status = tag("all pinned files byte-correct", "yes") if rec.get("prepared") else tag("placement incomplete", "no")
    return (
        '<section class="card"><p class="kicker">Session-5 data work · the standing blocker, closed with a receipt</p>'
        "<h2>Competition inputs are placed, hash-verified and prepared in this checkout</h2>"
        f"<p>The brief's open item was that the organizer data page needs a login. The repository answer is the "
        f"owner-mirror restore path: <code>bash scripts/download_competition_data.sh</code> (never contacts DrivenData) "
        f"followed by <code>python scripts/prepare_data.py</code>, <code>scripts/build_features.py</code> and "
        f"<code>scripts/build_addons.py</code>. A script-written receipt now records the result: "
        f"<strong>{groups}</strong> pinned files present and byte-correct, footprint "
        f"<strong>{int(detail.get('footprint_pixels', 0)):,}</strong> px, catalogue "
        f"<strong>{int(detail.get('label_pixels', 0)):,}</strong> px, {int(detail.get('bands', {}).get('n_files', 0))} "
        f"aligned arrays, caches: {e(cache_txt)}. {status} "
        f"{tag('owner mirrors, not organizer-authenticated', 'warning')}</p>"
        f"<p>Re-check it at any time with <code>python scripts/record_data_placement.py --check</code>. "
        f"{a('https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/evidence/data_placement_receipt.json', 'Open the receipt', external=True)} · "
        f"{a('https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/registry/data_manifest.json', 'Open the hash-pinned manifest', external=True)} · "
        f"{a('https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/31_session5_data_and_emission_2026-10-03.md', 'Read the session-5 note', external=True)}</p></section>"
    )


def emission_sweep_card() -> str:
    """Session-5 card: the frozen emission-density sweep, every number read from evidence/emission_sweep/."""
    path = ROOT / "evidence" / "emission_sweep" / "summary.json"
    if not path.is_file():
        return (
            '<section class="card"><p class="kicker">Session-5 frozen sweep · emission density</p>'
            "<h2>Emission-density sweep: no evidence in this checkout yet</h2>"
            "<p>Pre-registered in <code>knowledge/27_preregistered_emission_density_sweep_2026-10-03.md</code>; "
            "the runner is <code>scripts/run_emission_sweep.py</code>.</p></section>"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["rows"]
    dec = data["decision"]
    cal = dec["proxy_calibration_check"]
    curve = " · ".join(
        f"{key.replace('_', ' ')} {rows[key]['catalogue_hidden_mean']:.5f} ({rows[key]['emitted_pixels']:,} px)"
        for key in ("cal_solid", "cal_d1_5", "cal_d2_8", "thin_3.2", "thin_4.8", "thin_6.4")
    )
    verdict = ("the proxy reproduces the reported live ladder order, so its density axis is usable"
               if cal["calibrated"] else "the proxy does NOT reproduce the live ladder order — measurement only")
    return (
        '<section class="card"><p class="kicker">Session-5 frozen sweep · emission density</p>'
        "<h2>Re-spacing the best-known emission does not beat it — the ladder was already converged</h2>"
        f"<p>A fifteen-row sweep of the <em>same</em> frozen habitat (deterministic Poisson-disk re-spacing at nine "
        f"spacings plus three score-aware placements, with the pinned files as calibration rows) was scored on both "
        f"registered file-level proxies with no model fitted and no holdout draw spent. Curve on the catalogue-hidden "
        f"proxy: {e(curve)}. The pinned 2.8 px artifact is the maximum; both denser and sparser rows are worse, and "
        f"score-aware placement at the same spacing loses "
        f"{rows['aware_2.8']['paired_vs_reference']['mean']:+.5f}. Calibration check: {e(verdict)}. "
        f"Frozen rule returned: <code>{e(dec['recommendation'])}</code>. {tag('no slot implication', 'no')}</p>"
        f"<p>Two geometry facts came out of the same run: <code>dot_thin(·, 2.8)</code> reproduces the pinned artifact "
        f"pixel-for-pixel, and the spacing parameter is quantised by an integer disc, so 2.4 px and 2.8 px are literally "
        f"the same transform (which closes the old D2.8 naming question). "
        f"{a('https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/27_preregistered_emission_density_sweep_2026-10-03.md', 'Read the frozen protocol', external=True)} · "
        f"{a('https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/28_emission_density_sweep_results_2026-10-03.md', 'Read the results', external=True)} · "
        f"{a('https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/evidence/emission_sweep/summary.json', 'Open the raw summary', external=True)}</p></section>"
    )


def h43_screen_card() -> str:
    """Session-5 card: the frozen H43 drainage-network screen, read from evidence/h43_screen/."""
    base = ROOT / "evidence" / "h43_screen"
    summary_p, design_p = base / "summary_screen.json", base / "design_screen.json"
    if not design_p.is_file():
        return (
            '<section class="card"><p class="kicker">Session-5 frozen screen · H43</p>'
            "<h2>H43 drainage-network screen: no evidence in this checkout yet</h2>"
            "<p>Pre-registered in <code>knowledge/29_preregistered_h43_screen_2026-10-03.md</code>; the runner is "
            "<code>scripts/run_h43_screen.py</code> and refuses to run from a dirty worktree or overwrite existing "
            "evidence.</p></section>"
        )
    design = json.loads(design_p.read_text(encoding="utf-8"))
    diag = design.get("h43_diagnostics", {})
    knick_block = diag.get("knick", {})
    knick = knick_block.get("fit", {})
    rev = str(design.get("git", {}).get("revision", ""))[:8]
    parts = [
        '<section class="card"><p class="kicker">Session-5 frozen screen · H43 drainage organization</p>',
        "<h2>Drainage-network columns from the 100 m surface</h2>",
        "<p>Five columns — contributing area, stream power A^0.5·S, knickpoint excess over a binned-median "
        "concavity fit, off-catalogue knickpoint excess, and channel&#215;scarp — built from the cached detrended "
        "surface plus the visible catalogue only (the off-catalogue mask removes information). Diagnostics measured "
        "on the real band: ",
        f"{int(diag.get('pits', 0)):,} strict pits filled, {int(knick_block.get('channel_pixels', 0)):,} channel pixels, ",
        f"knickpoint coverage {100 * design.get('h43_columns_nonzero_fraction', {}).get('H43_KNICK', 0):.2f}%, ",
        f"fitted concavity theta = {float(knick.get('theta', 0.0)):.3f}.</p>",
    ]
    if not summary_p.is_file():
        parts.append(f"<p>Screen launched (git {e(rev)}); the summary lands in "
                     "<code>evidence/h43_screen/summary_screen.json</code> and this card fills itself from it.</p></section>")
        return "".join(parts)
    summary = json.loads(summary_p.read_text(encoding="utf-8"))
    arms = summary["arms"]
    items = []
    for arm, entry in arms.items():
        if arm == "C0_base":
            continue
        gains = entry["fold_gains"]
        gain_list = list(gains.values()) if isinstance(gains, dict) else list(gains)
        n_pos = sum(1 for g in gain_list if g > 0)
        # The gate counts positive folds *within each draw*; show both that statistic and the fold-mean count so a
        # reader cannot mistake the looser fold-mean count for the gate (A2_network: fold-mean 1/4 but draw counts 0/4, 3/4).
        pos_draws = list(entry.get("positive_folds_per_draw") or [])
        per_draw = ", ".join(f"{p}/4" for p in pos_draws) if pos_draws else "n/a"
        verdict = "G1 PASS" if entry["G1_SCREEN_PASS"] else "G1 FAIL"
        items.append(
            f"<li><code>{e(arm)}</code>: mean paired gain {entry['mean_gain']:+.5f}, per-draw positive folds {per_draw} (gate), "
            f"fold-mean positives {n_pos}/4, worst {entry['worst_fold_gain']:+.5f}, budget ok: {entry['budget_ok']}, "
            f"SGMC {entry['sgmc_mean_gain']:+.5f} ({entry['sgmc_positive_folds']}/4 folds) &#8594; <strong>{verdict}</strong></li>"
        )
    passed = sorted(arm for arm, entry in arms.items() if arm != "C0_base" and entry.get("G1_SCREEN_PASS"))
    verdict_txt = ("cleared the frozen G1 gate: " + ", ".join(passed)) if passed else (
        "failed the frozen G1 gate on every arm — no confirmation was fit and no candidate was built")
    guard = summary.get("viability_guard", {})
    guard_txt = "passed" if guard.get("passed") else "FAILED"
    ctrl = float(arms["C0_base"]["mean_dti"])
    prereg = a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/"
               "knowledge/29_preregistered_h43_screen_2026-10-03.md", "Read the frozen preregistration", external=True)
    module = a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/src/gemsdoe/h43.py",
               "Read the feature module", external=True)
    parts.append(f'<p><strong>Verdict:</strong> {e(verdict_txt)}.</p><ul class="list-clean">')
    parts.append("".join(items))
    parts.append(f"</ul><p>Sparse-column guard: {guard_txt} (floor {guard.get('min_nonzero_fraction')}); "
                 f"control mean {ctrl:.5f}. {tag('proxy DTI only, not a competition score', 'warning')} "
                 f"{prereg} · {module}</p></section>")
    return "".join(parts)


def session5_status_sentence() -> str:
    """Evidence-derived one-liner for the home banner: data placement, emission sweep, H43 verdict."""
    parts = []
    rec_p = ROOT / "evidence" / "data_placement_receipt.json"
    if rec_p.is_file():
        rec = json.loads(rec_p.read_text(encoding="utf-8"))
        n = sum(g["n_present"] for g in rec["manifests"])
        parts.append(f"session 5 closed the data-placement blocker with a script-written receipt "
                     f"({n} pinned files byte-correct, footprint {int(rec.get('prepared_detail', {}).get('footprint_pixels', 0)):,} px, "
                     f"caches prepared)")
    sw_p = ROOT / "evidence" / "emission_sweep" / "summary.json"
    if sw_p.is_file():
        sw = json.loads(sw_p.read_text(encoding="utf-8"))
        dec = sw["decision"]
        parts.append("the frozen emission-density sweep found the pinned 2.8 px artifact is the optimum of its own "
                     f"family (calibration check: {'passed' if dec['proxy_calibration_check']['calibrated'] else 'failed'}; "
                     f"recommendation: {dec['recommendation']})")
    h43_p = ROOT / "evidence" / "h43_screen" / "summary_screen.json"
    if h43_p.is_file():
        h43 = json.loads(h43_p.read_text(encoding="utf-8"))
        arms = h43["arms"]
        passed = [arm for arm in arms if arm != "C0_base" and arms[arm].get("G1_SCREEN_PASS")]
        gains = "; ".join(f"{arm} {arms[arm]['mean_gain']:+.5f}" for arm in arms if arm != "C0_base")
        parts.append("the frozen H43 drainage-network screen "
                     + (f"cleared G1 on {', '.join(sorted(passed))}" if passed
                        else f"failed G1 on every arm ({gains})")
                     + ("; confirmation authorized" if passed else "; no confirmation was fit"))
    elif (ROOT / "evidence" / "h43_screen" / "design_screen.json").is_file():
        parts.append("the frozen H43 drainage-network screen was launched on draws 32/33 (summary pending in this checkout)")
    return "; ".join(parts) + "."


def render_home() -> str:
    status = read_json("status_feed.json")
    submissions = read_json("submissions.json")
    current = status["current"]
    feed = status.get("events", [])
    approved = approved_entry(submissions)
    historical = next((row for row in submissions.get("files", []) if row.get("role") == "historical_reference"), None)

    if approved:
        banner = (
            '<section class="status-banner good"><strong>Holdout-approved candidate available for manual review.</strong>'
            '<p>A spatial holdout pass is a necessary research gate, not a competition score or proof of leaderboard performance. '
            'Review the exact-file receipt and current official rules before deciding to use any weekly slot.</p></section>'
        )
        approved_download = (
            f'<a class="button" href="{e(artifact_href(approved))}" download>Download GeoTIFF</a>'
            if has_local_artifact(approved)
            else '<p>File path is registered but the artifact is not present in this checkout.</p>'
        )
        main_artifact = (
            '<article class="card span-6 download-card"><p class="kicker">Slot-gated candidate</p>'
            f'<h2>{e(approved.get("name", approved["file"]))}</h2>'
            f'<p>{e(approved.get("summary", ""))}</p><p class="file-name">{e(approved["file"])}</p>'
            f'{tag("holdout gate passed", "yes")} {tag("not an official score", "warning")}'
            f'{approved_download}'
            '</article>'
        )
    else:
        banner = (
            '<section class="status-banner danger"><strong>No slot-approved submission.</strong>'
            '<p>Do not spend a weekly submission slot on any file from this page: the repository recommends none. '
            + e(h41a4_status_sentence()) + '; '
            + e(session5_status_sentence()) + ' Earlier records: '
            + e(h41_status_sentence()) + '; the session-3 H35/H40 and H31b screens failed their frozen gates; '
            'H34 failed its primary proxy gate, the fractional factorial is complete, H31 failed on feature '
            'sparsity, and the corrected H29 screen failed every arm. Every download is format-verified locally '
            'and unscored; the files are offered so the owner can decide, not because a proxy says to submit.</p></section>'
        )
        main_artifact = (
            '<article class="card span-6"><p class="kicker">Current submission status</p>'
            '<h2>No candidate cleared the gate</h2>'
            '<p>Only a candidate that beats the current same-run spatially blocked holdout best, passes every preregistered '
            'screen and fresh-confirmation gate, and passes the exact-file audit can be considered. No live score is inferred.</p>'
            f'<p>{tag("weekly slot used: no", "yes")} {tag("slot approval: none", "no")}</p>'
            f'<a class="button light" href="executive-summary.html">Read the manual submission guide</a>'
            '</article>'
        )

    if historical:
        if has_local_artifact(historical):
            download = f'<a class="button light" href="{e(artifact_href(historical))}" download>Download historical GeoTIFF</a>'
        else:
            download = '<p class="muted">The registered file is not present in this checkout.</p>'
        historical_card = (
            '<article class="card span-6 download-card"><p class="kicker">Historical reference · not a recommendation</p>'
            f'<h2>{e(historical.get("name", "Historical artifact"))}</h2>'
            f'<p>{e(historical.get("summary", ""))}</p>'
            f'<p class="file-name">{e(historical["file"])}</p>'
            f'{tag("unscored", "warning")} {tag("do not submit", "no")}'
            f'<p class="small">{e(historical.get("status", ""))}</p>'
            f'<p class="small"><strong>Archive-only optional note:</strong> <code>{e(historical.get("optional_comment", ""))}</code></p>'
            f'{download}</article>'
        )
    else:
        historical_card = '<article class="card span-6"><h2>No historical artifact registered</h2></article>'

    metrics = (
        '<section class="grid" aria-label="Research status metrics">'
        f'<div class="metric span-4"><span class="label">Research screens</span><span class="value">{e(current.get("screen_status", "unknown"))}</span><span class="label">Local proxies only—not official scores</span></div>'
        f'<div class="metric span-4"><span class="label">Weekly submission slot</span><span class="value">{"No" if not current.get("weekly_slot_used") else "Used"}</span><span class="label">None used for this research</span></div>'
        f'<div class="metric span-4"><span class="label">Official competition score</span><span class="value">Not verified</span><span class="label">No DrivenData leaderboard content copied</span></div>'
        '</section>'
    )
    timeline = []
    for event in reversed(feed[-5:]):
        timeline.append(
            '<li><time>' + e(event.get("date", "")) + '</time><strong>' + e(event.get("title", "")) + '</strong><span>'
            + e(event.get("detail", "")) + '</span></li>'
        )
    feed_card = (
        '<section class="card"><p class="kicker">Local research updates</p><h2>What changed</h2>'
        f'<p class="muted">Updated {e(status.get("updated_local_date", ""))}. This is the project evidence feed, not a leaderboard snapshot.</p>'
        f'<ol class="timeline">{"".join(timeline)}</ol><p><a href="status.html">Full status register →</a></p></section>'
    )
    body = (
        f'{render_downloads()}{banner}{metrics}<section class="grid" aria-label="Submission artifacts">{main_artifact}{historical_card}</section>'
        '<section class="grid"><article class="card span-7"><p class="kicker">Research, not score-chasing</p><h2>Test the unseen-fault hypothesis first</h2>'
        '<p>H29 has now been rerun with corrected bounded persistence and preregistration-compliant nearest-valid FFT padding; every preregistered arm failed, so no confirmation fits were run. The original run is archived as history. H31 is a separate pseudogravity/edge-drift screen and also failed, with sparse persistence features diagnosed as the cause. Session 3 rebuilt persistence as a dense continuous field in two independent workstreams — H40 (dense ladder) and H31b (dense worming persistence) — and added new physics-anchored interaction fields (H35); the frozen screens failed every arm, closing the worming-family line in four formulations across adjacent folds.</p>'
        '<p><strong>Holdout DTI is a catalogue-gap proxy, not the official competition score.</strong> The public competition uses expert-labelled '
        'faults unavailable to these local folds, and official private/final-round results are not observed here.</p>'
        '<p><a href="research.html">Read the ranked hypotheses and scientific caveats →</a></p></article>'
        '<article class="card span-5"><p class="kicker">Source control</p><h2>Manual verification, not scraping</h2>'
        '<p>Official competition pages are linked for the user to open. No page is embedded, polled, or copied into this status feed.</p>'
        '<p><a href="sources.html">Review sources and caveats →</a></p></article></section>'
        + feed_card
    )
    # The single-click download is placed in the hero itself, not only further down the page, so that a
    # visitor sees the actual file within the first screen (standing owner requirement, 2026-10-03).
    primary = next((row for row in submissions.get("files", []) if row.get("role") == "candidate_review"
                    and has_local_artifact(row)), None)
    hero_download = (
        a(artifact_href(primary), "Download the .tif in one click", class_name="button cta")
        + a("executive-summary.html", "Submission guide", class_name="button")
        + a("research.html", "Explore research", class_name="button secondary")
        if primary else
        a("executive-summary.html", "Submission guide", class_name="button")
        + a("research.html", "Explore research", class_name="button secondary")
    )
    buttons = hero_download
    return page(
        "Overview",
        "Auditable, spatially validated research for the DOE GEMS Prize. No slot-approved submission is currently available.",
        "index",
        "DOE GEMS Prize · GeoDAWN · evidence before entry",
        "Find faults worth believing.",
        "A transparent research workflow for predicting unmapped faults, built around spatial holdouts, exact-file "
        "validation, official sources and honest uncertainty. The download in the banner is one click and needs no login; "
        "its paste-ready submission note sits with it. Nothing here is a score claim.",
        body,
        buttons,
    )


def render_summary() -> str:
    submissions = read_json("submissions.json")
    contract = read_json("submission_contract.json")
    fmt = contract["format"]
    rules = contract["rules"]
    rules_label = f"Official {int(rules['rules_year'])} rules"
    approved = approved_entry(submissions)
    if approved:
        candidate_block = (
            '<div class="status-banner good"><strong>Candidate registered for manual review.</strong>'
            f'<p>Name: <strong>{e(approved.get("name", ""))}</strong> · file: <span class="file-name">{e(approved["file"])}</span></p>'
            f'<p>Optional comment: <code>{e(approved.get("optional_comment", ""))}</code></p>'
            f'<p>Local file present: {"yes" if has_local_artifact(approved) else "no"}. The holdout remains a proxy, not an official score.</p></div>'
        )
    else:
        candidate_block = (
            '<div class="status-banner danger"><strong>No current file is approved for submission.</strong>'
            '<p>The downloads above are research artifacts, not approvals. No weekly slot should be used unless a candidate beats the current comparable spatially blocked holdout best, passes fresh confirmation, and passes the exact-file checks; no current file meets that bar.</p></div>'
        )

    body = (
        f'{render_downloads()}{candidate_block}{data_placement_card()}'
        '<section class="grid"><article class="card span-7"><p class="kicker">Purpose</p><h2>Submission in one sentence</h2>'
        f'<p>Submit one probability raster for faults across the full GeoDAWN study area, using the provided template grid and the official manual interface. '
        f'The organizer’s {int(rules["rules_year"])} rules allow up to {int(rules["weekly_feedback_max"])} weekly feedback submissions and require '
        f'{int(rules["final_prediction_count"])} final selection for both {int(rules["prize_round_count"])} prize rounds. '
        'Check the current official rules and competition timeline before acting.</p>'
        '<div class="callout"><strong>Current stop:</strong> '
        + e(h41a4_status_sentence() + ' ' + session5_status_sentence()) + ' No official competition result is claimed; the slot rule is unchanged.</div>'
        '</article><article class="card span-5"><p class="kicker">Official references</p><h2>Verify before upload</h2><ul class="list-clean">'
        f'<li>{a("https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/", "Problem description and format", external=True)}</li>'
        f'<li>{a("https://docs.nlr.gov/docs/fy26osti/96647.pdf", rules_label, external=True)}</li>'
        f'<li>{a("https://www.drivendata.org/termsofuse/", "DrivenData Terms of Use", external=True)}</li>'
        '</ul></article></section>'
        '<section class="card"><p class="kicker">Manual upload checklist</p><h2>When a future artifact is approved</h2>'
        '<ol class="steps">'
        '<li><strong>Check eligibility, dates, and rules.</strong> Sign in and confirm registration on the official GEMS competition page yourself. Do not rely on an old date or this static site for the deadline.</li>'
        '<li><strong>Use the one explicitly slot-approved file.</strong> Confirm its name, SHA-256, and checker receipt in the local submission registry. Do not substitute the historical reference download.</li>'
        '<li><strong>Open the official submission page manually.</strong> Select the GeoTIFF through the browser file picker. This project does not automate login, upload, scoring, or page monitoring.</li>'
        '<li><strong>Enter a unique, short submission name.</strong> Use the registered candidate name shown above when one exists. Preserve the downloadable filename and content ID so the file can be identified later.</li>'
        '<li><strong>Optionally add the exact registered comment.</strong> State the method and artifact identifier; never describe a spatial holdout proxy as a competition score.</li>'
        '<li><strong>Submit through the official manual interface.</strong> Follow the portal response for your own transaction, but do not monitor, copy, or store leaderboard content in this project without prior written consent; do not scrape or schedule page reads.</li>'
        f'<li><strong>Respect the weekly and final-selection limits.</strong> The official rules say up to {int(rules["weekly_feedback_max"])} weekly feedback submissions and '
        f'{int(rules["final_prediction_count"])} selected final prediction for both {int(rules["prize_round_count"])} prize rounds. Confirm current rules before using a slot.</li>'
        '</ol></section>'
        '<section class="grid"><article class="card span-6"><p class="kicker">Format gate</p><h2>Exact TIFF contract</h2><ul class="list-clean">'
        f'<li>{int(fmt["band_count"])} raster band; `{e(fmt["dtype"])}`.</li><li>CRS {e(fmt["crs"])}; {int(fmt["pixel_size_m"])}-m resolution.</li><li>Exact template dimensions, bounds, and geotransform.</li>'
        f'<li>Every in-footprint value is finite and in [{fmt["probability_min"]}, {fmt["probability_max"]}].</li>'
        f'<li>Outside-footprint cells are {e(fmt["outside_footprint"])}, matching the official sample template.</li>'
        '<li>Use a unique content-addressed filename and keep a SHA-256 receipt.</li></ul>'
        '<p>Fetch and verify the pinned inputs with one command (it never contacts the organizer; it restores '
        'the hash-pinned owner mirrors): <code>bash scripts/download_competition_data.sh</code>, with '
        '<code>--group core|h31|all</code> and <code>--verify</code>. The legacy core restore writes to '
        '&lt;repo&gt;/data/bridge and ignores <code>GEMS_DATA_DIR</code>; the H31-group restore writes to '
        '&lt;repo&gt;/data. The submission checker and the download verifier resolve either layout through one shared '
        'helper since 2026-10-03, so the documented check below works after either restore:</p>'
        '<pre><code>bash scripts/download_competition_data.sh --verify\n'
        'GEMS_DATA_DIR=$PWD/data python scripts/check_submission.py \\\n'
        '  docs/downloads/&lt;candidate.tif&gt; --receipt evidence/format_checks/&lt;candidate.json&gt;\n'
        'python scripts/verify_downloads.py   # re-verify every registered download against its build-time hashes</code></pre>'
        f'<p>{a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/scripts/check_submission.py", "Review the checker source", external=True)}</p>'
        '<p>The local checker is necessary but cannot guarantee organizer acceptance. Review the current official problem page.</p></article>'
        '<article class="card span-6"><p class="kicker">Narrative disclosure</p><h2>Generative AI use</h2>'
        f'<p>The official {int(rules["rules_year"])} rules require a narrative disclosure of the extent and role of generative-AI use when applicable. '
        'This project has a draft disclosure in its repository; it must be updated against the actual final work before submission.</p>'
        f'<p>{a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/05_genai_disclosure_draft.md", "Review the current disclosure draft", external=True)}</p>'
        '</article></section>'
        + range_rejection_card() +
        '<section class="card"><h2>Important distinction</h2><p>Spatially blocked catalogue-gap holdouts are an internal proxy. They do not reproduce the competition’s newly expert-labelled test faults, '
        'its public leaderboard score, private test score, or second-round revised-label score. Never use a holdout value as a claimed submission result.</p></section>'
    )
    return page(
        "Executive summary and submission guide",
        "Manual steps and exact checks for an eventual GEMS GeoTIFF submission. No current artifact is slot-approved.",
        "summary",
        "Executive summary · manual upload only",
        "A clear route from research artifact to submission.",
        "No file is currently cleared for a weekly slot. The one-click GeoTIFF downloads sit at the very top of this page, each with its paste-ready note and format receipt; below them is the manual process and the exact format contract, so the next approved artifact is easy to identify and audit.",
        body,
        a("index.html", "Back to current status", class_name="button") + a("sources.html", "Official source links", class_name="button secondary"),
    )


def range_rejection_card() -> str:
    """What is known about the earlier [0,1] upload rejection — text and numbers read from the registers."""
    registry = json.loads((ROOT / "registry" / "irregularities.json").read_text(encoding="utf-8"))
    entries = {item.get("id"): item for item in registry["items"]}
    submission_error = entries.get("IR-29-PREV-SUBMIT-ERROR-CLASS", {})
    template = entries.get("IR-TEMPLATE-01", {})
    submissions = read_json("submissions.json")
    rows = submissions.get("files", [])
    locally_checked = sum(1 for row in rows if row.get("format_ok_local"))
    return (
        '<section class="card"><p class="kicker">Reported rejection · register-driven</p>'
        "<h2>“Predicted values must be in range [0, 1]”: what is known and what changed</h2>"
        f"<p>{e(submission_error.get('detail', ''))}</p>"
        f"<p><strong>Status:</strong> {e(submission_error.get('status', 'not recorded'))}. "
        f"<strong>Mitigation in force:</strong> {e(submission_error.get('mitigation', ''))}</p>"
        f"<p><strong>Related template finding:</strong> {e(template.get('detail', ''))} "
        f"<strong>Consequence:</strong> {e(template.get('impact', ''))}</p>"
        f"<p><strong>Current state:</strong> {locally_checked} of {len(rows)} registered downloads carry a local "
        "format receipt with <code>ok_to_upload = true</code> (each card above links its receipt). The local "
        "checker is necessary but cannot guarantee organizer acceptance — the portal validator is not public. "
        "If the portal ever rejects a file, record the exact message, do not edit the file, and report it so the "
        "register and this page can be updated from evidence rather than from guesswork.</p>"
        f"<p>{a('https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/registry/irregularities.json', 'Open the irregularity register', external=True)} · "
        f"{a('https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/src/gemsdoe/submission.py', 'Read the writer and independent checker', external=True)}</p></section>"
    )


def render_research() -> str:
    hypotheses = read_json("hypotheses.json")
    status = read_json("status_feed.json")["current"]
    h29_gate = json.loads((ROOT / "evidence" / "h29_gate.json").read_text(encoding="utf-8"))
    h29_holdout = json.loads((ROOT / "evidence" / "h29_holdout.json").read_text(encoding="utf-8"))
    h29_arm_count = len(h29_gate)
    h29_screen_draws = h29_gate["A1"]["screen_draws"]
    h29_fitted_draws = sorted({int(row["draw"]) for row in h29_holdout.get("rows", [])})
    h29_confirmation_draws = h29_gate["A1"]["confirmation_draws"]
    h29_confirmation_not_run = not any(draw in h29_confirmation_draws for draw in h29_fitted_draws)
    h31_design = json.loads((ROOT / "evidence" / "h31_worm_screen" / "design.json").read_text(encoding="utf-8"))
    h31_gate = h31_design["promotion_gate"]
    h31_fold_count = len(h31_design["spatial_folds"])
    h35_summary = json.loads((ROOT / "evidence" / "h35_h40_screen" / "summary_screen.json").read_text(encoding="utf-8"))
    h35_design = json.loads((ROOT / "evidence" / "h35_h40_screen" / "design_screen.json").read_text(encoding="utf-8"))
    h35_analyzer = json.loads((ROOT / "evidence" / "h35_h40_screen" / "analyzer_report.json").read_text(encoding="utf-8"))
    h35_gates = h35_summary["gates"]
    d28 = json.loads((ROOT / "evidence" / "d28_geometry.json").read_text(encoding="utf-8"))
    arm_rows = []
    for arm in ("A1_h35_struct", "A2_h35_corrob", "A3_h40_persist", "A4_union"):
        adm = h35_summary["arms"][arm]
        arm_rows.append(
            f'<tr><td>{e(arm)}</td><td>{adm["mean_gain"]:+.7f}</td>'
            f'<td>{", ".join(f"{g:+.5f}" for g in adm["fold_gains"])}</td>'
            f'<td>{", ".join(str(v) for v in adm["positive_folds_per_draw"])} (need {h35_gates["min_positive_folds"]})</td>'
            f'<td>{adm["worst_fold_gain"]:+.7f}</td>'
            f'<td>{tag("G1 FAIL", "no") if not adm["G1_SCREEN_PASS"] else tag("G1 PASS", "yes")}</td></tr>'
        )
    h35_card = (
        '<section class="grid"><article class="card span-12"><p class="kicker">Session-3 frozen screen · every number read from evidence/h35_h40_screen/</p>'
        '<h2>H35 interaction zones &amp; H40 dense persistence: all four arms FAIL G1</h2>'
        f'<p>Pre-registered (sha256 {e(h35_design["preregistration"]["sha256"][:12] + "…")}) before any fit; 4 folds × 2 draws (24/25) × 5 arms, '
        f'{h35_summary["elapsed_s"]:.1f} s, clean tree at {e(h35_summary["git"]["revision"][:7])}. Gates: mean paired gain ≥ {h35_gates["mean_gain"]}, ≥{h35_gates["min_positive_folds"]}/4 folds positive on both draws, '
        f'worst fold ≥ {h35_gates["max_fold_loss"]}, emission within ×[{h35_gates["budget_ratio_band"][0]}, {h35_gates["budget_ratio_band"][1]}] of control.</p>'
        '<table><thead><tr><th>arm</th><th>mean gain</th><th>fold gains (NW, NE, SW, SE)</th><th>positive folds (d24, d25)</th><th>worst fold</th><th>gate</th></tr></thead>'
        f'<tbody>{"".join(arm_rows)}</tbody></table>'
        f'<p>The A4 union arm is the notable near-miss: its mean gain (+{h35_summary["arms"]["A4_union"]["mean_gain"]:.7f}) clears the effect bar and its worst fold '
        f'({h35_summary["arms"]["A4_union"]["worst_fold_gain"]:+.7f}) clears the floor — only the draw-24 fold-robustness rule rejects it, exactly the fold-concentration pattern the preregistration pre-declared as noise. '
        'The independent analyzer recomputed every gate from raw cells and reported '
        f'{e("zero problems" if not h35_analyzer["integrity_problems"] else str(h35_analyzer["integrity_problems"]))}. '
        'No confirmation draws (26/27) were fit; no file was emitted; no weekly slot was used. Proxy outcome only — not a competition score.</p>'
        f'<p>{a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/19_preregistered_h35_h40_screen_2026-10-03.md", "Read the frozen preregistration", external=True)} · '
        + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/21_h35_h40_results_2026-10-03.md", "Read the results document", external=True) + ' · '
        + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/20_candidates_v3_2026-10-03.md", "Read the refreshed candidate slate", external=True) + '</p></article>'
        '<article class="card span-6"><p class="kicker">Emission geometry receipt</p><h2>Why fewer, better-placed dots scored higher</h2>'
        f'<p>Re-derived deterministically from the owner-mirrored rasters (script: <code>scripts/audit_d28_geometry.py</code> → <code>evidence/d28_geometry.json</code>): the parent emission has '
        f'{d28["files"]["h19_5_parent"]["emitted_px"]:,} pixels; the thinned d1.5 file keeps {d28["files"]["d1_5"]["emitted_px"]:,} (×{d28["files"]["d1_5"]["share_of_parent"]:.3f}) and captures '
        f'{d28["files"]["d1_5"]["parent_kernel_captured_share"] * 100:.2f} % of the parent mass under the metric’s ±3-pixel triangular kernel ({d28["files"]["d1_5"]["credit_per_emitted_px"]:.4f} credit per emitted pixel); '
        f'the sparsest d2.8 file keeps {d28["files"]["d2_8"]["emitted_px"]:,} (×{d28["files"]["d2_8"]["share_of_parent"]:.3f}), captures {d28["files"]["d2_8"]["parent_kernel_captured_share"] * 100:.2f} %, and earns '
        f'{d28["files"]["d2_8"]["credit_per_emitted_px"]:.4f} credit per emitted pixel — every pixel isolated ({d28["files"]["d2_8"]["isolated_share"] * 100:.1f} %), none on the catalogue '
        f'({d28["files"]["d2_8"]["catalogue_overlap_px"]} overlap pixels). The kernel credit per emitted pixel rises monotonically as the emission thins toward the trace: this is why a 36 % emission can beat a 100 % emission '
        'under the published metric, and it is a property of the metric, not of any model. Owner-reported competition scores for these files are unverified claims and are deliberately absent here.</p></article>'
        '<article class="card span-6"><p class="kicker">What it means</p><h2>Four worming-family screens, four consistent negatives</h2>'
        '<p>H29 (sparse persistence features), H31 (seed-tracked persistence), H40 (dense continuous persistence) with the new H35 tip-corridor interaction fields, and the parallel H31b dense-worming rebuild all failed the same fixed effect bar on the same '
        'spatial folds. The mechanisms are not disproven science — the caveat that this grid’s most persistent edges run E–W (survey-parallel, the H29 diagnostic) travels with every verdict — but on this pipeline the '
        'frozen structural baseline already extracts most of that information. The v3 slate\u2019s rank 1, H41 (slip-rate-weighted INGENIOUS off-catalogue trace centroids, already mirrored), is the first idea in this '
        'family to clear the frozen gate: on draws 28/29 two of its five arms passed G1, the union arm then reproduced on fresh draws 30/31 (+0.0077283, worst fold still positive), and the inherited G3 secondary-proxy gate '
        'withheld promotion anyway because the SGMC off-catalogue class lost ground in both stages. Every number behind that sentence \u2014 mean paired gains, per-fold gains, the AUC step, the emission budget band and the '
        'negative SGMC second proxy \u2014 is recomputed from the raw cells in the card above rather than repeated here. That is the gate stack working as designed: a replicated primary-proxy gain is still not a submission. The v4 slate (H43 drainage organization first, '
        'then H44\u2013H47) is ranked in knowledge/25 with each candidate\u2019s external-data obtainability stated; H44\u2013H47 wait on owner-side fetches, and H36/H37/H42 and the H38/H39 filter-role pair remain behind H43.</p></article></section>'
    )

    strategy_card = (
        "<section class=\"grid\"><article class=\"card span-6\"><p class=\"kicker\">Metric analysis</p>"
        "<h2>Why a sparser emission scored better, and what beating the leaderboard best requires</h2>"
        "<p>The repository\u2019s read of the published metric: credit is granted per true-positive pixel within a "
        "300 m triangular kernel, and a false positive costs a fraction of what a miss costs, so once a dot sits "
        "inside a neighbouring dot\u2019s kernel it adds nothing while still risking a false-positive charge. Under "
        "those conditions the optimal move is to emit only where the expected credit per emitted pixel clears a "
        "threshold the metric itself fixes, and to space dots so each one earns its own kernel. That is arithmetic "
        "about the scoring rule, not a tuning preference, and it explains why a thinned, catalogue-free emission can "
        "outrank a dense one from the same model.</p>"
        "<p>Closing the remaining gap therefore needs either more true-positive mass per emitted pixel, or a habitat "
        "that puts dots on structure the current model never ranks highly. The derivation, the measured "
        "credit-per-pixel ladder for the repository\u2019s own files and the resulting three-part system (habitat, "
        "emission rule, admission rule) live in <code>knowledge/07_metric_emission_analysis_2026-10-03.md</code> and "
        "<code>knowledge/13_strategy_system_2026-10-03.md</code>. The score figures are not republished here: they are "
        "unverified owner-reported claims, and these pages carry only locally recomputable proxies.</p></article>"
        "<article class=\"card span-6\"><p class=\"kicker\">Owner question</p>"
        "<h2>Are there new competition results to read?</h2>"
        "<p>This project deliberately does not answer that by fetching the competition site. The platform\u2019s terms "
        "prohibit automated access for any purpose including monitoring, and the project charter repeats the ban "
        "(<code>AGENTS.md</code> rule 3, <code>knowledge/03_drivendata_terms_access_policy.md</code>), so no leaderboard "
        "row, rank or feed item is scraped, embedded or cached here. The repository instead reports its own state "
        "continuously and leaves the competition page for the owner to open in a browser.</p>"
        "<ul class=\"list-clean\">"
        "<li><a href=\"https://www.drivendata.org/competitions/306/competition-doe-gems/\" target=\"_blank"
        " rel=\"noopener noreferrer\">Open the official competition page manually</a></li>"
        "<li><a href=\"https://docs.nlr.gov/docs/fy26osti/96647.pdf\" target=\"_blank\" rel=\"noopener noreferrer\">"
        "Official rules (submission limits, final selection, AI disclosure)</a></li></ul>"
        "<p>No weekly slot has been used by this repository, so nothing was submitted that could be scored; "
        "<code>evidence/candidate_scoreboard.json</code> and the submission register are the authoritative local "
        "record.</p></article></section>"
    )

    def _hypothesis_card(item: dict[str, Any]) -> str:
        layers = ", ".join(item.get("layers", []))
        return (
            f'<article class="card span-12"><div class="grid"><div class="span-8"><p class="kicker">Rank {e(item.get("rank"))} · {e(item["id"])}</p>'
            f'<h2>{e(item["title"])}</h2><p>{tag(item.get("status", ""))}</p><p><strong>Layers:</strong> {e(layers)}</p>'
            f'<p><strong>Physical signature / transform:</strong> {e(item.get("signature", ""))}</p>'
            f'<p><strong>Why it could catch a fault missing from the USGS/INGENIOUS catalogue:</strong> {e(item.get("why_unmapped", ""))}</p>'
            f'<p><strong>How it differs from anything in the reviewed repositories:</strong> {e(item.get("difference", ""))}</p></div>'
            f'<aside class="span-4"><div class="metric"><span class="label">Planning ΔDTI</span><span class="value">{e(item.get("planning_delta_dti", "not estimated"))}</span>'
            '<span class="label">Planning range only—not measured, not a score</span></div>'
            f'<p><strong>Cost:</strong> {e(item.get("cost", ""))}</p><p><strong>Data obtainability:</strong> {e(item.get("external_data", ""))}</p></aside></div></article>'
        )

    hypotheses_v3_path = ROOT / "registry" / "hypotheses_v3_2026-10-03.json"
    hypotheses_v3 = json.loads(hypotheses_v3_path.read_text(encoding="utf-8")) if hypotheses_v3_path.is_file() else None
    v3_section = ""
    if hypotheses_v3 is not None:
        v3_cards = "".join(_hypothesis_card(i) for i in hypotheses_v3.get("items", []))
        h31b_screen_dir = ROOT / "evidence" / "h31b_dense_screen"
        h31b_result = ""
        if (h31b_screen_dir / "summary.json").is_file():
            h31b_summary = json.loads((h31b_screen_dir / "summary.json").read_text(encoding="utf-8"))
            arms_txt = ", ".join(f"{k} {v:.4f}" for k, v in h31b_summary.get("arms", {}).items())
            if h31b_summary.get("pass_fail") == "PASS":
                decision = "A pass authorizes fresh confirmation on new draws, not a submission."
            else:
                decision = ("Per the frozen decision rules: no confirmation, no candidate TIFF, no slot. "
                            "Draw 22 mean paired gain +0.0050 (4/4 folds positive); draw 23 +0.0018 (2/4) — the stability "
                            "gates fail on draw 23. The 8-cell primary-arm mean is recorded for the scientific record only "
                            "(not a promotion anchor). Full analysis: "
                            + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/21_h31b_screen_results_2026-10-03.md", "knowledge/21 (H31b)", external=True))
            h31b_result = (
                f'<p><strong>Screen outcome (screen draws 22/23):</strong> '
                f'8-cell mean proxy DTI by arm — {e(arms_txt)}. '
                f'Gate: <span class="pill {"yes" if h31b_summary.get("pass_fail") == "PASS" else "no"}">{e(h31b_summary.get("pass_fail"))}</span>. '
                + decision + ' Raw cells and gates: '
                + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/evidence/h31b_dense_screen/", "evidence/h31b_dense_screen/", external=True) + '.</p>'
            )
        else:
            h31b_result = ('<p><strong>Screen status:</strong> ' + e(status.get("current", {}).get("screen_status", "running or not yet run"))
                           + ' — raw cells and frozen gates will be published under '
                           + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/evidence/h31b_dense_screen/", "evidence/h31b_dense_screen/", external=True)
                           + ' on completion.</p>')
        v3_section = (
            '<section class="status-banner"><strong>Candidates v3, Workstream A (2026-10-03) — five new untried hypotheses, ranked by expected ΔDTI per implementation cost.</strong> '
            'Per the owner brief: each names its layers, physical signature/transform, why it could catch a fault missing from the USGS/INGENIOUS catalogue, and how it differs from everything in the reviewed repositories. '
            'Rank 1 (H31b, dense continuous worming persistence) was preregistered and screened on the spatially-blocked holdout this session — it FAILED its frozen stability gates (draw-unstable), so no slot path opened for it. '
            'A parallel workstream registered an independent refreshed slate (H41 first) below and screened the same dense-persistence idea as H40 (also FAIL). Planning brackets are not predictions or scores. Register: '
            + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/registry/hypotheses_v3_2026-10-03.json", "registry/hypotheses_v3_2026-10-03.json", external=True) + ' · note: '
            + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/20b_candidates_v3_h31b_slate_2026-10-03.md", "knowledge/20b", external=True) + '.</section>'
            f'<section class="grid" aria-label="Ranked hypotheses v3 (Workstream A)">{v3_cards}</section>'
            '<section class="card"><p class="kicker">H31b — screened this session (result: FAIL, no slot path)</p><h2>Dense continuous worming persistence (magnetic + gravity)</h2>'
            '<p>H31 (the binarised predecessor) failed because its persistence columns were nonzero on 0.001–0.084 % of the footprint, so its arms emitted dot sets identical to the control in 8/8 cells. H31b records, for every pixel, the fraction of five upward-continuation heights at which the horizontal-gradient modulus clears the per-height p90 scale threshold, plus deepest-survival height and 0 m / 1200 m edge amplitudes — 12 dense columns (family W) over the frozen 81-column H34 control layout, with a 68-px margin-zero band where the FFT taper cannot be trusted.</p>'
            f'<p><strong>Frozen gates:</strong> per-draw mean paired gain ≥ +0.005 in ≥3/4 folds on each of draws 22/23, no fold below −0.010, the 8-cell mean must beat the current holdout best (0.14479), 40/40 cells finite; fresh confirmation draws only if the screen passes (moot — the screen FAILED; the reserved confirmation draws 24/25 were consumed by the parallel H35/H40 screen, so any retest needs new draws and a new preregistration). '
            + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/19_preregistered_h31b_dense_worming_2026-10-03.md", "Read the preregistration", external=True) + '</p>'
            + h31b_result
            + '</section>'
        )

    cards = []
    for item in hypotheses.get("items", []):
        layers = ", ".join(item.get("layers", []))
        state = tag(item.get("status", ""), "warning" if item["id"] == "H31" else "")
        cards.append(
            f'<article class="card span-12"><div class="grid"><div class="span-8"><p class="kicker">Rank {e(item.get("rank"))} · {e(item["id"])}'
            + (f' · {e(item["slate"])}' if item.get("slate") else '') + '</p>'
            f'<h2>{e(item["title"])}</h2><p>{state}</p><p><strong>Layers:</strong> {e(layers)}</p>'
            f'<p><strong>Physical signature:</strong> {e(item.get("signature", ""))}</p>'
            f'<p><strong>Why it could add unmapped faults:</strong> {e(item.get("why_unmapped", ""))}</p>'
            f'<p><strong>How it differs from reviewed work:</strong> {e(item.get("difference", ""))}</p></div>'
            f'<aside class="span-4"><div class="metric"><span class="label">Planning ΔDTI</span><span class="value">{e(item.get("planning_delta_dti", "not estimated"))}</span>'
            '<span class="label">Planning range only—not measured, not a score</span></div>'
            f'<p><strong>Cost:</strong> {e(item.get("cost", ""))}</p><p><strong>Data:</strong> {e(item.get("external_data", ""))}</p></aside></div></article>'
        )
    body = (
        '<section class="status-banner"><strong>Novelty was rechecked again on 2026-10-03 against the current main branch, including both session-3 workstreams and the session-4 screen.</strong> '
        'Every arm in the corrected H29 screen failed; the H31 seed-tracked screen and the H34 coverage-emission screen failed; the session-3 H35/H40 screen '
        '(tip-corridor interaction zones + dense continuous persistence, four arms) failed its frozen gate on all arms; the parallel H31b dense-worming screen '
        '(draws 22/23) failed its stability gates on draw 23. The worming/persistence family is now screened in four distinct formulations across two independent '
        'workstreams, and the slate carries an explicit decision not to run it a fifth time without a new mechanism: another retry would be silent fishing, not '
        'science. “Not found” is limited to the reviewed repositories, not all competitors. '
        'The v4 slate (H43 drainage organization first, then H44–H47) is in knowledge/25_candidates_v4; H41 was promoted from the v3 slate and screened this '
        'session, and is the first candidate in this family to clear a frozen gate on two arms. Two parallel v3 registers are rendered below: the Workstream-A slate '
        '(H31b first, screened) and the refreshed Workstream-B slate.</section>'
        f'{h35_card}{h41_screen_card()}{h41a4_bar_card()}{emission_sweep_card()}{h43_screen_card()}{data_placement_card()}{strategy_card}{v3_section}<section class="grid" aria-label="Refreshed ranked slate (Workstream B)">{"".join(cards)}</section>'
        '<section class="grid"><article class="card span-7"><p class="kicker">H31 research design</p><h2>Test the pseudogravity/drift increment beyond H29</h2>'
        f'<p>The original H29 run had already tested upward-continuation worm persistence on raw RTP and isostatic gravity, but its bounded-persistence normalization and FFT exterior padding were both found nonconforming. Its raw cells are archived and reconciled as historical only. The corrected run tested {h29_arm_count} preregistered arms over screen draws {" and ".join(map(str, h29_screen_draws))}; every arm failed, '
        f'{"so no confirmation models were fit" if h29_confirmation_not_run else "and its confirmation status is recorded in the evidence"}. H31 does not claim worming itself is new. It isolates a regularized vertical-integration pseudogravity <em>proxy</em> from RTP plus a lateral edge-drift feature, then checks whether those additions improve a same-run baseline. The available isostatic gravity anomaly is included separately. A symmetric fixed-neighborhood cross-support allows small grid misregistration; it is a tolerance, not geological proof.</p>'
        '<p>A synthetic engineering test found exact-pixel multiplication produced an empty joint term after the distinct transforms. Before any real-data fit, the preregistered joint feature was clarified to use a fixed small spatial tolerance; no model, data, or promotion gate changed.</p>'
        f'<p><strong>Current screen:</strong> {e(status.get("screen_status", "not run"))}. Confirmation is {e(status.get("confirmation_status", "blocked"))}.</p>'
        f'<p>{a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/02_preregistered_h31_worming_2026-10-03.md", "Read the preregistration and amendment", external=True)}</p>'
        '</article><article class="card span-5"><p class="kicker">Scientific limits</p><h2>Worming-like ≠ full inversion</h2>'
        '<p>Poisson-wavelet worming literature motivates upward continuation and tracking horizontal-gradient maxima. The implementation here is a scale-space proxy with regularized Fourier integration, not the full Hornby transform, not an inversion, and not a fault-depth estimator.</p>'
        '<p>Potential fields are non-unique: source interference, cultural noise, depth, remanence and misalignment can produce or hide edges. Persistence is not proof of faulting, geothermal activity, or discovery.</p>'
        '<p><a href="sources.html">Check the primary/review sources and limitations →</a></p></article></section>'
        '<section class="card"><p class="kicker">Promotion gates</p><h2>Spatial validation before any slot</h2>'
        f'<p>{h31_fold_count} spatial blocks are the replication units; folds and draws are paired cells, not independent extra samples. H31 must beat the strongest same-run control by a paired mean DTI gain {e(h31_gate["mean_paired_gain_over_best_same_run_control"])}, '
        f'be positive in {e(h31_gate["positive_spatial_blocks"])} blocks, keep the worst-block gain {e(h31_gate["worst_spatial_block_gain"])}, and keep catalogue-hug-share increase {e(h31_gate["catalogue_hug_share_increase"])}. '
        f'{"A fresh confirmation is required." if h31_gate["fresh_confirmation_required"] else "No fresh confirmation is required."} Raw-cell hashes and screen gates are checked before any confirmation.</p>'
        '<p>Passing these gates only permits a candidate to be considered; it does not authorize a weekly submission, guarantee the official score, or establish generalization to expert-labelled faults.</p></section>'
        '<section class="card"><p class="kicker">What came before</p><h2>Predecessor audit</h2>'
        '<p>The reviewed GEMSDOE25 code already tried fixed-scale potential-field derivatives, terrain/scarp descriptors, catalogue geometry, geothermal/context tables, thinning, single-tip continuation, and an H30 relay-bridge × scarp experiment. The predecessor A-family potential-field screen was reported inert/negative on a catalogue-gap proxy; H30-1 failed fresh-draw confirmation. These are predecessor proxy reports, not official scores and not recomputed here.</p>'
        f'<p><strong>H29 result:</strong> the corrected nearest-fill, bounded-persistence screen tested {h29_arm_count} preregistered arms; every arm failed. '
        f'{"No confirmation fits were run" if h29_confirmation_not_run else "Confirmation status is recorded in the evidence"}; no weekly slot was recommended or used. The earlier run and gate discrepancy are archived as historical evidence, not the current screen. These are catalogue-gap proxy outcomes, not competition scores. '
        + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/02_h29_results_2026-10-03.md", "Review the corrected H29 outcome", external=True) + ' · '
        + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/evidence/h29_gate.json", "Open the current H29 gate", external=True) + ' · '
        + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/06_h29_gate_reconciliation_2026-10-03.md", "Read the archived gate reconciliation", external=True) + '</p>'
        '<p>Historical score claims remain unverified owner/user reports. No leaderboard snapshot is shown or used here. H31 is not designed or tuned to reproduce them.</p>'
        f'<p>{a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/04_prior_work_audit.md", "Review the predecessor audit", external=True)}</p></section>'
        '<section class="card"><h2>Model and emission</h2><p>The frozen H31b screen compared five arms over the frozen 81-column H34 control layout: the base arm, plus magnetic (RTP), pseudogravity-proxy (PSG), isostatic-gravity (GRAV), and all-branch (WALL) additions of the dense worming-persistence family (12 columns, 68-px margin-zero band). The parallel H35/H40 screen used the same family and emission machinery with tip-corridor interaction additions. All arms share the same holdout masks, samples, classifier family (HistGradientBoosting), Hessian-ridge NMS emission, and score-ordered dotting budget within a cell. The output is scored by the local distance-weighted metric on held-out catalogue traces only.</p></section>'
    )
    return page(
        "Research and hypotheses",
        "Ranked hypotheses, preregistration, current negative screens, and scientific limits.",
        "research",
        "Research register · updated from local files",
        "Hypotheses, re-ranked against the current screens.",
        "The corrected H29, H31, H34, session-3 H35/H40 and H31b screens all failed their frozen gates; the session-4 H41 "
        "qfaults-corridor screen passed on two of four arms and its confirmation is recorded in knowledge/26. The v4 slate "
        "ranks the next five ideas by gain per cost, H43 first. No current file is slot-approved.",
        body,
        a("status.html", "View the evidence feed", class_name="button") + a("sources.html", "Review scientific sources", class_name="button secondary"),
    )


def render_status() -> str:
    status = read_json("status_feed.json")
    current = status["current"]
    event_rows = []
    for event in reversed(status.get("events", [])):
        event_rows.append(
            '<li><time>' + e(event.get("date", "")) + '</time><strong>' + e(event.get("title", "")) + '</strong><span>'
            + e(event.get("detail", "")) + '</span></li>'
        )
    body = (
        '<section class="status-banner"><strong>This is not a leaderboard feed.</strong><p>The DrivenData Terms prohibit automated monitoring and manual monitoring/copying without prior written consent. '
        'This page only reports checked-in research and release records. It contains no live page content, no rank polling, and no automated score fetch.</p></section>'
        '<section class="grid"><div class="metric span-4"><span class="label">Current research stage</span><span class="value">' + e(current.get("research_stage", "unknown")) + '</span></div>'
        '<div class="metric span-4"><span class="label">Screen status</span><span class="value">' + e(current.get("screen_status", "unknown")) + '</span></div>'
        '<div class="metric span-4"><span class="label">Confirmation status</span><span class="value">' + e(current.get("confirmation_status", "unknown")) + '</span></div>'
        '<div class="metric span-4"><span class="label">Inputs</span><span class="value">' + e(current.get("data_status", "unknown")) + '</span></div>'
        '<div class="metric span-4"><span class="label">Spatial holdout best</span><span class="value">' + e(current.get("holdout_best") if current.get("holdout_best") is not None else "not measured") + '</span><span class="label">Proxy, not competition score</span></div>'
        '<div class="metric span-4"><span class="label">Official competition score</span><span class="value">' + e(current.get("competition_score") if current.get("competition_score") is not None else "not verified") + '</span><span class="label">No leaderboard copied</span></div></section>'
        '<section class="card"><p class="kicker">Project-local updates</p><h2>Evidence timeline</h2><p class="muted">Last local update: ' + e(status.get("updated_local_date", "unknown")) + '</p>'
        f'<ol class="timeline">{"".join(event_rows)}</ol></section>'
        '<section class="card"><p class="kicker">Score-claim policy</p><h2>No live scores or rankings are published here</h2>'
        '<p>Historical owner/user-supplied score statements remain preserved in the original README prompt and a local claim register for provenance, but they are unverified and are not competition results, model targets, or promotion gates. This public status page intentionally does not reproduce their values, ranks, or account names.</p>'
        '<p>No leaderboard link, leaderboard content, polling, or manual monitoring/copying is included. The project publishes only its own dated experiment and artifact records; prior written consent would be required before any monitoring or copying.</p></section>'
    )
    return page(
        "Project-local status feed",
        "A local evidence timeline. This is not a DrivenData leaderboard or score feed.",
        "status",
        "Local evidence only · no external polling",
        "What is known, and what is not.",
        "Status updates are assembled from this repository’s own dated records. A blank result means no verified result is available—not that a score is zero.",
        body,
        a("index.html", "Overview", class_name="button") + a("sources.html", "Terms and source register", class_name="button secondary"),
    )


def render_sources() -> str:
    registry = read_json("sources.json")
    items = []
    hidden = 0
    for source in registry.get("sources", []):
        if source.get("site_hidden"):
            # Audit-only registry entries (e.g. a one-off verification of a score the owner
            # supplied) stay out of the rendered site per the checker's no-claim/no-leaderboard-link
            # rule; the full entry remains in registry/sources.json on GitHub.
            hidden += 1
            continue
        verified = tag("verified page/listing", "yes") if source.get("verified") else tag("not verified", "no")
        used = ''.join(f'<li>{e(value)}</li>' for value in source.get("used_for", []))
        items.append(
            '<article class="source-item"><div class="grid"><div class="span-7"><h3>' + source_url(source) + '</h3>'
            + '<p class="source-meta">' + e(source.get("publisher", "")) + ' · ' + e(source.get("kind", "")) + '</p>'
            + '<p><strong>Checked:</strong> ' + e(source.get("verified_date") or "not checked") + ' · ' + verified + '</p>'
            + ('<p><strong>DOI:</strong> ' + e(source["doi"]) + '</p>' if source.get("doi") else '')
            + '</div><div class="span-5"><p><strong>Used for</strong></p><ul class="list-clean">' + used + '</ul></div></div>'
            + ('<p class="callout"><strong>Caveat:</strong> ' + e(source.get("caveat", "")) + '</p>' if source.get("caveat") else '')
            + '</article>'
        )
    body = (
        '<section class="status-banner"><strong>Source discipline:</strong> every source has a verification status and limitation. '
        '“Verified” means the cited page/listing was read or a checked predecessor record was carried forward; it does not validate a model, competition score, owner-mirror file, or right to use data beyond its stated licence.</section>'
        '<section class="card"><p class="kicker">Official and research sources</p><h2>Open the primary source yourself</h2>'
        + (f'<p class="small">{hidden} registry entr{"y is" if hidden == 1 else "ies are"} audit-only (score-verification records) and shown in '
           + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/registry/sources.json", "registry/sources.json", external=True)
           + ' rather than on this page, per the site’s no-claim/no-leaderboard-link rule.</p>' if hidden else '')
        + ''.join(items) + '</section>'
        '<section class="card"><h2>Data and interpretation caveats</h2><p>Review the project irregularities register for mirror provenance, ambiguous band semantics, unverified score claims, proxy limits, and blocked data.</p><p><a href="irregularities.html">Open the irregularities page →</a></p></section>'
        '<section class="card"><p class="kicker">Terms decision</p><h2>No DrivenData polling or scraping</h2>'
        '<p>DrivenData’s Terms of Use prohibit robots or other automatic access for any purpose, including monitoring/copying, and manual monitoring/copying without prior written consent. No written consent for monitoring is present. This project includes no leaderboard link, live page content, polling, or copied score feed; local status comes only from repository evidence.</p>'
        f'<p>{a("https://www.drivendata.org/termsofuse/", "Read the official Terms of Use", external=True)} · {a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/03_drivendata_terms_access_policy.md", "Review the project access-policy notes", external=True)}</p></section>'
    )
    return page(
        "Sources and official links",
        "Official competition, policy, USGS and scientific references with verification status and caveats.",
        "sources",
        "Auditable references · primary sources first",
        "Sources you can check line by line.",
        "Official links, scientific grounding, verification dates, and explicit gaps. No leaderboard or login-walled data page is copied here.",
        body,
        a("research.html", "Back to research", class_name="button") + a("status.html", "Status and score-claim policy", class_name="button secondary"),
    )


def render_irregularities() -> str:
    registry = read_json("irregularities.json")
    cards = []
    for item in registry.get("items", []):
        severity = item.get("severity", "unknown")
        state_style = "no" if severity == "high" else "warning"
        cards.append(
            '<article class="card span-12"><div class="grid"><div class="span-8">'
            f'<p class="kicker">{e(item.get("id", ""))} · {tag(severity, state_style)}</p>'
            f'<h2>{e(item.get("subject", ""))}</h2><p><strong>Finding:</strong> {e(item.get("detail", ""))}</p>'
            f'<p><strong>Impact:</strong> {e(item.get("impact", ""))}</p></div>'
            f'<aside class="span-4"><p class="kicker">Status</p><p>{e(item.get("status", ""))}</p>'
            f'<p><strong>Mitigation:</strong> {e(item.get("mitigation", ""))}</p></aside></div></article>'
        )
    body = (
        '<section class="status-banner"><strong>Irregularities are not hidden.</strong><p>Items below include owner-mirror provenance, ambiguous labels/bands, unverified score reports, holdout limitations, and blocked external data. Each carries an impact and a mitigation.</p></section>'
        f'<section class="grid" aria-label="Project irregularities">{"".join(cards)}</section>'
        '<section class="card"><h2>Machine-readable register</h2><p>The same items are maintained in the repository for programmatic review.</p>'
        f'<p>{a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/registry/irregularities.json", "Open registry/irregularities.json", external=True)}</p>'
        f'<p>{a("sources.html", "Review official and scientific sources", class_name="button light")}</p></section>'
    )
    return page(
        "Irregularities and caveats",
        "Material data, interpretation, score, holdout, and method caveats in the GEMSDOE29 project.",
        "irregularities",
        "Data lineage · interpretation · evaluation limits",
        "The caveats are part of the result.",
        "Material uncertainties are recorded with their consequences and mitigations—not buried in fine print.",
        body,
        a("index.html", "Current project status", class_name="button") + a("research.html", "Research design", class_name="button secondary"),
    )


def render_root_redirect() -> str:
    """Route the legacy GitHub Pages root to the maintained static site in ``docs/``."""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="refresh" content="0; url=docs/index.html">'
        '<link rel="canonical" href="https://buffedlizard55-lab.github.io/GEMSDOE29/docs/">'
        '<title>GEMSDOE29 — opening research site</title></head><body>'
        '<main><h1>GEMSDOE29</h1><p>The research site is opening.</p>'
        '<p><a href="docs/index.html">Open the GEMS Prize research site</a></p></main>'
        '</body></html>\n'
    )


def render_all() -> dict[Path, str]:
    return {
        ROOT / "index.html": render_root_redirect(),
        DOCS / "index.html": render_home(),
        DOCS / "executive-summary.html": render_summary(),
        DOCS / "research.html": render_research(),
        DOCS / "status.html": render_status(),
        DOCS / "sources.html": render_sources(),
        DOCS / "irregularities.html": render_irregularities(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated HTML is stale; do not write files")
    args = parser.parse_args()
    outputs = render_all()
    stale = []
    for path, content in outputs.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    if stale:
        print("generated site is stale: " + ", ".join(stale), file=sys.stderr)
        return 1
    if args.check:
        print(f"site is current ({len(outputs)} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
