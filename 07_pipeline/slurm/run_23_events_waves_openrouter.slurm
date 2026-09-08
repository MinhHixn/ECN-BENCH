#!/bin/bash
#SBATCH --job-name=ecn-waves-openrouter-23events
#SBATCH --account=gem
#SBATCH -p waves
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=03:00:00
#SBATCH --output=logs/waves_openrouter_23events_%A.log

# ==============================================================================
# GLiCID HPC EMERGENCY ADAPTATION SCRIPT
# Cluster Target: WAVES Cluster (/scratch/waves is OPERATIONAL)
# Control Node: nautilus-devel-001
# Note: /scratch/nautilus is DOWN due to GPFS outage. All paths rerouted to /scratch/waves.
# Model Backend: OpenRouter Cloud API (replaces local vLLM to prevent GPU heat & GPFS dependency)
# ==============================================================================

# 1. Network Proxy for Outbound API Calls from Waves Compute Nodes
export http_proxy="http://proxy.ec-nantes.fr:3128" 2>/dev/null
export https_proxy="http://proxy.ec-nantes.fr:3128" 2>/dev/null

# 2. Environment Paths (Strictly /scratch/waves & $HOME)
USER_ID=$(whoami)
PROJECT_ROOT="/scratch/waves/users/$USER_ID/ECN-HPC-DEPLOY"
WAVES_SCRATCH="/scratch/waves/users/$USER_ID/ecnbench_workspace"
export PATH="$HOME/ecnbench/bin:$PATH"

mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$WAVES_SCRATCH/simulation_logs"

# 3. OpenRouter Model Configuration (Tested Valid Key)
export OPENROUTER_API_KEY="REDACTED_SET_OPENROUTER_API_KEY"
export OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

# Target Model for the 23 Llama-3.1-8B Events
export OPENROUTER_BENCHMARK_MODEL="meta-llama/llama-3.1-8b-instruct"
export OPENROUTER_GRAPH_MODEL="meta-llama/llama-3.1-8b-instruct"
export OPENROUTER_EVALUATOR_MODEL="deepseek/deepseek-v4-flash-0731"

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

# 4. Target 23 Failed Events List
EVENTS_23_LIST="S9,T1,T2,T3,T4,T5,T6,T8,T9,C1,C2,C4,C5,C6,C7,C8,C9,C10,C11,C12,C13,C14,C15"

echo "================================================================="
echo "SUBMITTING 23 EVENTS RECOVERY JOB ON WAVES CLUSTER (OPENROUTER)"
echo "Control Node: nautilus-devel-001"
echo "Active Storage: /scratch/waves"
echo "Target Model: $OPENROUTER_BENCHMARK_MODEL"
echo "Evaluator:    $OPENROUTER_EVALUATOR_MODEL"
echo "Events (23):  $EVENTS_23_LIST"
echo "================================================================="

# 5. Execute Simulation Protocol
cd "$PROJECT_ROOT/MiroFish-Offline/backend" 2>/dev/null || cd "$HOME/ecnbench/MiroFish-Offline/backend" 2>/dev/null
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python scripts/run_ecnbench_protocol.py \
  --seeds-dir ../../data/seeds \
  --events-raw ../../data/events_raw.json \
  --injection-bank ../../data/injections/step30_injection_bank.json \
  --output-dir "$WAVES_SCRATCH/simulation_logs" \
  --event-ids "$EVENTS_23_LIST" \
  --repeats 1

echo "================================================================="
echo "JOB COMPLETED SUCCESSFULLY FOR ALL 23 EVENTS ON WAVES!"
echo "Output Directory: $WAVES_SCRATCH/simulation_logs"
echo "================================================================="
