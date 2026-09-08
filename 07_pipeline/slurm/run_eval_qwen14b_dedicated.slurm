#!/bin/bash
#SBATCH --job-name=ecn-eval-qwen14b
#SBATCH --output=/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY/logs/eval_qwen14b_%j.log
#SBATCH --error=/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY/logs/eval_qwen14b_%j.log
#SBATCH --partition=gpu
#SBATCH --qos=medium
#SBATCH --time=20:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1

set -euo pipefail
PROJECT_ROOT="/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY"
cd "$PROJECT_ROOT"

source /etc/profile.d/modules.sh 2>/dev/null || true
module load apptainer 2>/dev/null || true

export http_proxy="http://proxy.ec-nantes.fr:3128" 2>/dev/null || true
export https_proxy="http://proxy.ec-nantes.fr:3128" 2>/dev/null || true

SIF_PATH="/scratch/nautilus/users/mhnguyn2025@ec-nantes.fr/ecnbench/vllm_v0.6.3.sif"
VENV_PATH="/scratch/waves/users/mhnguyn2025@ec-nantes.fr/project_backup/MiroFish-Offline/backend/venv"

export VLLM_PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()' 2>/dev/null || echo 8081)
export EVALUATOR_BACKEND_PORT="$VLLM_PORT"
export EVALUATOR_MODEL_NAME="deepseek-r1-14b"
export BENCHMARK_ROLE_EVALUATOR_MODEL="deepseek-r1-14b"
export BENCHMARK_ROLE_EVALUATOR_BASE_URL="http://127.0.0.1:${VLLM_PORT}/v1"
export BENCHMARK_ROLE_EVALUATOR_API_KEY="EMPTY"
export BENCHMARK_MODE="True"
export HEADLESS_MODE="True"

mkdir -p "$PROJECT_ROOT/logs"

# Start vLLM using Apptainer
apptainer run --nv \
  -B /scratch:/scratch \
  "$SIF_PATH" \
  --model deepseek-ai/DeepSeek-R1-Distill-Qwen-14B \
  --served-model-name "deepseek-r1-14b" \
  --port "$VLLM_PORT" \
  --host 127.0.0.1 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.85 \
  --max-model-len 8192 \
  --trust-remote-code > "$PROJECT_ROOT/logs/vllm_qwen14b_${SLURM_JOB_ID}.log" 2>&1 &

VLLM_PID=$!
trap "kill -9 $VLLM_PID 2>/dev/null || true" EXIT

echo "Waiting for vLLM Dedicated Qwen14B Evaluator on port $VLLM_PORT..."
for i in $(seq 1 300); do
  if curl -s "http://127.0.0.1:${VLLM_PORT}/v1/models" >/dev/null 2>&1; then
    echo "Evaluator Server Ready!"
    break
  fi
  sleep 2
done

source "$VENV_PATH/bin/activate"
python "$PROJECT_ROOT/eval_qwen14b_dedicated.py"
echo "DEDICATED QWEN14B EVALUATION COMPLETED SUCCESSFULLY!"
