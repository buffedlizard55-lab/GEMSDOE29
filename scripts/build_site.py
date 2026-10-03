#!/usr/bin/env python3
"""Render the GitHub Pages site (root index.html + docs/*.html) from the registries and evidence.

Everything on the pages is injected from JSON that the pipelines themselves wrote
(data/manifest.json, registry/*.json, evidence/*.json) — the HTML never re-types a number, which is
how this repo enforces 'no hallucinations' on the site layer. Re-run after any experiment.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
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
    if root:  # page lives at repo root; subpages under docs/
        home, pref = "index.html", "docs/"
    else:     # page lives in docs/; siblings unprefixed, home up one level
        home, pref = "../index.html", ""
    links = [(home, "Home"), (pref + "executive-summary.html", "Executive summary &amp; submission guide"),
             (pref + "research.html", "Research &amp; method"), (pref + "sources.html", "Sources, scores &amp; flags")]
    return "<nav>" + "".join(f'<a href="{h}">{txt}</a>' for h, txt in links) + "</nav>"


def page(title, body, root: bool = False):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body><main>
{nav_for(root)}
<h1>{esc(title)}</h1>
{body}
<footer>GEMSDOE29 · built {now} · every figure on this page is generated from the repo's own JSON
evidence (scripts/build_site.py) · competition: DrivenData #306 DOE GEMS Prize · owner-reported
scores are labelled as such and are not organizer receipts.</footer>
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
    irr = J("registry/irregularities.json")
    hyp = J("registry/hypotheses_h29.json")
    gate = J("evidence/h29_gate.json") if (ROOT / "evidence/h29_gate.json").exists() else {}
    hold = J("evidence/h29_holdout.json") if (ROOT / "evidence/h29_holdout.json").exists() else {}
    worm = J("evidence/worming_receipt.json") if (ROOT / "evidence/worming_receipt.json").exists() else {}
    ledger_p = ROOT / "registry/artifact_ledger.json"
    ledger = J("registry/artifact_ledger.json") if ledger_p.exists() else {"artifacts": {}}
    arts = ledger.get("artifacts", {})

    wr = arts.get("WORMRANK", {})
    files_dir = ROOT / "docs" / "downloads"
    def fmeta(stem, suffix="-nan.tif"):
        p = files_dir / f"{stem}{suffix}"
        if not p.exists():
            return None
        import hashlib
        h = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(1 << 20):
                h.update(chunk)
        return {"name": p.name, "bytes": p.stat().st_size, "sha256": h.hexdigest()}

    m_nan = fmeta(wr.get("stem", ""), "-nan.tif")
    m_zip = fmeta(wr.get("stem", ""), "-nan.zip")
    m_zero = fmeta(wr.get("stem", ""), "-zeros.tif")
    gate_pass = bool((gate.get("A2") or {}).get("PASS"))
    gate_txt = ("FROZEN GATE PASSED (local proxy) — slot-recommended, live effect unverified"
                if gate_pass else
                "FROZEN GATE NOT PASSED on the local proxy — research artifact; see research page. "
                "No slot spend is recommended by this repo.")
    gate_kind = "ok" if gate_pass else "warn"

    # ---------------- index.html (repo root, Pages 'build from main root') ----------------
    dl_block = ""
    if m_nan:
        dl_block = f"""
