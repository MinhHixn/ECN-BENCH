#!/usr/bin/env python3
"""Rebuild the working layout the analysis scripts expect.

The scripts in this archive were written to run from the original repository root,
where the scored campaigns sit at `completed_benches/<model>/<campaign_id>/` next to
the scripts themselves. This archive is organised for *readers* instead, so paths
differ. Running this script once materialises a `_workspace/` directory with the
original layout, after which every command in `00_docs/REPRODUCE.md` works unmodified:

    python 05_analysis/make_workspace.py
    cd _workspace
    python make_predictive_signal.py

Raw simulation traces are hard-linked, so `_workspace/` costs almost no additional
disk space despite containing the full 2.3 GB of transcripts. Everything a script
might *write* — scored records, analysis JSONs, figures — is copied instead, so
re-running an analysis can never modify the released archive. Nothing outside
`_workspace/` is written or modified.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REL = os.path.dirname(HERE)
WS = os.path.join(REL, "_workspace")

CAMPAIGNS = {
    "llama-3.1-8b-awq": "ecnbench_20260714T173650169846Z",
    "mistral-7b-awq": "ecnbench_20260715T080203247382Z",
    "qwen2.5_7b": "ecnbench_20260717T154127454597Z",
    "qwen2.5-14b-awq": "ecnbench_20260727_qwen14b_complete",
}

n_link = n_copy = 0


def place(src, dst, link=False):
    """Copy src to dst. With link=True, hard-link instead (read-only inputs only).

    Anything a script may overwrite MUST be copied: a hard link shares the inode,
    so writing through the workspace copy would silently rewrite the archive.
    """
    global n_link, n_copy
    if not os.path.isfile(src):
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    if link:
        try:
            os.link(src, dst)
            n_link += 1
            return True
        except OSError:
            pass
    shutil.copy2(src, dst)
    n_copy += 1
    return True


def place_tree(src_dir, dst_dir, link=False):
    if not os.path.isdir(src_dir):
        return
    for dp, _dn, fn in os.walk(src_dir):
        rel = os.path.relpath(dp, src_dir)
        target = dst_dir if rel == "." else os.path.join(dst_dir, rel)
        for f in fn:
            place(os.path.join(dp, f), os.path.join(target, f), link=link)


def main():
    if os.path.exists(WS):
        print(f"'{WS}' already exists.")
        if input("Remove and rebuild? [y/N] ").strip().lower() != "y":
            print("Aborted; nothing changed.")
            return 1
        shutil.rmtree(WS)

    print("Building _workspace/ ...")

    # 1. campaigns: scored records + raw traces, under their original campaign ids
    for model, camp in CAMPAIGNS.items():
        dst = os.path.join(WS, "completed_benches", model, camp)
        place_tree(os.path.join(REL, "02_campaigns", model), dst)          # copied
        place_tree(os.path.join(REL, "03_traces", model), dst, link=True)  # read-only
        print(f"  completed_benches/{model}/{camp}")

    # 2. the truncation arms live inside the Mistral campaign dir in the original layout
    place_tree(
        os.path.join(REL, "04_experiments", "03_truncation-grid", "scored_arms"),
        os.path.join(WS, "completed_benches", "mistral-7b-awq",
                     CAMPAIGNS["mistral-7b-awq"]),
    )

    # 3. the benchmark definition, at the path run_manifest.json records
    place_tree(os.path.join(REL, "01_benchmark"), os.path.join(WS, "data"))

    # 4. analysis + experiment scripts and their inputs/outputs, flat at the root
    for sub in (
        os.path.join("04_experiments", "01_evaluator-replication"),
        os.path.join("04_experiments", "02_degeneracy-transfer"),
        os.path.join("04_experiments", "03_truncation-grid"),
        os.path.join("04_experiments", "04_single-agent-cot-baseline"),
        os.path.join("05_analysis", "scripts"),
        os.path.join("05_analysis", "outputs"),
    ):
        src = os.path.join(REL, sub)
        if not os.path.isdir(src):
            continue
        for f in sorted(os.listdir(src)):
            p = os.path.join(src, f)
            if os.path.isfile(p):
                place(p, os.path.join(WS, f))

    # build_reproducibility_analysis.py resolves ROOT as its parent's parent
    place(os.path.join(REL, "07_pipeline", "hpc", "build_reproducibility_analysis.py"),
          os.path.join(WS, "ECN-HPC-DEPLOY", "build_reproducibility_analysis.py"))

    # the simulation/scoring engine, at the path the scripts add to sys.path
    place_tree(os.path.join(REL, "07_pipeline", "backend"),
               os.path.join(WS, "MiroFish-Offline", "backend"))

    # 5. figures, so figure scripts overwrite in place rather than creating strays
    place_tree(os.path.join(REL, "06_figures"), WS)

    print(f"\n  hard-linked {n_link} files, copied {n_copy}")
    print(f"\nWorkspace ready:  {WS}")
    print("\nNext:")
    print("  cd _workspace")
    print("  python ECN-HPC-DEPLOY/build_reproducibility_analysis.py")
    print("  python make_predictive_signal.py")
    print("  python analyze_cot_baseline.py && python make_cot_baseline_figure.py")
    print("  python analyze_degeneracy_transfer.py")
    print("  python analyze_truncation_grid.py")
    print("\nSee 00_docs/REPRODUCE.md for what each command regenerates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
