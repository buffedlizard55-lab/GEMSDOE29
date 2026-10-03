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
    candidates = [row for row in submissions.get("files", []) if row.get("role") == "candidate_review"]
    if not candidates:
        return ""
    cards = []
    for row in candidates:
        present = has_local_artifact(row)
        download = (
            f'<a class="button" href="{e(artifact_href(row))}" download>Download GeoTIFF</a>'
            if present
            else '<p class="muted">Registered file is not present in this checkout.</p>'
        )
        zip_path = Path(row["path"]).with_suffix(".zip")
        zip_link = (
            f' <a class="button light" href="{e(zip_path.relative_to("docs").as_posix())}" download>Download .zip</a>'
            if (ROOT / zip_path).is_file()
            else ""
        )
        # Score claims stay in the JSON registry only; public pages must not republish them
        # (tests/test_project_integrity.py::test_public_pages_do_not_republish_score_claims_or_leaderboard_links).
        proxy = tag("score claims kept in registry/score_claims.json", "warning")
        card = (
            '<article class="card span-6 download-card"><p class="kicker">Download-ready research candidate '
            '(not an official score)</p>'
            f'<h2>{e(row.get("name", row["file"]))}</h2>'
            f'<p>{e(row.get("summary", ""))}</p>'
            f'<p class="file-name">{e(row["file"])}</p>'
            f'<p class="small">sha256 <code>{e(str(row.get("sha256", ""))[:16])}…</code> · '
            f'{int(row.get("positive_pixels", 0)):,} emitted px · format ok: {e(row.get("format_ok_local"))}</p>'
            f'{proxy} {tag("unscored", "warning")} {tag("owner decides", "no")}'
            f'<p class="small"><strong>Paste-ready Note:</strong> <code>{e(row.get("optional_comment", ""))}</code></p>'
            f'{download}{zip_link}'
            "</article>"
        )
        cards.append(card)
    return (
        '<section aria-label="Candidate downloads"><p class="kicker">Formatted and waiting for a human decision</p>'
        '<h2>Download the submission GeoTIFF</h2>'
        '<p>Each file below is one band, EPSG:32611, 100 m, template grid, finite values in [0, 1] inside the '
        'footprint, NaN outside, with a script-written format receipt. None of them is a verified competition '
        'score, and the repository does not spend weekly slots: that is the owner\'s decision.</p>'
        f'<section class="grid">{"".join(cards)}</section></section>'
    )


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
            'H34 (metric-native coverage emission) failed its frozen primary gate (catalogue-hidden proxy, &minus;0.021 mean paired gain, 0/4 folds) while passing its secondary off-catalogue class (+0.054, 4/4). '
            'The 2<sup>5&minus;1</sup> fractional factorial over feature families is running. H29 failed all four arms; H31 is unfitted. '
            'Every download is format-verified locally and unscored; the files are offered so the owner can decide, not because a proxy says to submit.</p></section>'
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
        f'<div class="metric span-4"><span class="label">H31 screen</span><span class="value">{e(current.get("screen_status", "unknown"))}</span><span class="label">No holdout outcome claimed</span></div>'
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
        '<p>H29 already tested raw-RTP/gravity worm persistence as a gate, rank and model features; all four arms failed its registered proxy threshold. H31 is a narrower extension: it tests regularized RTP-to-pseudogravity integration and explicit edge drift beyond that prior result. '
        'No H31 model fit or DTI screen has occurred; confirmation remains blocked until a fresh screen passes.</p>'
        '<p><strong>Holdout DTI is a catalogue-gap proxy, not the official competition score.</strong> The public competition uses expert-labelled '
        'faults unavailable to these local folds, and official private/final-round results are not observed here.</p>'
        '<p><a href="research.html">Read the ranked hypotheses and scientific caveats →</a></p></article>'
        '<article class="card span-5"><p class="kicker">Source control</p><h2>Manual verification, not scraping</h2>'
        '<p>Official competition pages are linked for the user to open. No page is embedded, polled, or copied into this status feed.</p>'
        '<p><a href="sources.html">Review sources and caveats →</a></p></article></section>'
        + feed_card
    )
    buttons = a("executive-summary.html", "Submission guide", class_name="button") + a("research.html", "Explore research", class_name="button secondary")
    return page(
        "Overview",
        "Auditable, spatially validated research for the DOE GEMS Prize. No slot-approved submission is currently available.",
        "index",
        "DOE GEMS Prize · GeoDAWN · evidence before entry",
        "Find faults worth believing.",
        "A transparent research workflow for predicting unmapped faults—built around spatial holdouts, exact-file validation, official sources, and honest uncertainty.",
        body,
        buttons,
    )