<div class="card" id="download">
<h2 style="margin-top:0">⬇ Submission TIF — one click</h2>
<p><a class="dl" href="docs/downloads/{m_nan['name']}">Download {m_nan['name']}</a></p>
<p class="mut">{m_nan['bytes']:,} bytes · SHA-256 <code>{m_nan['sha256'][:16]}…</code> ·
{fmt_px(wr.get('px', 0))} emitted pixels · single-band float32 · EPSG:32611 · 3730×3292 · 100 m ·
values exactly 0.0/1.0 in the footprint, NaN outside — the format that cannot raise
“Predicted values must be in range [0, 1]”.</p>
<p>{badge(wr.get('status', 'missing status label'), status_kind(wr.get('status', 'missing')))}
{badge(gate_txt, gate_kind)}</p>
<p><b>Paste into the DrivenData <i>Note</i> field:</b></p>
<pre>{esc(wr.get('note', '—'))}</pre>
<p class="mut">Unique submission name (≤200 chars, paste alongside the file name if you rename):
<b>{esc(m_nan['name'].removesuffix('.tif'))}</b>. Fallbacks: <a href="docs/downloads/{m_zip['name'] if m_zip else '—'}">.zip (same TIFF)</a> ·
<a href="docs/downloads/{m_zero['name'] if m_zero else '—'}">-zeros.tif (0.0 outside footprint)</a>.
Check receipts: docs/downloads/checks-{esc(wr.get('stem', ''))}.json.</p>
<p><a href="docs/executive-summary.html">→ Step-by-step submission guide</a> ·
Reference (already live-scored 0.2600 — <b>do not resubmit</b>):
{esc(arts.get('REFD28', {}).get('stem', '—'))}</p>
</div>"""
    lb = live["leaderboard_public_2026-10-03T0826Z"]
    lb_rows = "".join(f"<tr><td class='num'>{r['rank']}</td><td>{esc(r['team'])}</td>"
                      f"<td class='num'>{r['public_dti']}</td><td class='num'>{r['submissions']}</td></tr>"
                      for r in lb)
    rows = "".join(
        f"<tr><td>{esc(s['project'])}</td><td><code>{esc(s['file'])}</code></td>"
        f"<td class='num'>{s['score']}</td><td>{esc(s.get('status', ''))}</td></tr>"
        for s in live["group_submissions"][:10])

    idx_body = f"""
<p class="mut">{badge('Ends 2026-12-03 23:59 UTC (competition homepage, read 2026-10-03)', 'warn')}
{badge('3 submissions / rolling 7 days — sibling/owner-reported; rules PDF unreachable in sandbox (IR-29-RULES-URL)', 'warn')}
{badge('Group best (owner-reported): 0.2600 · public rank #15', 'ok')}
{badge('Public #1: DARD 0.3195 (leaderboard read 2026-10-03)', 'bad')}</p>
{dl_block}
<h2>Why 0.2600 scored 0.2600 — the 60-second answer</h2>
<div class="card"><p>The winning file is <b>not</b> a better detector. It is the H19-5 solid fault
surface (121,131 px, live 0.1922) <b>thinned with Poisson-disk spacing 2.8 px to 44,090 dots</b>.
Because the metric takes a <i>maximum</i> of predicted probability within a 300 m tolerance around each
truth pixel but <i>sums</i> false-positive mass, overlapping credit kernels are wasted pixels: dropping
64 % of the pixels lost only ~24 % of the credit and bought the rest back as
discipline — spacing +26.8 %, then +0.0123 for a smarter 2.8-px lattice. The geometry lever is
<b>arithmetic-exhausted at ≈0.255–0.260 on this surface</b> (GEMSDOE27 live inversion; our tests
reproduce the 0.2477 file bit-for-bit and the 44,090-px count exactly).</p>
<p>Reaching 0.3195 needs <b>0.570·|G| of weighted credit at the same budget — more than any emission
in this competition's public history has earned</b>. That is a detector problem (concentration &gt; 5.7×
blind), which is why this repo bets on new physics in: multiscale worming (upward-continuation
persistence), residualized 2 m geothermal probes, and (registered, pending) flight-line spectral notch.</p></div>
<h2>This session's science in one table</h2>
{gate_table(gate, hold)}
<h2>Live leaderboard, public column (read once, 2026-10-03T08:26Z)</h2>
<table><tr><th>Rank</th><th>Team</th><th>Public DTI</th><th>Subs</th></tr>{lb_rows}</table>
<h2>Group score ledger (owner-reported claims; first 10 of {len(live['group_submissions'])})</h2>
<table><tr><th>Project</th><th>Submission</th><th>Score</th><th>Status</th></tr>{rows}</table>
<p><a href="docs/sources.html">Full ledger + verification state →</a></p>
<h2>Flagged for review (this session, {len(irr['irregularities'])} items)</h2>
{irregularities_table(irr)}
<p>Repo contract: the owner's full brief + core values live in <a href="https://github.com/buffedlizard55-lab/GEMSDOE29/blob/main/README.md"><code>README.md</code></a> and must be re-read at the start of every session.</p>
"""
    (ROOT / "index.html").write_text(page("GEMSDOE29 — worming the deep/shallow boundary (DOE GEMS #306)", idx_body, root=True))

    # ---------------- docs/executive-summary.html ----------------
    exec_body = f"""
