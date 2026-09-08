#!/bin/bash
#SBATCH --job-name=ecn-qwen14b-6events-fix
#SBATCH --account=gem
#SBATCH -p standard
#SBATCH --qos=medium
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --output=logs/qwen14b_6events_fix_%A.log

# ==============================================================================
# GLiCID HPC REPAIR SCRIPT FOR 6 EXCLUDED EVENTS OF QWEN2.5-14B
# Target Events: T3, T4, T5, T6, C6, T8
# Model: Qwen 2.5 14B Instruct via OpenRouter API
# Evaluator: DeepSeek R1 Distill Qwen 14B
# Setup: N=300 agents, R=60 rounds, Step 30 injection
# ==============================================================================

# 1. Network Proxy for Outbound API Calls from Compute Nodes
export http_proxy="http://proxy.ec-nantes.fr:3128" 2>/dev/null
export https_proxy="http://proxy.ec-nantes.fr:3128" 2>/dev/null
export HTTP_PROXY="http://proxy.ec-nantes.fr:3128" 2>/dev/null
export HTTPS_PROXY="http://proxy.ec-nantes.fr:3128" 2>/dev/null

# 2. Environment Paths
USER_ID=$(whoami)
PROJECT_ROOT="/scratch/waves/users/$USER_ID/ECN-HPC-DEPLOY"
WAVES_SCRATCH="/scratch/waves/users/$USER_ID/ecnbench_workspace"
export PATH="$HOME/ecnbench/bin:$PATH"

mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$WAVES_SCRATCH/simulation_logs/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete"

# 3. OpenRouter Model Configuration
export OPENROUTER_API_KEY="REDACTED_SET_OPENROUTER_API_KEY"
export OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

export OPENROUTER_BENCHMARK_MODEL="qwen/qwen-2.5-14b-instruct"
export OPENROUTER_GRAPH_MODEL="qwen/qwen-2.5-14b-instruct"
export OPENROUTER_EVALUATOR_MODEL="deepseek/deepseek-r1-distill-qwen-14b"

export LLM_BASE_URL="https://openrouter.ai/api/v1"
export EVALUATOR_LLM_BASE_URL="https://openrouter.ai/api/v1"
export GRAPH_LLM_BASE_URL="https://openrouter.ai/api/v1"

export BENCHMARK_MODE='true'
export DEV_MINIMAL_MODE='true'
export DEV_MINIMAL_AGENT_COUNT='300'
export DEV_MINIMAL_MAX_STEPS='60'
export DEV_MINIMAL_INJECTION_STEP='30'
export LLM_TIMEOUT_SECONDS='1800'
export LLM_USE_JSON_SCHEMA='True'

EVENTS_6_LIST="T3,T4,T5,T6,C6,T8"

echo "================================================================="
echo "SUBMITTING 6 EXCLUDED EVENTS FIX FOR QWEN2.5-14B"
echo "Target Model: $OPENROUTER_BENCHMARK_MODEL"
echo "Evaluator:    $OPENROUTER_EVALUATOR_MODEL"
echo "Events (6):   $EVENTS_6_LIST"
echo "Agents:       $DEV_MINIMAL_AGENT_COUNT | Rounds: $DEV_MINIMAL_MAX_STEPS"
echo "================================================================="

cd "$PROJECT_ROOT/MiroFish-Offline/backend" 2>/dev/null || cd "$HOME/ecnbench/MiroFish-Offline/backend" 2>/dev/null
source /scratch/waves/users/mhnguyn2025@ec-nantes.fr/project_backup/MiroFish-Offline/backend/venv/bin/activate

python scripts/run_ecnbench_protocol.py   --seeds-dir ../../data/seeds   --events-raw ../../data/events_raw.json   --injection-bank ../../data/injections/step30_injection_bank.json   --output-dir "$WAVES_SCRATCH/simulation_logs/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete"   --event-ids "$EVENTS_6_LIST"   --repeats 1

echo "================================================================="
echo "JOB COMPLETED SUCCESSFULLY FOR ALL 6 QWEN14B EVENTS!"
echo "================================================================="