def render_summary() -> str:
    submissions = read_json("submissions.json")
    status = read_json("status_feed.json")["current"]
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
            '<p>The downloads above are research candidates, not approvals: the historical rebuild matches the group\'s '
            'best-reported geometry and the SGMC inventory alternative loses the registered catalogue-hidden gate. '
            'A weekly slot is the owner\'s decision and needs a fresh confirmation draw plus the exact-file receipt.</p></div>'
        )

    body = (
        f'{render_downloads()}{candidate_block}'
        '<section class="grid"><article class="card span-7"><p class="kicker">Purpose</p><h2>Submission in one sentence</h2>'
        '<p>Submit one probability raster for faults across the full GeoDAWN study area, using the provided template grid and the official manual interface. '
        'The organizer’s 2026 rules require one final selection for both prize rounds; up to three weekly feedback submissions are permitted by the rules. '
        'Check the current official rules and competition timeline before acting.</p>'
        '<div class="callout"><strong>Current stop:</strong> '+ e(status.get("screen_status", "not run")) + '. No H31 holdout score is available; no competition result is claimed.</div>'
        '</article><article class="card span-5"><p class="kicker">Official references</p><h2>Verify before upload</h2><ul class="list-clean">'
        f'<li>{a("https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/", "Problem description and format", external=True)}</li>'
        f'<li>{a("https://docs.nlr.gov/docs/fy26osti/96647.pdf", "September 2026 Official Rules", external=True)}</li>'
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
        '<li><strong>Respect the weekly and final-selection limits.</strong> The official rules say up to three weekly feedback submissions and one selected final prediction for both prize rounds. Confirm current rules before using a slot.</li>'
        '</ol></section>'
        '<section class="grid"><article class="card span-6"><p class="kicker">Format gate</p><h2>Exact TIFF contract</h2><ul class="list-clean">'
        '<li>One raster band; `float32`.</li><li>CRS EPSG:32611; 100-m resolution.</li><li>Exact template dimensions, bounds, and geotransform.</li>'
        '<li>Every in-footprint value is finite and in [0, 1].</li><li>Outside-footprint cells are null/NaN, matching the official sample template.</li>'
        '<li>Use a unique content-addressed filename and keep a SHA-256 receipt.</li></ul>'
        '<p>After restoring the template, run the local checker from the repository root. For example:</p>'
        '<pre><code>GEMS_DATA_DIR=/path/to/restored/data python scripts/check_submission.py \\\n  docs/downloads/&lt;candidate.tif&gt; --receipt evidence/format_checks/&lt;candidate.json&gt;</code></pre>'
        f'<p>{a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/scripts/check_submission.py", "Review the checker source", external=True)}</p>'
        '<p>The local checker is necessary but cannot guarantee organizer acceptance. Review the current official problem page.</p></article>'
        '<article class="card span-6"><p class="kicker">Narrative disclosure</p><h2>Generative AI use</h2>'
        '<p>The September 2026 official rules require a narrative disclosure of the extent and role of generative-AI use when applicable. '
        'This project has a draft disclosure in its repository; it must be updated against the actual final work before submission.</p>'
        f'<p>{a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/05_genai_disclosure_draft.md", "Review the current disclosure draft", external=True)}</p>'
        '</article></section>'
        '<section class="card"><h2>Important distinction</h2><p>Spatially blocked catalogue-gap holdouts are an internal proxy. They do not reproduce the competition’s newly expert-labelled test faults, '
        'its public leaderboard score, private test score, or second-round revised-label score. Never use a holdout value as a claimed submission result.</p></section>'
    )
    return page(
        "Executive summary and submission guide",
        "Manual steps and exact checks for an eventual GEMS GeoTIFF submission. No current artifact is slot-approved.",
        "summary",
        "Executive summary · manual upload only",
        "A clear route from research artifact to submission.",
        "No file is currently cleared for a weekly slot. This page records the manual process and format contract so the next approved artifact is easy to identify and audit.",
        body,
        a("index.html", "Back to current status", class_name="button") + a("sources.html", "Official source links", class_name="button secondary"),
    )