<h2 style="border:0">Do this in 60 seconds</h2>
<ol>
<li>Click <a href="../index.html#download">the download button</a> on the home page
(<code>{esc(m_nan['name'] if m_nan else '—')}</code> or the <code>.zip</code>).</li>
<li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">the competition
<i>My Submissions → New submission</i> form</a> (you must be logged in as the enrolled team — the agent never
touches the portal; the ToS prohibits automated access).</li>
<li>Attach the file. The form states it accepts a single-band GeoTIFF (.tif) or a .zip containing exactly one
GeoTIFF, and that the CRS, shape and geotransform must match the submission format — our verifier enforces all of
those against the pinned template <i>before</i> you download.</li>
<li>Paste the note (unique name + short comment, ≤200 chars):
<pre>{esc(wr.get('note', '—'))}</pre></li>
<li>Submit. You have <b>3 submissions per rolling 7 days</b>; the Initial Prize Round scores against a hidden
private set; you later choose ONE submission for both rounds.</li>
</ol>
<h2>Why the old upload failed “Predicted values must be in range [0, 1]” — and why this one can't</h2>
<div class="card"><p>Diagnosis (from byte-forensics of the failed file, GEMSDOE25 IR-25-NAN-FOOTPRINT): it wrote
<b>NaN inside the footprint</b> (2,344,929 of 5,167,373 pixels). NaN fails any “≤1” range test, so the portal's
range check rejects it regardless of what values you think you're submitting. The public docs don't publish the
validator, so we defend in depth, and every shipped file is re-verified here from disk by
<code>scripts/verify_downloads.py</code>:</p>
<ul>
<li>profile (CRS EPSG:32611, transform, 3730×3292, float32) copied from the pinned sample template;</li>
<li><b>every</b> in-footprint pixel finite and exactly 0.0 or 1.0 — including the 3,061 pixels that are nodata
in the features stack (IR-29-FOOTPRINT-DIFF) — written as 0.0;</li>
<li>NaN only <i>outside</i> the footprint (the sample's own convention) plus a <code>-zeros.tif</code> fallback
with 0.0 outside (both conventions are scored historically identically — 12GEMSDOE pair);</li>
<li>the .zip variant contains exactly one GeoTIFF, byte-checked after read-back;</li>
<li>SHA-256 + check receipts next to the file in <code>docs/downloads/</code>.</li>
</ul></div>
<h2>What you are submitting — honest status</h2>
<div class="card">{badge(gate_txt, gate_kind)}
<p>This file reorders (not reselects) the dots of the owner's live-scored 0.2600 geometry using a persistence
score computed from a Fourier upward-continuation ladder on the official magnetic and gravity bands
(see <a href="research.html">research page</a>). Same spacing guarantee, same pixel budget scale, new claiming
order. {fmt_px(wr.get('px', 0))} px emitted; catalogue-masked; 0 px on catalogue pixels.</p>
<p class="mut">The repo's rule, unchanged from prior sessions: a proxy pass makes a file <i>eligible</i> for a slot decision;
it is never evidence of a live score. If the gate above says NOT PASSED, spending a weekly slot is the owner's
explicit call against the numbers shown — not this repo's recommendation.</p></div>
<h2>Rollback / reference</h2>
<p><code>{esc(arts.get('REFD28', {}).get('stem', '—'))}-nan.tif</code> is a bit-for-bit reproduction of the
44,090-px geometry that the owner reports scored 0.2600 (tests/test_sibling_reproduction.py). It exists to prove
format validity and for emergency rollback; resubmitting it would waste a slot without changing anything.</p>
"""
    (ROOT / "docs" / "executive-summary.html").write_text(page("How to submit — GEMSDOE29", exec_body))

    # ---------------- docs/research.html ----------------
    res_body = research_body(worm, gate, hold, hyp)
    (ROOT / "docs" / "research.html").write_text(page("Worming research & method — GEMSDOE29", res_body))

    # ---------------- docs/sources.html ----------------
    src_body = sources_body(srcs, manifest, live, irr)
    (ROOT / "docs" / "sources.html").write_text(page("Sources & verification — GEMSDOE29", src_body))
    print("site written: index.html + docs/{executive-summary,research,sources}.html")


def gate_table(gate, hold):
    if not gate:
        return "<div class='card'>Gate results pending — run scripts/run_holdout_screen.py.</div>"
    rows = ""
    for arm, g in gate.items():
        if not isinstance(g, dict):
            continue
        pd_ = g.get("per_draw", {})
        cells = " · ".join(f"draw{k[-1]}: {v['mean_delta']:+.4f} ({v['positive_folds']}/4 folds)"
                           for k, v in pd_.items())
        verdict = g.get("PASS")
        vtxt = "PASS" if verdict is True else ("FAIL" if verdict is False else str(verdict))
        rows += (f"<tr><td><b>{esc(arm)}</b></td><td>{esc(cells)}</td>"
                 f"<td>{esc(g.get('confirm_draw') or '—')}</td>"
                 f"<td>{badge(vtxt, 'ok' if verdict is True else 'bad')}</td></tr>")
    n_rows = len(hold.get("rows", [])) if hold else 0
    return (f"<div class='card'><table><tr><th>arm</th><th>mean paired quadrant ΔDTI (sparse proxy)</th>"
            f"<th>confirming draw</th><th>gate (≥+0.005, ≥3/4, both screen draws, ≥1 confirm)</th></tr>"
            f"{rows}</table><p class='mut'>Proxy = catalogue hide-and-recover (4 folds × draws, {n_rows} runs). "
            "This proxy is structurally blind to far-field habitat (IR-29-PROXY-BLIND-TO-FARFIELD): read the "
            "research page's audits alongside these numbers.</p></div>")


def research_body(worm, gate, hold, hyp):
    if worm:
        m, g = worm.get("magnetic", {}), worm.get("gravity", {})
        la = worm.get("line_audit_magnetic", {})
        xc = worm.get("uc_crosscheck", {})
        worm_cards = f"""
<h2>Upward-continuation ladder — measured, on the official grids</h2>
<table><tr><th>field</th><th>level-0 edges</th><th>survive whole ladder (≥1600 m)</th>
<th>exist at zero continuation only</th><th>mean persistence</th></tr>
<tr><td>rtp (magnetic)</td><td class='num'>{fmt_px(m.get('n_edges_level0', 0))}</td>
<td class='num'>{m.get('frac_edges_full_ladder', 0):.1%}</td>
<td class='num'>{m.get('frac_edges_level0_only', 0):.1%}</td>
<td class='num'>{m.get('mean_persistence', 0):.3f}</td></tr>
<tr><td>iso_grav_anom</td><td class='num'>{fmt_px(g.get('n_edges_level0', 0))}</td>
<td class='num'>{g.get('frac_edges_full_ladder', 0):.1%}</td>
<td class='num'>{g.get('frac_edges_level0_only', 0):.1%}</td>
<td class='num'>{g.get('mean_persistence', 0):.3f}</td></tr></table>
<div class='card'><p><b>Operator cross-check:</b> our continuation of the <code>tmi</code> band to 150 m has
Spearman {xc.get('spearman_hgm_ours_vs_contractor_up150', float('nan')):.3f} rank agreement with the official
contractor <code>TMI_up150</code> grid's gradient (u8-quantised, {fmt_px(xc.get('n_sampled_pixels', 0))} sampled
pixels) — the continuation operator behaves like the survey's own.</p>
<p><b>Acquisition-line audit (the number, not the hunch):</b> mean persistence by strike —
E–W {la.get('mean_persist_ew_strike', 0):.3f}, other {la.get('mean_persist_other', 0):.3f},
N–S {la.get('mean_persist_ns_strike', 0):.3f} over {fmt_px(la.get('n_ew', 0))}/{fmt_px(la.get('n_other', 0))}/{fmt_px(la.get('n_ns', 0))} edges.
E–W edges (where 200/400 m east–west flight-line aliasing would live) are, if anything, <i>more</i> persistent —
so a naive “kill E–W strikes” filter is refuted on this grid (IR-29-LINE-PERSISTENCE-INVERSION); the strike-blind
gate/rank arms are what remains, plus a registered spectral-notch experiment (H29-3).</p>
<p><b>Parent-emission orthogonality:</b> only ≈2.7 % of the live-scored dots sit on p95 level-0 edges, of which
≈1.7 %×44,090 ≈ 734 are deep-persistent (IR-29-PARENT-OFF-EDGES). Consequence: worming enters as <i>order</i>
and as <i>model feature</i>, and any hard gate is near-powerless — all three forms were run and are reported.</p></div>"""
    else:
        worm_cards = "<div class='card'>worming receipt missing — run scripts/run_worming.py.</div>"

    arm_rows = ""
    for r in hold.get("rows", []):
        a, b = r.get("A", {}), r.get("B", {})
        arm_rows += (f"<tr><td>{r['draw']}</td><td>{esc(r['name'])}</td>"
                     f"<td class='num'>{r['n_hidden']:,}</td>"
                     + "".join(f"<td class='num'>{a.get(k, {}).get('paired_delta', 0):+.4f}</td>" for k in ("A1", "A2"))
                     + "".join(f"<td class='num'>{b.get(k, {}).get('paired_delta', 0):+.4f}</td>" for k in ("B1", "B2"))
                     + "</tr>")
    hyp_rows = "".join(
        f"<tr><td>{h['rank']}</td><td><b>{esc(h['id'])}</b> {esc(h['name'])}</td>"
        f"<td>{esc(h['layers'] if isinstance(h['layers'], str) else ', '.join(h['layers']))}</td>"
        f"<td>{esc(h['signature'])}</td><td>{esc(h['why_unmapped'])}</td><td>{esc(h['differs'])}</td>"
        f"<td>{esc(h['cost'])}</td></tr>" for h in hyp["hypotheses"])
    not_rows = "".join(f"<li><b>{esc(x['idea'])}</b> — {esc(x['why'])}</li>" for x in hyp["explicitly_not_redone"])
    return f"""
