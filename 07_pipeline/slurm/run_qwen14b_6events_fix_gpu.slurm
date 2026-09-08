#!/bin/bash
#SBATCH --job-name=ecn-qwen14b-6events-fix
#SBATCH --account=gem
#SBATCH -p gpu
#SBATCH --qos=medium
#SBATCH --nodes=1
#SBATCH --gres=gpu:2
#SBATCH --constraint=gpu_a100
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY/logs/qwen14b_6events_fix_%j.log
#SBATCH --error=/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY/logs/qwen14b_6events_fix_%j.log

# =============================================================================
# ECN-BENCH: 6 Missing/Excluded Events Fix for Qwen2.5-14B (T3, T4, T5, T6, C6, T8)
# Target Model: qwen2.5:14b | Evaluator: deepseek-r1-14b
# Agents: 300 | Rounds: 60 | Repeats: 1
# =============================================================================

source /etc/profile.d/modules.sh 2>/dev/null || true
module load apptainer 2>/dev/null || true
USER_ID=$(whoami)
PROJECT_ROOT="/scratch/waves/users/$USER_ID/ECN-HPC-DEPLOY"
SCRATCH_DIR="/scratch/nautilus/users/$USER_ID/ecnbench"
WAVES_SCRATCH="/scratch/waves/users/$USER_ID/ecnbench_workspace"
SIF_PATH="$SCRATCH_DIR/vllm_v0.6.3.sif"
export PATH="$HOME/ecnbench/bin:$PATH"
export HF_HOME="$SCRATCH_DIR/hf_cache"
export HF_HUB_OFFLINE=1

mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$WAVES_SCRATCH/simulation_logs"
OUTLINES_JOB_CACHE="$WAVES_SCRATCH/outlines_qwen14b_6events_${SLURM_JOB_ID}"

# 6 Target Events
AGENT_COUNT=300
ROUNDS=60
EVENT_IDS="T3,T4,T5,T6,C6,T8"
EVAL_MODEL_ID="/scratch/waves/users/$USER_ID/ecnbench/hf_cache/models--deepseek-ai--DeepSeek-R1-Distill-Qwen-14B/snapshots/1df8507178afcc1bef68cd8c393f61a886323761"

echo "=================================================="
echo "STARTING 6 EXCLUDED EVENTS RE-RUN FOR QWEN2.5-14B"
echo "Events: $EVENT_IDS"
echo "Agents: $AGENT_COUNT | Rounds: $ROUNDS"
echo "=================================================="

# 1. Boot Isolated Neo4j
echo "--- Starting Isolated Neo4j ---"
export JAVA_HOME="$SCRATCH_DIR/java17/jdk-17.0.11+9"
export PATH="$JAVA_HOME/bin:$PATH"

BOLT_PORT=$((10000 + RANDOM % 10000))
HTTP_PORT=$((20000 + RANDOM % 10000))
VLLM_EVAL_PORT=$((50000 + RANDOM % 10000))
export NEO4J_URI="bolt://localhost:$BOLT_PORT"

JOB_NEO4J_DIR="/scratch/waves/users/$USER_ID/ecnbench_workspace/neo4j_qwen14b_6events_${SLURM_JOB_ID}"
mkdir -p "$JOB_NEO4J_DIR/conf" "$JOB_NEO4J_DIR/data"
cp "$SCRATCH_DIR/neo4j-community-5.15.0/conf/neo4j.conf" "$JOB_NEO4J_DIR/conf/neo4j.conf"
{
  echo "server.directories.data=$JOB_NEO4J_DIR/data"
  echo "server.directories.run=$JOB_NEO4J_DIR"
  echo "server.bolt.listen_address=0.0.0.0:$BOLT_PORT"
  echo "server.http.listen_address=127.0.0.1:$HTTP_PORT"
  echo "dbms.security.auth_enabled=false"
} >> "$JOB_NEO4J_DIR/conf/neo4j.conf"
export NEO4J_CONF="$JOB_NEO4J_DIR/conf"
$SCRATCH_DIR/neo4j-community-5.15.0/bin/neo4j start
sleep 20

# 2. Ollama on GPU 0
echo "--- Starting Ollama Server on GPU 0 ---"
export OLLAMA_MODELS="$SCRATCH_DIR/ollama_storage"
export OLLAMA_NUM_PARALLEL=2
export OLLAMA_CONTEXT_LENGTH=8192
export OLLAMA_NUM_CTX=8192
CUDA_VISIBLE_DEVICES=0 $HOME/ecnbench/bin/ollama serve > "$PROJECT_ROOT/logs/ollama_qwen14b_6events_${SLURM_JOB_ID}.log" 2>&1 &
sleep 15

