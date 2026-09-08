#!/usr/bin/env python
"""Re-score the repaired Llama-3.1-8B units with a token budget the reasoning
evaluator can actually finish in.

Why this wrapper exists
-----------------------
app/benchmarks/evaluator.py calls chat_json(max_tokens=1500) when micro_questions
are present. deepseek/deepseek-v4-flash-0731 is a reasoning model: on the rebuilt
~19k-character evidence it spends the whole budget on reasoning tokens and returns
finish_reason="length" with message.content = None. LLMClient.chat then does
re.sub(...) straight onto that None, so the unit dies with

    Evaluator scoring failed after 3 attempts:
    expected string or bytes-like object, got 'NoneType'

That is infrastructure loss, not a measurement: 15 of 34 units failed this way on
the first pass, and only 2 recovered on retry. The 2026-08-16 broken repair never
hit it because it scored every unit against an EMPTY evidence field, which keeps
the reasoning short -- the same defect that made that data invalid.

This wrapper raises the ceiling and leaves the repo's pipeline source untouched, so
previously published runs stay reproducible as they were. Nothing else about the
scoring path changes: same evaluator class, same prompt, same schema, same
temperature.

Usage:
    python rescore_llama_fix.py --results-filename <file.json> \
        --evaluator-model deepseek/deepseek-v4-flash-0731 [--max-tokens 6000]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEPLOY = HERE / "ECN-HPC-DEPLOY"
sys.path.insert(0, str(DEPLOY / "MiroFish-Offline" / "backend"))
sys.path.insert(0, str(DEPLOY))

from app.utils import llm_client as _llm  # noqa: E402

MIN_BUDGET = 6000


def install_patches(min_budget: int) -> None:
    """(1) give the reasoning evaluator room to finish; (2) never re.sub on None."""
    orig_chat_json = _llm.LLMClient.chat_json
    orig_chat = _llm.LLMClient.chat

    def chat_json(self, messages, temperature=None, max_tokens=2048, **kw):
        return orig_chat_json(self, messages, temperature=temperature,
                              max_tokens=max(max_tokens, min_budget), **kw)

    def chat(self, *a, **kw):
        out = orig_chat(self, *a, **kw)
        return "" if out is None else out

    _llm.LLMClient.chat_json = chat_json
    _llm.LLMClient.chat = chat

    # The None arrives inside orig_chat itself (content = response.choices[0]
    # .message.content, then re.sub on it), so also make re.sub/re.search tolerant
    # of None for the duration of this process only.
    _sub, _search = re.sub, re.search
    re.sub = lambda p, r, s, *a, **k: _sub(p, r, "" if s is None else s, *a, **k)
    re.search = lambda p, s, *a, **k: _search(p, "" if s is None else s, *a, **k)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-filename", required=True)
    ap.add_argument("--evaluator-model", default="deepseek/deepseek-v4-flash-0731")
    ap.add_argument("--events", default="")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=MIN_BUDGET)
    ap.add_argument("--api-key", default=os.environ.get("OPENROUTER_API_KEY", ""))
    args = ap.parse_args()

    install_patches(args.max_tokens)
    print(f"[patch] evaluator token budget raised to >= {args.max_tokens}")
    print(f"[patch] null completion content coerced to '' (triggers the normal retry)")

    argv = [
        "run_openrouter_eval_official.py",
        "--api-key", args.api_key,
        "--evaluator-model", args.evaluator_model,
        "--target-model", "Llama-3.1-8B-AWQ",
        "--base-workspace-dir", str(HERE),
        "--results-filename", args.results_filename,
        "--events-raw-path", str(HERE / "data" / "events_raw.json"),
        "--concurrency", str(args.concurrency),
    ]
    if args.events:
        argv += ["--events", args.events]

    sys.argv = argv
    import runpy
    runpy.run_path(str(DEPLOY / "run_openrouter_eval_official.py"), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