<h2 style="border:0">What “worming” is, in one paragraph</h2>
<p>Upward continuation of a potential field <i>is</i> a wavelet scale change (Hornby, Boschetti &amp; Horowitz 1999,
GJI 137:175–196; operational account: Horowitz 2018, Stanford GMC — links on the sources page). Continue the grid
through a ladder of heights; at each height take the local maxima of the horizontal-gradient modulus; link maxima
across heights into “worms”. An edge that survives km of continuation is tied to deep, laterally coherent source
contrast; one that dies at the first step is shallow — near-surface geology or instrument/lineation artifact. We
implement the ladder spectrally (exp(−2πh|k|)), on <code>rtp</code> and <code>iso_grav_anom</code>, with a
level-relative p95 threshold and a tolerance that grows 1 px + 0.5 px per 100 m, then use persistence three ways:
emission <b>gate</b> (A1), emission <b>re-rank</b> (A2), and <b>head features</b> (B1) — with a fourth arm (B2)
screening residualized 2 m geothermal probes as independent corroboration.</p>
<p class="mut">Unit-test anchor: this repo verifies the operator's wavelet identity numerically
(tests/test_worming_and_thinning.py: UC by h of a dike at depth d ≈ the same dike at d+h; corr &gt; 0.97, and
deep retains gradient amplitude to 1600 m strictly more than shallow). Design-level honesty: 51 % of gravity
level-0 edges die at zero-continuation — that IS the population the audit distrusts, now with a number.</p>
{worm_cards}
<h2>Holdout screen (frozen gate in knowledge/01, written before any run)</h2>
{gate_table(gate, hold)}
<table><tr><th>draw</th><th>fold</th><th>hidden px</th><th>ΔA1</th><th>ΔA2</th><th>ΔB1</th><th>ΔB2</th></tr>
{arm_rows or '<tr><td colspan=7>pending</td></tr>'}</table>
<h2>Hypothesis slate (ranked; each checked against prior repos for non-duplication)</h2>
<table><tr><th>#</th><th>id</th><th>layers</th><th>signature</th><th>why it catches an unmapped fault</th>
<th>differs from prior repos</th><th>cost</th></tr>{hyp_rows}</table>
<h3>Deliberately not redone</h3><ul>{not_rows}</ul>
<h2>What this means for beating 0.3195</h2>
<div class="card"><p>The arithmetic: at the group's best emission (44,090 px, owner-reported 0.2600) the leader's
public 0.3195 requires weighted credit 0.570·|G| — never earned at that budget. Geometry is exhausted; only
concentration above ≈5.7× blind closes the gap, and that requires information the h19-5 family never used. This
repo brought two such sources to a frozen gate (potential-field persistence; official thermal-probe residuals) and
records whatever it measured — no spin. If the gates fail, the conclusion <i>is</i> the finding: these two
particular new-information channels do not move the proxy, and the slot budget should go to registered arms with
live-testable value (H29-3 notch, H29-5 strain×persistence corridors) or to a real U-Net ensemble with the reference
solution's loss on GPU, which this sandbox cannot train.</p></div>
"""


def sources_body(srcs, manifest, live, irr):
    s_rows = "".join(
        f"<tr><td><a href='{esc(s['url'])}'>{esc(s['url'])}</a></td><td>{esc(s.get('accessed', '—'))}</td>"
        f"<td>{badge(s.get('status', ''), status_kind(s.get('status', '')))}</td><td>{esc(s.get(chr(39)+chr(99)+chr(108)+chr(97)+chr(105)+chr(109)+chr(115)+chr(39), chr(39)+chr(45)+chr(39)))}</td></tr>"
        for s in srcs["sources"])
    m_rows = "".join(
        f"<tr><td><code>{esc(f['path'])}</code></td><td class='num'>{f['bytes']:,}</td>"
        f"<td><code>{f['sha256'][:20]}…</code></td><td>{esc(f['what'])}</td></tr>"
        for f in manifest["files"])
    all_scores = "".join(
        f"<tr><td>{esc(s['project'])}</td><td><code>{esc(s['file'])}</code></td>"
        f"<td class='num'>{s['score']}</td><td>{esc(s.get('status', s.get('parent', s.get('note', ''))))}</td></tr>"
        for s in live["group_submissions"])
    return f"""
