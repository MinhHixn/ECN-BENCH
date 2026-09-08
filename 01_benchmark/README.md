# Frozen benchmark inputs

`events_raw.json` is the authoritative event catalogue used to interpret the 30-event campaigns. Its study-level descriptive header retains superseded counts; enumerate actual event records. Seed dossiers are under `seeds/<event_id>/context.md`. The round-30 input bank is `injections/step30_injection_bank.json`.

These are historical inputs, not a certified leakage-free forecasting dataset. Source timestamps, market resolutions and option-set semantics were not independently adjudicated for every event in the September revision. The C/S/T prefixes are retained for traceability, not as a validated taxonomy.

The injection bank is stale-aligned for C6, T1, T3, T4, T5, T6 and T8. Repairs changed simulation questions but deliberately retained this bank. B is only nominally relevant. Bodies are not length-matched: relevant/null ratios range 1.51–2.37 with median 2.04; all null bodies share one text.

The 20-event post-release subset is not contamination-clean for later evaluators. Its uniform-choice reference is mean 1/K = 0.3264; no exact pooled accuracy test is justified by this reference alone.

Historical design notes and research templates remain in this directory. They describe intended protocols, which must not be assumed identical to executed campaigns. Current interpretation: `../00_docs/PROVENANCE.md`.

