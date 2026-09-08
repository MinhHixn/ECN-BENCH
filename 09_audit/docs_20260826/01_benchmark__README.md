# 01_benchmark — the benchmark definition

Everything needed to run ECN-BENCH against a **new** model. These are the *inputs*; the
outputs are in `02_campaigns/` and `03_traces/`.

| Path | What it is |
|---|---|
| `events_raw.json` | **The authoritative 30-event catalogue.** Question, options, ground truth, resolution date and seed reference per event. |
| `seeds/<event_id>/` | The seed dossier each event's agents read. `context.md` is the document itself. |
| `injections/step30_injection_bank.json` | The round-30 perturbations: one content-relevant injection (Condition B) and one length-matched unrelated injection (Condition C) per event. |
| `research_templates/` | The per-event research templates the dossiers were built from, plus `RESEARCH_GUIDE.md`. |
| `manual_seeds.json` | Manually curated seed metadata. |
| `seeds_mapping.txt` | Event id → seed directory mapping. |
| `ECNBENCH_25_Event_Seed_Pack.md` | Narrative description of the original seed pack. |

## The taxonomy

Event ids encode a three-way taxonomy:

| Prefix | Class |
|---|---|
| `C` | Social / Electoral |
| `S` | Senate / Binary |
| `T` | Technical / Economic |

This supersedes the 2×2 Information-Type × Resolution-Horizon grid of the original
specification, which the seed corpus does not carry as per-event metadata.

## Two warnings before you use this

**1. There are two catalogues in circulation, and they disagree.**
This file is the authoritative root catalogue. A stale copy that shipped inside the HPC
deployment directory assigns *different questions* to seven ids —
**C6, T1, T3, T4, T5, T6, T8**. Both are preserved side by side for diffing at
`09_audit/stale-catalogue/`.

This is not a hypothetical hazard: it silently corrupted two separate re-simulation
attempts in this project, because a relative `--events-raw ../../data/events_raw.json`
resolved to the stale file. **Always pass an absolute path, and diff the questions your
run produced against this file before scoring anything.**

**T1 and T5 collide silently** — same options, same ground truth — so an id mix-up
between those two raises no error at all, only wrong data.

**2. The injection bank is deliberately stale-aligned for those same seven ids.**
It was *not* re-authored when the catalogue collision was found. Re-authoring it would
have given the repaired campaign better stimuli than the other three, which all ran
under the same off-topic injection. Consistency across campaigns was chosen over
correctness within one. This is a design limitation, stated in the paper — not an
oversight. If you run new campaigns, you may reasonably choose differently, but then
your results are not comparable to these on those seven events.

## Chance is not 0.5

`options` has K between 2 and 9 across the catalogue. Chance accuracy is `1/K` per
event, so any test against a chance baseline is a **Poisson binomial**, computed
exactly — not a coin flip. Treating it as 0.5 overstates significance by a wide margin.
