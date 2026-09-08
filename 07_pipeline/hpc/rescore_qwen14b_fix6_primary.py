#!/usr/bin/env python
"""Re-score the qwen14b-fix6 primary pass with a token budget deepseek/deepseek-r1
can actually fit in its context window.

Why this wrapper exists
------------------------
app/benchmarks/evaluator.py hardcodes chat_json(max_tokens=65536) at its call
site, on the assumption "this evaluator's model has a 1M-token context window"
(true for deepseek/deepseek-v4-flash-0731, the model that comment was written
for). deepseek/deepseek-r1 (used here as the primary-pass substitute for the
unreachable local DeepSeek-R1-14B endpoint, same substitution the 2026-08-16
Llama repair used) only has a 64000-token context on OpenRouter, so requesting
max_tokens=65536 alone overflows it before any input is even counted --
every one of the first 18 units failed immediately with HTTP 400 "maximum
context length is 64000 tokens... requested about 69302 tokens", 0/18 scored.

This wrapper caps (not floors) chat_json's max_tokens at a value comfortably
inside deepseek-r1's window even accounting for our largest observed evidence
input (~3.8k tokens) and reasoning overhead, while staying well above the
6000-16000 floor already established (2026-08-16 Llama repair) as enough room
for the schema's own JSON output (probabilities + 7 MCQ dims + validated_scales
+ micro mappings). Leaves the repo's pipeline source untouched.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent  # ECN-HPC-DEPLOY on the HPC side
sys.path.insert(0, str(HERE / "MiroFish-Offline" / "backend"))
sys.path.insert(0, str(HERE))

from app.utils import llm_client as _llm  # noqa: E402

CAP = 16000


def install_cap(cap: int) -> None:
    orig_chat_json = _llm.LLMClient.chat_json

    def chat_json(self, messages, temperature=None, max_tokens=2048, **kw):
        return orig_chat_json(self, messages, temperature=temperature,
                               max_tokens=min(max_tokens, cap), **kw)

    _llm.LLMClient.chat_json = chat_json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-filename", required=True)
    ap.add_argument("--evaluator-model", default="deepseek/deepseek-r1")
    ap.add_argument("--target-model", default="Qwen2.5-14B")
    ap.add_argument("--events", default="")
    ap.add_argument("--events-raw-path", required=True)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--max-tokens-cap", type=int, default=CAP)
    ap.add_argument("--api-key", default=os.environ.get("OPENROUTER_API_KEY", ""))
    args = ap.parse_args()

    install_cap(args.max_tokens_cap)
    print(f"[patch] evaluator token budget capped at <= {args.max_tokens_cap} "
          f"(was hardcoded 65536, overflowed deepseek-r1's 64k context)")

    argv = [
        "run_openrouter_eval_official.py",
        "--api-key", args.api_key,
        "--evaluator-model", args.evaluator_model,
        "--target-model", args.target_model,
        "--base-workspace-dir", str(HERE),
        "--results-filename", args.results_filename,
        "--events-raw-path", args.events_raw_path,
        "--concurrency", str(args.concurrency),
    ]
    if args.events:
        argv += ["--events", args.events]

    sys.argv = argv
    import runpy
    runpy.run_path(str(HERE / "run_openrouter_eval_official.py"), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
