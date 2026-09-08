#!/usr/bin/env python3
"""Run Single-Agent RAG + Chain-of-Thought (CoT) baseline on 20 contamination-clean events across 4 models.

Evaluates 4 models:
1. Llama-3.1-8B: meta-llama/llama-3.1-8b-instruct
2. Mistral-8B: mistralai/ministral-8b-2512
3. Qwen2.5-7B: qwen/qwen-2.5-7b-instruct
4. Qwen3-14B: qwen/qwen3-14b

Runs 3 independent replicates (k=3) with high concurrency.
"""
import os, json, time, concurrent.futures, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE

# Updated 2026-08-21: grown from 17 to 20 events now that Qwen2.5-14B's six
# wrong-topic exclusions are recovered (see make_predictive_signal.py). NOT YET
# RE-RUN as of this edit -- single_agent_cot_baseline_results.json on disk still
# only covers the 17-event set; rerun this script (240 tasks, was 204) before
# trusting analyze_cot_baseline.py's output against the 20-event swarm figures.
CLEAN20 = ["C1", "C5", "C6", "C8", "C9", "C11", "C13", "C14", "C15",
           "S2", "S3", "S4", "S5", "S6", "S7", "S9", "T2", "T6", "T8", "T9"]
CLEAN17 = CLEAN20  # legacy alias so the rest of this file needs no other edits

MODELS = {
    "Llama-3.1-8B": "meta-llama/llama-3.1-8b-instruct",
    "Mistral-8B": "mistralai/ministral-8b-2512",
    "Qwen2.5-7B": "qwen/qwen-2.5-7b-instruct",
    "Qwen3-14B": "qwen/qwen3-14b",
}

with open(os.path.join(ROOT, 'MiroFish-Offline/.env'), 'r') as f:
    for line in f:
        if line.startswith('OPENROUTER_API_KEY='):
            API_KEY = line.split('=', 1)[1].strip()

# Load event metadata
with open(os.path.join(ROOT, 'completed_benches/mistral-7b-awq/ecnbench_20260715T080203247382Z/event_results_evaluatorB_openrouter.json'), 'r', encoding='utf-8') as f:
    eval_b = json.load(f)

event_meta = {}
for u in eval_b:
    eid = u['event_id']
    if eid in CLEAN17 and eid not in event_meta:
        event_meta[eid] = {
            'event_id': eid,
            'question': u['question'],
            'options': u['options'],
            'ground_truth': u['ground_truth']
        }

# Load injection bank
with open(os.path.join(ROOT, 'data/injections/step30_injection_bank.json'), 'r', encoding='utf-8') as f:
    bank = json.load(f)
inj_map = {e['event_id']: e for e in bank.get('events', [])}

# Load contexts
contexts = {}
for eid in CLEAN17:
    cpath = os.path.join(ROOT, f'data/seeds/{eid}/context.md')
    if os.path.exists(cpath):
        with open(cpath, 'r', encoding='utf-8') as cf:
            contexts[eid] = cf.read()
    else:
        contexts[eid] = ""

OUT_FILE = os.path.join(ROOT, 'single_agent_cot_baseline_results.json')

def call_openrouter(model_id, prompt, seed=42, temp=0.0):
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": "You are a world-class calibrated probabilistic superforecaster. Always reason carefully step-by-step and output strictly valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": temp,
        "seed": seed
    }
    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/chat/completions',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                content = data['choices'][0]['message']['content']
                return json.loads(content)
        except Exception as e:
            time.sleep(1.5 * (attempt + 1))
            if attempt == 4:
                raise e

def normalize_probs(raw_probs, options):
    opt_map = {o.casefold(): o for o in options}
    matched = {}
    if isinstance(raw_probs, dict):
        for k, v in raw_probs.items():
            k_clean = str(k).strip()
            matched_opt = opt_map.get(k_clean.casefold())
            if matched_opt:
                try:
                    matched[matched_opt] = float(v)
                except:
                    pass
    
    for o in options:
        if o not in matched:
            matched[o] = 0.0
            
    total = sum(matched.values())
    if total <= 0:
        return {o: 1.0 / len(options) for o in options}
    return {o: v / total for o, v in matched.items()}

