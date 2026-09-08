
import glob, os, sys

search_roots = [
    "/scratch/waves/users/mhnguyn2025@ec-nantes.fr/",
    "/scratch/nautilus/users/mhnguyn2025@ec-nantes.fr/"
]

found_dirs = {}
for root in search_roots:
    for p in glob.glob(root + "/**/actions.jsonl", recursive=True):
        if "14b" in p.lower() or "qwen2.5-14b" in p.lower() or "qwen2.5_14b" in p.lower() or "qwen14b" in p.lower():
            parent_dir = os.path.dirname(os.path.dirname(p)) # campaign root
            found_dirs[parent_dir] = found_dirs.get(parent_dir, 0) + 1

print(f"Found {len(found_dirs)} Qwen14B simulation campaign directories:")
for d, unit_cnt in found_dirs.items():
    print(f"  Directory: {d} -> Total actions.jsonl files: {unit_cnt}")
