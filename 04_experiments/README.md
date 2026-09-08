# Previously collected follow-up observations

The evaluator replication, degeneracy-transfer, truncation grid and single-agent CoT observations were collected before this revision. No new observations were collected on September 6.

Use `../05_analysis/scripts/paper_analysis.py` to reanalyse the current manuscript. Other analyses and their old outputs in these subdirectories are historical. In particular:
- Transfer counts are conditioned on usable responses, with missing responses disclosed.
- Truncation changes content and speaker coverage as well as length.
- Enforcement labels indicate requested constraints, not verified strict-schema acceptance.
- Repeated length/condition readings are paired within events.
- CoT has two checkpoint-matched and two unmatched arms, unequal serving and mixed temperatures.
- There is no single-agent null-injection arm, so deliberation-specific content sensitivity is not identified.

Generation scripts may call paid model endpoints. They are not invoked by the offline reproduction command.