def render_research() -> str:
    hypotheses = read_json("hypotheses.json")
    status = read_json("status_feed.json")["current"]
    cards = []
    for item in hypotheses.get("items", []):
        layers = ", ".join(item.get("layers", []))
        state = tag(item.get("status", ""), "warning" if item["id"] == "H31" else "")
        cards.append(
            f'<article class="card span-12"><div class="grid"><div class="span-8"><p class="kicker">Rank {e(item.get("rank"))} · {e(item["id"])}</p>'
            f'<h2>{e(item["title"])}</h2><p>{state}</p><p><strong>Layers:</strong> {e(layers)}</p>'
            f'<p><strong>Physical signature:</strong> {e(item.get("signature", ""))}</p>'
            f'<p><strong>Why it could add unmapped faults:</strong> {e(item.get("why_unmapped", ""))}</p>'
            f'<p><strong>How it differs from reviewed work:</strong> {e(item.get("difference", ""))}</p></div>'
            f'<aside class="span-4"><div class="metric"><span class="label">Planning ΔDTI</span><span class="value">{e(item.get("planning_delta_dti", "not estimated"))}</span>'
            '<span class="label">Planning range only—not measured, not a score</span></div>'
            f'<p><strong>Cost:</strong> {e(item.get("cost", ""))}</p><p><strong>Data:</strong> {e(item.get("external_data", ""))}</p></aside></div></article>'
        )
    body = (
        '<section class="status-banner"><strong>Novelty was rechecked against the latest main branch.</strong> The first H31 slate was written and implemented on a branch based at ad130c8, before main received the H29 experiment. That H29 work already tested raw-RTP/gravity worm persistence; H31 is now described only as a narrower pseudogravity-transform/drift extension, with a reduced planning range. H32 is the next unimplemented candidate. “Not found” is limited to the reviewed repositories, not all competitors.</section>'
        f'<section class="grid" aria-label="Ranked hypotheses">{"".join(cards)}</section>'
        '<section class="grid"><article class="card span-7"><p class="kicker">H31 research design</p><h2>Test the pseudogravity/drift increment beyond H29</h2>'
        '<p>H29 already ran upward-continuation worm persistence on raw RTP and isostatic gravity, including joint persistence as gate/rank/head features. No arm passed the preregistered +0.005 screen. Draws 2–3 were computed for all arms despite screen failures, so the reconciliation treats them as exploratory extras rather than eligible confirmations. H31 does not claim worming itself is new. It isolates a regularized vertical-integration pseudogravity <em>proxy</em> from RTP plus a lateral edge-drift feature, then checks whether those additions improve a same-run baseline. The available isostatic gravity anomaly is included separately. A symmetric Euclidean 200-m cross-support (5×5 bounding window, diagonal corners excluded) allows small grid misregistration; it is a tolerance, not geological proof.</p>'
        '<p>The first synthetic engineering test found exact-pixel multiplication produced an all-zero joint term after the distinct transforms. Before any real-data fit, the preregistered joint feature was clarified to use the fixed ±2-pixel tolerance; no model, data, scale, or gate changed.</p>'
        f'<p><strong>Current screen:</strong> {e(status.get("screen_status", "not run"))}. Confirmation is {e(status.get("confirmation_status", "blocked"))}.</p>'
        f'<p>{a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/02_preregistered_h31_worming_2026-10-03.md", "Read the preregistration and amendment", external=True)}</p>'
        '</article><article class="card span-5"><p class="kicker">Scientific limits</p><h2>Worming-like ≠ full inversion</h2>'
        '<p>Poisson-wavelet worming literature motivates upward continuation and tracking horizontal-gradient maxima. The implementation here is a scale-space proxy with regularized Fourier integration, not the full Hornby transform, not an inversion, and not a fault-depth estimator.</p>'
        '<p>Potential fields are non-unique: source interference, cultural noise, depth, remanence and misalignment can produce or hide edges. Persistence is not proof of faulting, geothermal activity, or discovery.</p>'
        '<p><a href="sources.html">Check the primary/review sources and limitations →</a></p></article></section>'
        '<section class="card"><p class="kicker">Promotion gates</p><h2>Spatial validation before any slot</h2>'
        '<p>Four spatial quadrants are the replication units; folds and draws are paired cells, not independent extra samples. H31 must beat the strongest same-run control by a paired mean DTI gain above 0.001, be positive in at least 3/4 spatial blocks, never lose more than 0.010 in one block, and avoid a material increase in catalogue-hug share. A fresh two-draw confirmation with the same gates is required. Raw-cell hashes and screen gates are recomputed before confirmation.</p>'
        '<p>Passing these gates only permits a candidate to be considered; it does not authorize a weekly submission, guarantee the official score, or establish generalization to expert-labelled faults.</p></section>'
        '<section class="card"><p class="kicker">What came before</p><h2>Predecessor audit</h2>'
        '<p>The reviewed GEMSDOE25 code already tried fixed-scale potential-field derivatives, terrain/scarp descriptors, catalogue geometry, geothermal/context tables, thinning, single-tip continuation, and an H30 relay-bridge × scarp experiment. The predecessor A-family potential-field screen was reported inert/negative on a catalogue-gap proxy; H30-1 failed fresh-draw confirmation. These are predecessor proxy reports, not official scores and not recomputed here.</p>'
        '<p><strong>Same-repository prior result:</strong> H29 on the prior main branch tested raw-RTP/gravity worm gating, rank order and model features, plus residualized thermal probes. No arm passed its frozen +0.005 screen. Draws 2–3 were computed for all arms anyway and are exploratory extras, not valid confirmations; see the gate reconciliation. No slot was recommended or used. This is a prior catalogue-gap proxy outcome, not a competition score. '
        + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/02_h29_results_2026-10-03.md", "Review the H29 outcome table", external=True) + ' · '
        + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/evidence/h29_gate.json", "Open the original H29 screen snapshot", external=True) + ' · '
        + a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/06_h29_gate_reconciliation_2026-10-03.md", "Read the gate reconciliation", external=True) + '</p>'
        '<p>Historical score claims remain unverified owner/user reports. No leaderboard snapshot is shown or used here. H31 is not designed or tuned to reproduce them.</p>'
        f'<p>{a("https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/knowledge/04_prior_work_audit.md", "Review the predecessor audit", external=True)}</p></section>'
        '<section class="card"><h2>Model and emission</h2><p>The frozen screen compares a fixed BDE + X1–X3 baseline, a H27 tip control, and factorial additions of magnetic-pseudogravity persistence/drift, gravity persistence/drift, and joint cross-support. All arms share the same holdout masks, samples, classifier family, and emission budget within a cell. The output is scored by the local distance-weighted metric on held-out catalogue traces only.</p></section>'
    )
    return page(
        "Research and hypotheses",
        "Three ranked hypotheses after the H29 prior-work review, with preregistration, prior results, and scientific limits.",
        "research",
        "Research register · updated from local files",
        "Three hypotheses, re-ranked against H29.",
        "H29’s four registered arms failed the spatial catalogue-gap proxy gate. H31 is now only an unfitted pseudogravity-transform/drift extension; H32 is the first unimplemented candidate, and H33 remains blocked. No current file is slot-approved.",
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
    for source in registry.get("sources", []):
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
        '<section class="card"><p class="kicker">Official and research sources</p><h2>Open the primary source yourself</h2>' + ''.join(items) + '</section>'
        '<section class="card"><h2>Data and interpretation caveats</h2><p>Review the project irregularities register for mirror provenance, ambiguous band semantics, unverified score claims, proxy limits, and blocked data.</p><p><a href="irregularities.html">Open the irregularities page →</a></p></section>'
        '<section class="card"><p class="kicker">Terms decision</p><h2>No DrivenData polling or scraping</h2>'
        '<p>DrivenData’s Terms of Use prohibit robots or other automatic access for any purpose, including monitoring/copying, and manual monitoring/copying without prior written consent. The reviewed terms display last modified August 7, 2014. No written consent for monitoring is present. This project includes no leaderboard link, live page content, polling, or copied score feed; local status comes only from repository evidence.</p>'
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
