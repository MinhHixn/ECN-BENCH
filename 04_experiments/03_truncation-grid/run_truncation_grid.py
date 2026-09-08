#!/usr/bin/env python
"""Score the evidence-truncation grid built by build_truncation_inputs.py.

Two arms, one evaluator model, four evidence lengths:

  unconstrained -- chat_json is forced to send NO response_format at all. This is
                   the July 2026 condition: the keyword filter in the local
                   llm_client (`"r1" in model.lower()`) dropped structured-output
                   enforcement for the fixed DeepSeek-R1 evaluator, which is the
                   source-level defect Section~\\ref{sec:epistemic_mapping} documents.
  enforced      -- the pipeline's normal path: response_format json_object plus the
                   strict nested json_schema.

Holding the evaluator model fixed across arms is deliberate: it makes the contrast
"enforcement on/off", not "one model versus another", so the length x enforcement
interaction is identified.

Usage:
    python run_truncation_grid.py --arm unconstrained --level 2k [--events C1,C5]
    python run_truncation_grid.py --all            # every cell, sequentially
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEPLOY = HERE / "ECN-HPC-DEPLOY"
sys.path.insert(0, str(DEPLOY / "MiroFish-Offline" / "backend"))
sys.path.insert(0, str(DEPLOY))

from app.utils import llm_client as _llm  # noqa: E402

CAMPAIGN = HERE / "completed_benches/mistral-7b-awq/ecnbench_20260715T080203247382Z"
LEVELS = ["full", "8k", "5k", "2k"]

# An arm is an (evaluator, enforcement) pair. The q14b arms exist because
# qwen/qwen3-14b is the only comparison evaluator that reproduces the degeneracy at
# all (8/58 units, and 6 of those 8 are units Evaluator J also flattened), so it is
# the only accessible instrument on which a length titration has anything to titrate.
# The deepseek-r1 arms are the negative control: that model never returns a uniform
# vector, so its length curve should be flat by construction.
ARM_SPEC = {
    "unconstrained":     ("deepseek/deepseek-r1", False),
    "enforced":          ("deepseek/deepseek-r1", True),
    "q14b_unconstrained": ("qwen/qwen3-14b", False),
    "q14b_enforced":      ("qwen/qwen3-14b", True),
}
ARMS = list(ARM_SPEC)
DEFAULT_MODEL = None   # resolved from the arm unless --evaluator-model overrides it


def load_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return key
    for name in (".env", ".env.openrouter"):
        p = HERE / "MiroFish-Offline" / name
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("OPENROUTER_API_KEY="):
                return line.partition("=")[2].strip().strip('"').strip("'")
    raise SystemExit("no OPENROUTER_API_KEY in env or MiroFish-Offline/.env")


_BUDGET = 16000


def patch_common(min_budget: int) -> None:
    global _BUDGET
    _BUDGET = min_budget
    """Same two fixes as rescore_llama_fix.py: a budget a reasoning model can finish
    in, and never re.sub() on a null completion. Neither touches pipeline source."""
    orig_chat = _llm.LLMClient.chat

    def chat(self, *a, **kw):
        out = orig_chat(self, *a, **kw)
        return "" if out is None else out

    _llm.LLMClient.chat = chat
    _sub, _search = re.sub, re.search
    re.sub = lambda p, r, s, *a, **k: _sub(p, r, "" if s is None else s, *a, **k)
    re.search = lambda p, s, *a, **k: _search(p, "" if s is None else s, *a, **k)

    orig_chat_json = _llm.LLMClient.chat_json

    def chat_json(self, messages, temperature=None, max_tokens=2048, **kw):
        return orig_chat_json(self, messages, temperature=temperature,
                              max_tokens=max(max_tokens, min_budget), **kw)

    _llm.LLMClient.chat_json = chat_json


def patch_unconstrained() -> None:
    """Reproduce the July instrument: no JSON mode, no schema, free-form completion."""
    orig_chat_json = _llm.LLMClient.chat_json

    def chat_json(self, messages, temperature=None, max_tokens=2048,
                  repair_truncated_json=False, json_schema=None,
                  enforce_benchmark_params=True):
        # the budget must be raised here too: this replaces chat_json outright, so
        # the wrapper patch_common installed on chat_json is no longer in the path,
        # and the evaluator's own call site asks for only 1500 tokens -- less than a
        # reasoning model spends before it emits its first content token.
        raw = self.chat(
            messages=messages,
            temperature=0.0 if temperature is None else temperature,
            max_tokens=max(max_tokens, _BUDGET),
            response_format=None,                 # <- the defect being reproduced
            enforce_benchmark_params=enforce_benchmark_params,
        )
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", (raw or "").strip(),
                         flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", cleaned)
            if m:
                return json.loads(m.group(0))
            raise

    _llm.LLMClient.chat_json = chat_json
    _ = orig_chat_json


def run_cell(arm: str, level: str, model: str, events: str, concurrency: int,
             budget: int, api_key: str) -> None:
    fname = f"event_results_trunc_{level}_{arm}.json"
    target = CAMPAIGN / fname
    if not target.exists():
        raise SystemExit(f"missing {target} -- run build_truncation_inputs.py first")

    patch_common(budget)
    if not ARM_SPEC[arm][1]:
        patch_unconstrained()
    print(f"[grid] arm={arm} level={level} model={model} budget>={budget}")
    print(f"[grid] file {target.relative_to(HERE)}")

    argv = [
        "run_openrouter_eval_official.py",
        "--api-key", api_key,
        "--evaluator-model", model,
        "--target-model", "Mistral-7B-AWQ",
        "--base-workspace-dir", str(HERE),
        "--results-filename", fname,
        "--events-raw-path", str(HERE / "data" / "events_raw.json"),
        "--concurrency", str(concurrency),
    ]
    if events:
        argv += ["--events", events]
    sys.argv = argv
    import runpy
    runpy.run_path(str(DEPLOY / "run_openrouter_eval_official.py"), run_name="__main__")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--level", choices=LEVELS)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--events", default="")
    ap.add_argument("--evaluator-model", default=None,
                    help="override the model the arm implies")
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--max-tokens", type=int, default=16000)
    args = ap.parse_args()

    key = load_api_key()
    if args.all:
        raise SystemExit("--all runs 8 cells in one process; the arm patches are not "
                         "reversible in-process. Drive it from the shell, one cell per "
                         "process, e.g. a loop over --arm/--level.")
    if not (args.arm and args.level):
        raise SystemExit("give --arm and --level (or use the shell loop)")
    model = args.evaluator_model or ARM_SPEC[args.arm][0]
    run_cell(args.arm, args.level, model, args.events,
             args.concurrency, args.max_tokens, key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
