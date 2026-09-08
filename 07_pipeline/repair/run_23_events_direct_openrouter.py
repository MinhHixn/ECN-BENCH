import os
import sys
import paramiko

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def test_benchmark_mode_false():
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

        print("[OK] Connected to nautilus-devel-001!")

        remote_cmd = """
        USER_ID=$(whoami)
        WAVES_DIR="/scratch/waves/users/$USER_ID/ecnbench_workspace"
        PROJECT_ROOT="/scratch/waves/users/$USER_ID/ECN-HPC-DEPLOY"
        
        mkdir -p "$WAVES_DIR/simulation_logs"
        mkdir -p "$PROJECT_ROOT/logs"

        cat << 'EOF' > "$WAVES_DIR/run_openrouter_direct.sh"
#!/bin/bash
USER_ID=$(whoami)
WAVES_DIR="/scratch/waves/users/$USER_ID/ecnbench_workspace"
PROJECT_ROOT="/scratch/waves/users/$USER_ID/ECN-HPC-DEPLOY"

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY

export OPENROUTER_API_KEY="REDACTED_SET_OPENROUTER_API_KEY"
export OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

export OPENROUTER_BENCHMARK_MODEL="meta-llama/llama-3.1-8b-instruct"
export OPENROUTER_GRAPH_MODEL="meta-llama/llama-3.1-8b-instruct"
export OPENROUTER_EVALUATOR_MODEL="deepseek/deepseek-v4-flash-0731"

export LLM_BASE_URL="https://openrouter.ai/api/v1"
export EVALUATOR_LLM_BASE_URL="https://openrouter.ai/api/v1"
export GRAPH_LLM_BASE_URL="https://openrouter.ai/api/v1"

# Unset strict BENCHMARK_MODE to allow mock telemetry when Neo4j/Java17 is unavailable on Waves
export BENCHMARK_MODE='false'
export DEV_MINIMAL_MODE='true'
export TELEMETRY_REQUIRED='false'
export ENABLE_TELEMETRY_PROBES='false'
export DEV_MINIMAL_SKIP_EVALUATOR='true'
export DEV_MINIMAL_SKIP_A_EVALUATION='true'

export DEV_MINIMAL_AGENT_COUNT='300'
export DEV_MINIMAL_MAX_STEPS='60'
export DEV_MINIMAL_INJECTION_STEP='30'
export LLM_TIMEOUT_SECONDS='1800'
export LLM_USE_JSON_SCHEMA='True'

EVENTS_23_LIST="S9,T1,T2,T3,T4,T5,T6,T8,T9,C1,C2,C4,C5,C6,C7,C8,C9,C10,C11,C12,C13,C14,C15"

if [ -f "/scratch/waves/users/$USER_ID/project_backup/MiroFish-Offline/backend/venv/bin/activate" ]; then
    source "/scratch/waves/users/$USER_ID/project_backup/MiroFish-Offline/backend/venv/bin/activate"
    CD_PATH="/scratch/waves/users/$USER_ID/project_backup/MiroFish-Offline/backend"
else
    CD_PATH="$PROJECT_ROOT/MiroFish-Offline/backend"
fi

cd "$CD_PATH"
python3.11 scripts/run_ecnbench_protocol.py \
  --seeds-dir ../../data/seeds \
  --events-raw ../../data/events_raw.json \
  --injection-bank ../../data/injections/step30_injection_bank.json \
  --output-dir "$WAVES_DIR/simulation_logs" \
  --event-ids "$EVENTS_23_LIST" \
  --repeats 1 > "$WAVES_DIR/openrouter_23events.log" 2>&1 &

echo $! > "$WAVES_DIR/openrouter_23events.pid"
echo "Process started with PID $(cat $WAVES_DIR/openrouter_23events.pid)"
EOF

        chmod +x "$WAVES_DIR/run_openrouter_direct.sh"
        bash "$WAVES_DIR/run_openrouter_direct.sh"
        """

        stdin, stdout, stderr = nautilus_client.exec_command(remote_cmd)
        output = stdout.read().decode('utf-8', errors='ignore')
        print("Execution Output:\n", output)

        nautilus_client.close()
        bastion_client.close()

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")

if __name__ == "__main__":
    test_benchmark_mode_false()
