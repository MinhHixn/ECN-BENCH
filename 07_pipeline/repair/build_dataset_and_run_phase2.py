import os
import sys
import paramiko
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def build_merged_and_run_phase2():
    print("=============================================================")
    print("BUILDING COMPLETE 23-EVENT DATASET & LAUNCHING PHASE 2 RE-SCORING")
    print("=============================================================")

    key_path = os.path.expanduser("~/.ssh/id_ed25519")
    passphrase = "TPGVision"
    user = "mhnguyn2025@ec-nantes.fr"
    bastion_host = "bastion.glicid.fr"
    nautilus_host = "nautilus-devel-001.nautilus.intra.glicid.fr"

    try:
        pkey = paramiko.Ed25519Key.from_private_key_file(key_path, password=passphrase) if os.path.exists(key_path) else None
        bastion_client = paramiko.SSHClient()
        bastion_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if pkey:
            bastion_client.connect(bastion_host, username=user, pkey=pkey, look_for_keys=False, allow_agent=False)
        else:
            bastion_client.connect(bastion_host, username=user, password=passphrase)

        bastion_transport = bastion_client.get_transport()
        channel = bastion_transport.open_channel("direct-tcpip", (nautilus_host, 22), ('127.0.0.1', 0))

        nautilus_client = paramiko.SSHClient()
        nautilus_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if pkey:
            nautilus_client.connect(nautilus_host, username=user, pkey=pkey, sock=channel, look_for_keys=False, allow_agent=False)
        else:
            nautilus_client.connect(nautilus_host, username=user, password=passphrase, sock=channel)

        build_script = """
        USER_ID=$(whoami)
        WAVES_DIR="/scratch/waves/users/$USER_ID/ecnbench_workspace"
        PROJECT_ROOT="/scratch/waves/users/$USER_ID/ECN-HPC-DEPLOY"
        API_KEY="REDACTED_SET_OPENROUTER_API_KEY"

        RECOVERY_DIR="$WAVES_DIR/simulation_logs/llama_23events_recovery"
        TARGET_DIR="$PROJECT_ROOT/completed_benches/llama-3.1-8b-awq/ecnbench_20260714T173650169846Z"
        DEST_JSON="$TARGET_DIR/event_results_llama_23events_recovery.json"
        EVENTS_RAW="$PROJECT_ROOT/data/events_raw.json"

        mkdir -p "$TARGET_DIR"

        # Python script to (re)build event_results rows from all unit directories.
        # Merges with any existing DEST_JSON so already-scored rows (real OpenRouter
        # probabilities, evaluator_fallback_used=False) are never clobbered -- only
        # missing/still-fallback units get (re)built from the raw simulation output.
        python3.11 -c "
import glob, os, json

rec_dir = '$RECOVERY_DIR'
dest_json = '$DEST_JSON'
events_raw_path = '$EVENTS_RAW'
TARGET_EVENTS = ['S9','T1','T2','T3','T4','T5','T6','T8','T9','C1','C2','C4','C5','C6','C7','C8','C9','C10','C11','C12','C13','C14','C15']

# events_by_id, same lookup convention as run_openrouter_eval_official.py
raw = json.load(open(events_raw_path, encoding='utf-8'))
events_by_id = {}
for cat_events in raw.get('core_events', {}).values():
    for e in cat_events:
        events_by_id[e['id']] = e
for e in raw.get('supplementary_events', {}).get('events', []):
    events_by_id[e['id']] = e

# Preserve any already-scored rows from a prior run.
existing_by_key = {}
if os.path.exists(dest_json):
    try:
        for r in json.load(open(dest_json, encoding='utf-8')):
            k = (r.get('event_id'), r.get('condition'), r.get('repeat'))
            existing_by_key[k] = r
    except Exception:
        pass

unit_dirs = sorted(glob.glob(f'{rec_dir}/**/*_r1', recursive=True))

rows = []
seen = set()

for u in unit_dirs:
    unit_name = os.path.basename(u) # e.g. S9_A_r1
    parts = unit_name.split('_')
    if len(parts) < 3:
        continue
    event_id = parts[0]
    condition = parts[1]
    repeat = int(parts[2].replace('r', ''))

    key = (event_id, condition, repeat)
    if key in seen:
        continue
    seen.add(key)

    prior = existing_by_key.get(key)
    if prior is not None and not prior.get('evaluator_fallback_used', True):
        # Already scored for real in a previous Phase 2 pass -- keep as-is.
        rows.append(prior)
        continue

    cfg_file = os.path.join(u, 'simulation_config.json')
    question = ''
    options = []
    evidence_text = ''
    if os.path.exists(cfg_file):
        try:
            cfg = json.load(open(cfg_file))
            question = cfg.get('question', '')
            options = cfg.get('options', [])
            evidence_text = cfg.get('evidence_text', '')
        except Exception:
            pass

    event_obj = events_by_id.get(event_id, {})
    ground_truth = str(event_obj.get('outcome') or event_obj.get('answer') or '')

    row = {
        'event_id': event_id,
        'unit_id': f'{event_id}_{condition}_r{repeat}',
        'condition': condition,
        'repeat': repeat,
        'question': question,
        'options': options,
        'evidence_text': evidence_text,
        'ground_truth': ground_truth,
        'evaluator_fallback_used': True,
        'evaluator_fallback_reason': 'dev_minimal_skip_evaluator',
        'evaluator_fallback_source': 'dev_minimal_default_probabilities'
    }
    rows.append(row)

# Carry over any previously-scored rows whose unit dir wasn't found this pass
# (e.g. simulation dir since cleaned up) rather than silently dropping them.
for k, r in existing_by_key.items():
    if k not in seen:
        rows.append(r)

rows.sort(key=lambda r: (r['event_id'], r['condition'], r['repeat']))

with open(dest_json, 'w') as f:
    json.dump(rows, f, indent=2)

kept_real = sum(1 for r in rows if not r.get('evaluator_fallback_used', True))
events_present = sorted(set(r['event_id'] for r in rows))
missing_events = [e for e in TARGET_EVENTS if e not in events_present]
no_ground_truth = [r['unit_id'] for r in rows if not r.get('ground_truth')]

print(f'Wrote {len(rows)} unit rows to {dest_json}')
print(f'  already-scored rows kept as-is: {kept_real}')
print(f'  events present ({len(events_present)}/{len(TARGET_EVENTS)}): {events_present}')
print(f'  MISSING events (no unit dirs found yet): {missing_events}')
print(f'  rows with empty ground_truth ({len(no_ground_truth)}): {no_ground_truth[:10]}')
"

        echo "--- LAUNCHING PHASE 2 OFFICIAL OPENROUTER RE-SCORING ---"
        export PYTHONPATH="$PROJECT_ROOT/MiroFish-Offline/backend:$PROJECT_ROOT:$PYTHONPATH"
        unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY

        VENV_PY="/scratch/waves/users/$USER_ID/project_backup/MiroFish-Offline/backend/venv/bin/python3.11"
        cd "$PROJECT_ROOT"
        # No --events filter: auto-repair mode only touches rows that are still
        # evaluator_fallback_used / missing mcq_dimensions, so the rows already
        # scored for real in a prior pass are never re-sent to the judge.
        $VENV_PY run_openrouter_eval_official.py \
          --api-key "$API_KEY" \
          --evaluator-model deepseek/deepseek-v4-flash-0731 \
          --target-model Llama-3.1-8B-AWQ \
          --base-workspace-dir "$PROJECT_ROOT" \
          --results-filename event_results_llama_23events_recovery.json \
          --concurrency 6 > "$WAVES_DIR/phase2_rescore.log" 2>&1 &

        echo $! > "$WAVES_DIR/phase2_rescore.pid"
        echo "Phase 2 Re-scoring started with PID $(cat $WAVES_DIR/phase2_rescore.pid)"
        """

        stdin, stdout, stderr = nautilus_client.exec_command(build_script)
        print("Launch Output:\n", stdout.read().decode('utf-8', errors='ignore'))

        nautilus_client.close()
        bastion_client.close()

    except Exception as e:
        print(f"[ERROR]: {e}")

if __name__ == "__main__":
    build_merged_and_run_phase2()