# 3. vLLM Evaluator Server on GPU 1 (DeepSeek-R1-14B)
echo "--- Starting vLLM Evaluator Server on GPU 1 (Port $VLLM_EVAL_PORT) ---"
CUDA_VISIBLE_DEVICES=1 apptainer run --nv \
  -B /scratch:/scratch \
  --env OUTLINES_CACHE_DIR="${OUTLINES_JOB_CACHE}_eval" \
  --env HF_HOME="$HF_HOME" \
  --env HF_HUB_OFFLINE=1 \
  --env VLLM_ALLOW_LONG_MAX_MODEL_LEN=1 \
  "$SIF_PATH" \
  --model "$EVAL_MODEL_ID" \
  --served-model-name "deepseek-r1-14b" \
  --tensor-parallel-size 1 \
  --port $VLLM_EVAL_PORT \
  --gpu-memory-utilization 0.85 \
  --max-model-len 8192 \
  --enforce-eager \
  --trust-remote-code > "$PROJECT_ROOT/logs/vllm_eval_qwen14b_6events_${SLURM_JOB_ID}.log" 2>&1 &

echo "Waiting for servers to start..."
MAX_WAIT=600; WAIT_TIME=0
check_port() {
  python3 -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('127.0.0.1',$1)); s.close()" 2>/dev/null
}
while ! (check_port 11434 && check_port $VLLM_EVAL_PORT); do
  sleep 10; WAIT_TIME=$((WAIT_TIME + 10))
  if [ $WAIT_TIME -ge $MAX_WAIT ]; then echo "TIMEOUT: servers failed to start"; exit 1; fi
  echo "Still waiting ($WAIT_TIME/$MAX_WAIT)..."
done
echo "Both Ollama & vLLM Servers Ready!"

# 4. Execute Simulation Protocol for 6 Events
cd "$PROJECT_ROOT/MiroFish-Offline/backend"
source /scratch/waves/users/$USER_ID/project_backup/MiroFish-Offline/backend/venv/bin/activate

export LLM_BASE_URL="http://localhost:11434/v1"
export OPENROUTER_BASE_URL="http://localhost:11434/v1"
export GRAPH_LLM_BASE_URL="http://localhost:11434/v1"
export EVALUATOR_LLM_BASE_URL="http://localhost:$VLLM_EVAL_PORT/v1"
export BENCHMARK_LLM_BASE_URL="http://localhost:11434/v1"
export OPENROUTER_BENCHMARK_MODEL="qwen2.5:14b"
export OPENROUTER_GRAPH_MODEL="qwen2.5:14b"
export OPENROUTER_EVALUATOR_MODEL="deepseek-r1-14b"
export LLM_MODEL_NAME="qwen2.5:14b"
export BENCHMARK_MODE='true'
export DEV_MINIMAL_MODE='true'
export DEV_MINIMAL_SKIP_A_EVALUATION='False'
export LLM_TIMEOUT_SECONDS='1800'
export TIKTOKEN_CACHE_DIR="/scratch/nautilus/users/$USER_ID/ecnbench/tiktoken_cache"
export DEV_MINIMAL_AGENT_COUNT="$AGENT_COUNT"
export DEV_MINIMAL_MAX_STEPS="$ROUNDS"
export DEV_MINIMAL_INJECTION_STEP=$((ROUNDS / 2))
export LLM_API_KEY='dummy'
export EMBEDDING_BASE_URL='http://localhost:11434'
export LLM_USE_JSON_SCHEMA='False'
export BUST_PERSONA_CHECKPOINT='true'
export DISABLE_TOOL_USE='false'
export ENABLE_FJ_ANCHORING='True'
export ENABLE_MEAN_FIELD_AGGREGATION='True'

OUTPUT_DIR="$WAVES_SCRATCH/simulation_logs/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete"
mkdir -p "$OUTPUT_DIR"

echo "Executing scripts/run_ecnbench_protocol.py for events: $EVENT_IDS"
date +"start %Y-%m-%dT%H:%M:%S"

python scripts/run_ecnbench_protocol.py \
  --seeds-dir ../../data/seeds \
  --events-raw ../../data/events_raw.json \
  --injection-bank ../../data/injections/step30_injection_bank.json \
  --output-dir "$OUTPUT_DIR" \
  --event-ids "$EVENT_IDS" \
  --repeats 1

date +"end %Y-%m-%dT%H:%M:%S"
echo "6-EVENTS FIX COMPLETED SUCCESSFULLY!"

# 5. Cleanup
pkill -f vllm
pkill -f ollama
NEO4J_CONF="$JOB_NEO4J_DIR/conf" $SCRATCH_DIR/neo4j-community-5.15.0/bin/neo4j stop
rm -rf "$JOB_NEO4J_DIR" "$OUTLINES_JOB_CACHE"*
