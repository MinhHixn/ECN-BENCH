# 03_traces — raw multi-agent simulation transcripts

The complete record of what the agents actually did: ~2.3 GB, 360 SQLite databases plus
per-agent action logs, personas and driver logs. This is the bulk of the archive and the
part that is hardest to obtain any other way.

## Layout

```
03_traces/
  llama-3.1-8b-awq/   <unit>/ …           90 units, 120 databases
  mistral-7b-awq/     <unit>/ …           90 units, 120 databases
  qwen2.5_7b/         <unit>/ …           90 units, 120 databases
  qwen2.5-14b-awq/
      recovered-2026-08-21/               18 units, 24 databases
      original-2026-07-27_C15-fragment/    3 units,  4 databases
```

Unit directories are named `<event>_<condition>_r<repeat>`, e.g. `C10_B_r1`.

**Qwen2.5-14B is split by provenance on purpose**, because its two surviving trace sets
came from different runs months apart and must not be treated as one campaign. The other
three models are flat, one directory per unit.

## Inside a unit

| File | Contents |
|---|---|
| `twitter_simulation.db` | SQLite. `user` (300 rows), `post`, `comment`, `like`, `dislike`, `follow`, `mute`, `rec`, `trace`, `chat_group`, `group_members`, `group_messages`, `report`, `product`. |
| `reddit_simulation.db` | Same schema, Reddit platform. |
| `twitter/actions.jsonl` | Line-delimited action log: header, then `round_start` / action / `round_end` records. |
| `reddit/actions.jsonl` | Same, Reddit. |
| `twitter_profiles.csv` | The 300 generated agent personas. |
| `reddit_profiles.json` | Same, Reddit format. |
| `simulation_config.json` | Resolved configuration, including `event_question` — **the field to check for wrong-topic runs**. |
| `simulation.log` | Full driver log, often 3 MB+. |

`_execution_traces/execution.jsonl` (where present) records job-level events.

**Condition A units carry no database** and are ~0.5 MB: A is direct elicitation, no
simulation ran. `simulation_executed` is `false` for every A row.

## Three things to know before analysing these

**1. Action density is genuinely very low.** A typical Condition-B twitter trace holds
only a handful of `CREATE_POST` actions across 300 agents and 60 rounds. This is a real
property of the runs — analysed in the paper's interaction-realism section — not a
truncated export. Do not assume a bug when you find a nearly-empty `post` table.

**2. The `actions.jsonl` header disagrees with the run.** It declares
`total_rounds: 120`, while the run actually emits rounds 0–60, matching
`run_manifest.json`'s `total_simulation_hours: 60` / `minutes_per_round: 60`. Trust the
observed `round` values, not the header.

**3. The evaluator did not read these files directly.** It read `evidence_text`, a
capped digest built by `build_evidence_text()` from `{twitter,reddit}/actions.jsonl`
plus the tail of `simulation.log` — **not** from the SQLite databases. So the transcript
here is *richer* than what any evaluator saw. If you are re-scoring, decide deliberately
whether you want to reproduce the pipeline's view (use `evidence_text` from
`02_campaigns/`) or improve on it (use these files).

## Detecting the outage signature

23 of Llama-3.1-8B's 30 events executed against an unreachable endpoint while recording
`error: null` and `evaluator_fallback_used: false`. The reliable tell is **a flat
`round_jsd`** in the corresponding scored record — the same placeholder repeated at
every checkpoint. One Qwen2.5-14B unit, `C9_C_r1`, carries the same signature and could
not be repaired. Check before trusting any unit; see `00_docs/PROVENANCE.md` §2.2.

## Storage note

Within this archive as delivered, these files may be **hard-linked** to the working copy
they were assembled from. They are byte-identical, read-only research artifacts, and any
archiving tool (zip, tar, rsync) will materialise real content. If you intend to *edit*
a trace, copy it first.
