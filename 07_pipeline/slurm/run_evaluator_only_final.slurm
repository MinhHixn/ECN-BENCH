#!/bin/bash
#SBATCH --job-name=ecn-evaluator-only
#SBATCH --account=gem
#SBATCH -p gpu
#SBATCH --qos=short
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --constraint=gpu_a100
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY/logs/evaluator_only_%j.log
#SBATCH --error=/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY/logs/evaluator_only_%j.log

source /etc/profile.d/modules.sh 2>/dev/null || true
module load apptainer 2>/dev/null || true
USER_ID=$(whoami)
PROJECT_ROOT="/scratch/waves/users/$USER_ID/ECN-HPC-DEPLOY"
SCRATCH_DIR="/scratch/nautilus/users/$USER_ID/ecnbench"
SIF_PATH="$SCRATCH_DIR/vllm_v0.6.3.sif"
EVAL_MODEL_ID="/scratch/waves/users/$USER_ID/ecnbench/hf_cache/models--deepseek-ai--DeepSeek-R1-Distill-Qwen-14B/snapshots/1df8507178afcc1bef68cd8c393f61a886323761"

export VLLM_PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()' 2>/dev/null || echo 58734)

echo "=================================================="
echo "STARTING DEDICATED EVALUATOR JOB (DeepSeek-R1-14B)"
echo "Port: $VLLM_PORT"
echo "=================================================="

mkdir -p "$PROJECT_ROOT/logs"

# Start vLLM using nohup with stdin redirection so it doesn't get EOF
nohup apptainer run --nv \
  -B /scratch:/scratch \
  "$SIF_PATH" \
  --model "$EVAL_MODEL_ID" \
  --served-model-name "deepseek-r1-14b" \
  --port "$VLLM_PORT" \
  --gpu-memory-utilization 0.85 \
  --max-model-len 8192 \
  --trust-remote-code < /dev/null > "$PROJECT_ROOT/logs/vllm_evaluator_only_${SLURM_JOB_ID}.log" 2>&1 &

VLLM_PID=$!
trap "kill -9 $VLLM_PID 2>/dev/null || true" EXIT

source /scratch/waves/users/$USER_ID/project_backup/MiroFish-Offline/backend/venv/bin/activate

python "$PROJECT_ROOT/run_hpc_evaluator_standalone.py"

echo "EVALUATOR JOB FINISHED SUCCESSFULLY!"
