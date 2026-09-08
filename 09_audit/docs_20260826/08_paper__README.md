# 08_paper

| File | What it is |
|---|---|
| `ecn_bench_paper.tex` / `.pdf` | The technical report — the primary write-up. 85 pages. |
| `ecn_bench_paper_conf.tex` / `.pdf` | The conference version, 8 pages, IEEEtran `conference` class. Shares all figures with the report and cites it as `\cite{techreport}`. Synchronised to the released data on 2026-08-26 — see below. |
| `PAPER_DATA_MANIFEST.md` | The working manifest kept during the project. Session-by-session record of what changed and why. Superseded by `00_docs/PROVENANCE.md` for anything a reader needs, but retained: it carries detail the condensed version drops. |

## ⚠ Do not remove `\usepackage[T1]{fontenc}` / `\usepackage{lmodern}`

Both preambles open with these two lines and a comment saying they are required. They
are. Without them, IEEEtran builds under the default OT1 Computer Modern setup, and
XeTeX — which Tectonic uses — **silently falls back to the regular face for every bold,
italic and small-caps request**. The document still compiles with 0 errors and 0
overfull boxes; it simply loses all of its emphasis.

That was the actual state of these PDFs until 2026-08-26. Every `\textbf` run-in lead,
every `\emph`, IEEEtran's own `Abstract` / `Index Terms` labels and small-caps table
captions rendered as ordinary roman — including the bold cells that
`tab:per_event_llama_8b`'s caption explicitly promises ("Bold B-score indicates With-Sim
< No-Sim"), none of which were bold. If you edit the preamble, rebuild and check that
`\textbf` still looks bold.

## Build

```bash
tectonic -X compile ecn_bench_paper.tex
```

Tectonic 0.17 resolves all packages offline on first run. Expect **87 pages, 0 errors,
0 undefined references or citations, 0 overfull boxes**, and 9 cosmetic underfull hboxes
(long unbreakable `\texttt{}` strings). The conference version is **8 pages**, same
clean status. Figures resolve from `../06_figures/` — either copy them next to the
`.tex` or add `\graphicspath{{../06_figures/}}`.

Six `LaTeX Font Warning: Font shape ... undefined` lines are expected and benign:
`TU/ptm/*` is IEEEtran asking for Times in the Unicode encoding, and
`T1/lmr/bx/sc` / `T1/lmr/m/scit` are bold and italic *inside* IEEEtran's small-caps
table captions, which Latin Modern resolves to the nearest available shape.

The IEEEtran `conference` class was chosen for the short version because it resolves
offline; retarget it before submitting anywhere specific.

## Both versions are synchronised to the released data

`ecn_bench_paper_conf.tex` had been left at **2026-08-17**, before Qwen2.5-14B was
recovered to 30/30 and the globally-clean event set grew from 17 to 20 events. It was
brought up to date on 2026-08-26, sourcing every value from the verified JSONs in
`04_experiments/` and `05_analysis/outputs/`:

| Was (17-event) | Now (20-event, verified) |
|---|---|
| 17 events, 68 (model, event) pairs | 20 events, 80 pairs |
| 56.5/68 = 83.1 % directional accuracy | 65.5/80 = 81.9 % |
| chance 34.6 % | 32.6 % |
| p = 9.8 × 10⁻¹⁹ | 3.7 × 10⁻²² |
| ΔBrier +0.125 [+0.053, +0.195] | +0.112 [+0.042, +0.182] |
| Δ dir. acc. +0.184 [+0.066, +0.309] | +0.194 [+0.075, +0.313] |
| CoT pooled 0.856 vs swarm 0.831 | 0.834 vs 0.819 |
| 204 CoT calls, df = 16 / 67 | 240 calls, df = 19 / 79 |
| 59 events for 80 % power | 55 |

**Two claims changed in substance, not only in value**, and were rewritten rather than
renumbered:

1. The conference version said that on both identity-matched arms the single call has
   the lower Brier *and the higher directional accuracy*. On 20 events the accuracy half
   is no longer true — it splits, favouring the single call for Llama-3.1-8B (0.778 vs
   0.675) and the swarm for Qwen2.5-7B (0.790 vs 0.850). The Brier half holds on both.
2. It said "no clustered *p* falls below 0.069". That is now false: the three-replicate
   ensemble variant reaches 0.034 and 0.032. Both *primary* estimates remain
   non-significant (0.109 matched, 0.083 four-arm), and the text now says exactly that,
   flagging the ensemble as a 3×-cost upper bound rather than the comparison.

Both papers compile clean — the report at 87 pages, the conference version at 8 — with
0 errors, 0 undefined references and 0 overfull boxes.

## Before camera-ready

The Data Availability section was rewritten on **2026-08-26** and is already correct in
`ecn_bench_paper.tex`: it describes this archive, states that reproduction was verified
end to end, and no longer claims Qwen2.5-14B's artifacts "were never transferred off the
cluster" — the six events recovered 2026-08-21 and the C15 fragment are released here.

What remains is a single value. The preamble defines:

```latex
\newif\ifecnanonymous
\ecnanonymoustrue                                    % <- flip to \ecnanonymousfalse
\newcommand{\ecnarchivedoi}{10.5281/zenodo.XXXXXXX}  % <- fill in
```

Set both and the section resolves the real link by itself. Put the same DOI in
`CITATION.cff`. `00_docs/latex_data_availability.tex` holds the standalone version of
the section, for reference or for pasting into a different manuscript.

## Read the tables against the JSON, not the other way round

The LaTeX tables have drifted from their source JSONs before, through manual
transcription. When they disagree, the JSON is authoritative:

- Table `tab:four_model_clean` ← `04_experiments/01_evaluator-replication/reproducibility_analysis_master.json`
- Table `tab:predictive_signal` ← `05_analysis/outputs/predictive_signal_analysis.json`
- Table `tab:cot_baseline` ← `04_experiments/04_single-agent-cot-baseline/cot_baseline_analysis.json`

The paper carries its own errata table recording 25 claims that were corrected,
downgraded or withdrawn during the audit. `00_docs/PROVENANCE.md` §3 lists the
withdrawn ones in a form that does not require reading the paper first.
