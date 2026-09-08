
import glob, json, os, time

print("\n=== STEP 2: COMPLETE AUDIT OF ALL 4 MODEL EVENT_RESULTS.JSON FILES ===")

model_files = [
    ("Llama-3.1-8B-AWQ", "/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ecnbench_workspace/simulation_logs/llama-3.1-8b-awq/ecnbench_20260811T211641407066Z/event_results.json"),
    ("Mistral-7B-AWQ", "/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ecnbench_workspace/simulation_logs/mistral-7b-awq/ecnbench_20260812T073651745891Z/event_results.json"),
    ("Qwen2.5-7B", "/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ecnbench_workspace/simulation_logs/qwen2.5_7b/ecnbench_20260812T085316759135Z/event_results.json"),
    ("Qwen2.5-14B", "/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ecnbench_workspace/simulation_logs/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete/event_results.json")
]

for model_name, path in model_files:
    print(f"\n==================================================")
    print(f"MODEL: {model_name}")
    print(f"Path: {path}")
    if os.path.exists(path):
        mtime = os.path.getmtime(path)
        dt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
        sz = os.path.getsize(path)
        print(f"Modified: {dt} | Size: {sz} bytes")
        
        try:
            data = json.load(open(path, encoding='utf-8'))
            total = len(data)
            valid_probs = sum(1 for r in data if r.get('probabilities'))
            valid_mcq = sum(1 for r in data if isinstance(r.get('mcq_dimensions'), dict) and len(r.get('mcq_dimensions')) >= 7)
            valid_micro = sum(1 for r in data if isinstance(r.get('micro_epistemic_mapping'), dict) and len(r.get('micro_epistemic_mapping')) >= 1)
            fallbacks = sum(1 for r in data if r.get('evaluator_fallback_used'))
            
            print(f"  Total Units: {total}")
            print(f"  Valid Probabilities: {valid_probs} / {total} ({valid_probs/max(1,total)*100:.1f}%)")
            print(f"  Valid 7-Dim MCQ Rubrics: {valid_mcq} / {total} ({valid_mcq/max(1,total)*100:.1f}%)")
            print(f"  Valid Micro-Epistemic Mappings: {valid_micro} / {total} ({valid_micro/max(1,total)*100:.1f}%)")
            print(f"  Evaluator Fallbacks Used: {fallbacks} / {total}")
            
            brier_scores = [r.get('brier') for r in data if r.get('brier') is not None]
            if brier_scores:
                print(f"  Brier Score Mean: {sum(brier_scores)/len(brier_scores):.4f} (Min: {min(brier_scores):.4f}, Max: {max(brier_scores):.4f})")
                
        except Exception as e:
            print(f"  [ERROR] Loading JSON: {e}")
    else:
        print("  [ERROR] File does not exist!")