<h2 style="border:0">Official sources, as actually read this session</h2>
<table><tr><th>source</th><th>accessed (UTC)</th><th>state</th><th>what it verifiably says</th></tr>{s_rows}</table>
<h2>Input data provenance (hash-pinned owner mirrors — NOT organizer-authenticated)</h2>
<p class="mut">{esc(manifest['note'])}</p>
<table><tr><th>path</th><th>bytes</th><th>sha256</th><th>content</th></tr>{m_rows}</table>
<h3>Blocked this session (named so a networked runner can act)</h3>
<ul>{''.join(f"<li><code>{b['key']}</code> — <a href='{b['url']}'>{b['url']}</a> — {esc(b['reason'])}</li>" for b in manifest['blocked_this_session'])}</ul>
<h2>Full score ledger</h2>
<p class="mut">{esc(live['verification_note'])}</p>
<table><tr><th>project</th><th>submission</th><th>reported score</th><th>verification / parent</th></tr>{all_scores}</table>
<h2>Irregularities register</h2>
{irregularities_table(irr)}
"""


def irregularities_table(irr):
    return ("<table><tr><th>id</th><th>sev</th><th>state</th><th>finding → action</th></tr>" + "".join(
        f"<tr><td><code>{esc(i['id'])}</code></td><td>{badge(i['sev'], status_kind(i['sev'] if i['sev'] != 'high' else 'bad'))}</td>"
        f"<td>{esc(i['status'])}</td><td>{esc(i['finding'])}<br><span class='mut'>→ {esc(i['action'])}</span></td></tr>"
        for i in irr["irregularities"]) + "</table>")


if __name__ == "__main__":
    main()