def run_task(args):
    model_name, model_slug, eid, repeat, seed = args
    meta = event_meta[eid]
    ctx = contexts[eid]
    inj = inj_map.get(eid, {}).get('relevant_update', {})
    headline = inj.get('headline', '') if isinstance(inj, dict) else ''
    body = inj.get('body', '') if isinstance(inj, dict) else ''
    
    prompt = f"""You are an expert superforecaster and probabilistic reasoning engine.
Your task is to forecast the outcome of the following real-world event based on the Background Dossier and Breaking Market Intelligence.

---
EVENT QUESTION:
{meta['question']}

POSSIBLE OUTCOMES:
{json.dumps(meta['options'])}

---
BACKGROUND DOSSIER:
{ctx}

---
BREAKING MARKET INTELLIGENCE (LATEST UPDATE):
Headline: {headline}
Details: {body}

---
INSTRUCTIONS:
1. Conduct a thorough step-by-step Chain-of-Thought (CoT) analysis:
   - Evaluate base rates and historical priors from the background dossier.
   - Assess the specific diagnostic value and impact of the breaking market intelligence.
   - Formulate a well-calibrated probability distribution across all possible outcomes.
2. Return ONLY a valid JSON object matching this schema:
{{
  "reasoning": "Your step-by-step Chain-of-Thought reasoning here...",
  "probabilities": {{
    "<Exact Option 1>": 0.xx,
    "<Exact Option 2>": 0.xx
  }}
}}
All probabilities must be non-negative and sum to 1.0.
"""
    t0 = time.time()
    try:
        res = call_openrouter(model_slug, prompt, seed=seed, temp=0.0 if repeat==1 else 0.7)
        raw_probs = res.get('probabilities', {})
        probs = normalize_probs(raw_probs, meta['options'])
        gt = meta['ground_truth']
        
        # Compute Brier score
        brier = sum((probs.get(o, 0.0) - (1.0 if o == gt else 0.0)) ** 2 for o in meta['options'])
        
        # Compute directional accuracy
        max_p = max(probs.values())
        tied = [o for o, v in probs.items() if abs(v - max_p) < 1e-6]
        if len(tied) == 1:
            hit = 1.0 if tied[0].casefold() == str(gt).casefold() else 0.0
        else:
            hit = 1.0 / len(tied) if any(t.casefold() == str(gt).casefold() for t in tied) else 0.0
            
        dur = time.time() - t0
        
        reasoning_val = res.get("reasoning", "")
        reasoning_str = json.dumps(reasoning_val) if isinstance(reasoning_val, (dict, list)) else str(reasoning_val)
        
        return {
            "model": model_name,
            "model_slug": model_slug,
            "event_id": eid,
            "repeat": repeat,
            "seed": seed,
            "question": meta['question'],
            "options": meta['options'],
            "ground_truth": gt,
            "probabilities": probs,
            "brier": round(brier, 4),
            "hit": hit,
            "reasoning": reasoning_str[:300],
            "duration_s": round(dur, 2),
            "status": "success"
        }
    except Exception as e:
        return {
            "model": model_name,
            "model_slug": model_slug,
            "event_id": eid,
            "repeat": repeat,
            "seed": seed,
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    print(f"Starting High-Concurrency Single-Agent RAG+CoT benchmark on {len(CLEAN20)} Clean Events x {len(MODELS)} Models x 3 Repeats = {len(CLEAN20)*len(MODELS)*3} tasks...")
    tasks = []
    seeds = [42, 100, 2026]
    for mname, mslug in MODELS.items():
        for eid in CLEAN17:
            for rep_idx, seed in enumerate(seeds, start=1):
                tasks.append((mname, mslug, eid, rep_idx, seed))
                
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(run_task, t): t for t in tasks}
        completed = 0
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()
            results.append(res)
            completed += 1
            if completed % 20 == 0 or completed == len(tasks):
                print(f"Progress: {completed}/{len(tasks)} ({(completed/len(tasks)*100):.1f}%) completed...")
                with open(OUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2)

    success_cnt = sum(1 for r in results if r.get('status') == 'success')
    print(f"All {len(results)} tasks completed! ({success_cnt}/{len(results)} successful). Results saved to {OUT_FILE}")
