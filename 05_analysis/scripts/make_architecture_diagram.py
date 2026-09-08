import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

def create_architecture_diagram(output_path="fig1_architecture_code_generated.png"):
    # Set up figure and axis (16:9 aspect ratio, 300 DPI for publication quality)
    fig, ax = plt.subplots(figsize=(16, 9), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    
    # Hide axis lines and ticks
    ax.axis('off')
    ax.set_xlim(0, 160)
    ax.set_ylim(0, 90)

    # Color Palette (Academic Camera-Ready)
    COLOR_INPUT = {'fill': '#F0F7FF', 'border': '#2563EB', 'text': '#1E3A8A'}
    COLOR_PHASE1 = {'fill': '#F0FDFA', 'border': '#0D9488', 'text': '#115E59'}
    COLOR_PHASE2 = {'fill': '#F5F3FF', 'border': '#7C3AED', 'text': '#5B21B6'}
    COLOR_PHASE3 = {'fill': '#ECFDF5', 'border': '#059669', 'text': '#065F46'}
    COLOR_INFRA = {'fill': '#F8FAFC', 'border': '#475569', 'text': '#1E293B'}
    COLOR_ALERT = {'fill': '#FFF1F2', 'border': '#E11D48', 'text': '#9F1239'}
    COLOR_COND_A = {'fill': '#EFF6FF', 'border': '#3B82F6', 'text': '#1D4ED8'}
    COLOR_COND_B = {'fill': '#ECFDF5', 'border': '#10B981', 'text': '#047857'}
    COLOR_COND_C = {'fill': '#FEF3C7', 'border': '#F59E0B', 'text': '#B45309'}

    # Helper function to draw fancy rounded boxes with text
    def draw_box(x, y, width, height, title, details=None, style=COLOR_INPUT, badge=None, alert=False):
        box_style = COLOR_ALERT if alert else style
        box = FancyBboxPatch((x, y), width, height,
                             boxstyle="round,pad=0.5,rounding_size=1.5",
                             facecolor=box_style['fill'],
                             edgecolor=box_style['border'],
                             linewidth=1.8,
                             zorder=2)
        ax.add_patch(box)
        
        # Title text
        ax.text(x + width/2, y + height - 1.8, title,
                ha='center', va='top', fontsize=10.5, fontweight='bold',
                color=box_style['text'], zorder=3)
        
        # Badge on top right if present
        if badge:
            badge_box = FancyBboxPatch((x + width - len(badge)*1.2 - 2, y + height - 2.2), len(badge)*1.2 + 1.5, 1.8,
                                       boxstyle="round,pad=0.2,rounding_size=0.8",
                                       facecolor=box_style['border'],
                                       edgecolor='none', zorder=4)
            ax.add_patch(badge_box)
            ax.text(x + width - (len(badge)*1.2 + 1.5)/2 - 1, y + height - 1.3, badge,
                    ha='center', va='center', fontsize=7.5, fontweight='bold', color='#FFFFFF', zorder=5)

        # Body details
        if details:
            for i, line in enumerate(details):
                ax.text(x + 1.5, y + height - 4.2 - (i * 1.8), line,
                        ha='left', va='top', fontsize=8.5, color='#334155', zorder=3)

    # Helper function to draw clean directional arrows
    def draw_arrow(x1, y1, x2, y2, color='#64748B', style='->', lw=1.5, connectionstyle="arc3,rad=0"):
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                                arrowstyle=style,
                                mutation_scale=14,
                                color=color,
                                linewidth=lw,
                                connectionstyle=connectionstyle,
                                zorder=1)
        ax.add_patch(arrow)

    # Main Title Header
    ax.text(80, 86, "Figure 1: ECN-BENCH Multi-Agent Social Simulation & Probability Elicitation Pipeline",
            ha='center', va='center', fontsize=14, fontweight='bold', color='#0F172A')
    ax.text(80, 83.5, "Architecture Overview & Execution Phases (Code-Generated Academic Vector Diagram)",
            ha='center', va='center', fontsize=9.5, color='#475569')

    # ==================== COLUMN 1: INPUTS & INTERVENTIONS (x: 5 - 38) ====================
    ax.text(21.5, 79, "1. INPUTS & EXPERIMENTAL CONDITIONS", ha='center', fontsize=9.5, fontweight='bold', color='#1E3A8A')
    
    draw_box(5, 64, 33, 12, "Polymarket Event Seed", 
             ["• E = 30 Resolved Markets", "• Options K in [2, 9]", "• Sanitized context.md"],
             style=COLOR_INPUT, badge="Input Corpus")

    draw_box(5, 48, 33, 12, "Condition B: Relevant Injection", 
             ["• Content-Specific Breaking News", "• Injected at Round R = 30", "• Measures Signal Sensitivity"],
             style=COLOR_COND_B, badge="Cond B (With-Sim)")

    draw_box(5, 32, 33, 12, "Condition C: Null Injection", 
             ["• Structurally Matched Null Noise", "• Injected at Round R = 30", "• Measures Noise Resistance"],
             style=COLOR_COND_C, badge="Cond C (Null)")

    draw_box(5, 16, 33, 12, "Condition A: Direct Elicitation", 
             ["• Single-pass direct query to LLM", "• No social simulation stage", "• Shared reference record (Audit)"],
             style=COLOR_COND_A, badge="Cond A (No-Sim)")

    # ==================== COLUMN 2: 3-PHASE EXECUTION CORE (x: 46 - 110) ====================
    ax.text(78, 79, "2. 3-PHASE EXECUTION PIPELINE CORE", ha='center', fontsize=9.5, fontweight='bold', color='#115E59')

    # Phase 1
    draw_box(46, 64, 64, 12, "Phase 1: Persona Engine & Graph Memory Initialization", 
             ["• LLM Persona Generator extracts N = 300 diverse agent DNA profiles (Worldview, Motivation, Style, Biases)",
              "• Agent memories initialized into Graphiti Temporal Context Engine backed by Neo4j graph database"],
             style=COLOR_PHASE1, badge="Phase 1 (N=300)")

    # Phase 2 Dual Platforms
    draw_box(46, 42, 30, 16, "Twitter Simulation", 
             ["• OASIS Open Topology", "• Actions: Post, Comment,", "  Like, Follow", "• R = 60 rounds"],
             style=COLOR_PHASE2, badge="Twitter Sim")

    draw_box(80, 42, 30, 16, "Reddit Simulation", 
             ["• Subreddit Structure", "• Threaded Discussions", "  (r/politics, r/finance)", "• R = 60 rounds"],
             style=COLOR_PHASE2, badge="Reddit Sim")

    # Round 30 Checkpoint annotation
    box_r30 = FancyBboxPatch((65, 36.5), 32, 3.5, boxstyle="round,pad=0.2,rounding_size=0.5",
                             facecolor='#FFFBEB', edgecolor='#F59E0B', lw=1, zorder=3)
    ax.add_patch(box_r30)
    ax.text(81, 38.2, "Round 30 Checkpoint: Inject Cond B / C", ha='center', va='center', fontsize=8, fontweight='bold', color='#B45309', zorder=4)

    # Phase 3
    draw_box(46, 16, 64, 16, "Phase 3: Telemetry & Belief State Extraction", 
             ["• Telemetry probes interview agents at Rounds 12, 24, 36, 48, 60",
              "• ReportAgent aggregates agent beliefs via ensemble voting into probability vector f = [f_1, ..., f_K]",
              "• Graphiti temporal metadata tracks entity transitions (valid_at / invalid_at) across rounds"],
             style=COLOR_PHASE3, badge="Phase 3 (Round 60)")

    # ==================== COLUMN 3: EVALUATOR & METRICS (x: 118 - 155) ====================
    ax.text(136.5, 79, "3. EVALUATOR & BENCHMARK METRICS", ha='center', fontsize=9.5, fontweight='bold', color='#5B21B6')

    draw_box(118, 54, 37, 22, "7-Dimension LLM Evaluator", 
             ["• Fixed Evaluator Model (DeepSeek-R1-14B)",
              "• Evaluates probabilities & 7 rubric dimensions:",
              "  1. Prediction Accuracy (BS)",
              "  2. Polarization (Esteban-Ray ER)",
              "  3. Herd Effect (Excess Conformity)",
              "  4. Deliberation Quality (DQI)",
              "  5. Susceptibility Margin (Cond B vs C)",
              "  6. Opinion Convergence (JSD)",
              "  7. Information Diversity (Entropy H)"],
             style=COLOR_PHASE2, badge="DeepSeek-R1-14B", alert=True)

    draw_box(118, 16, 37, 34, "Scoring & Benchmark Outputs", 
             ["• Brier Score: BS = sum(f_k - o_k)^2",
              "• Brier Skill Score: BSS = 1 - BS_model / BS_random",
              "• EPI Index: Weighted composite S_1 ... S_7",
              "----------------------------------------",
              "Key Validated Finding (Section IX-F):",
              "• 17 Clean Post-Release Events:",
              "  Modal forecast hits outcome in 88.2%",
              "  of pairs (60/68) vs 34.6% chance",
              "  baseline (p = 2.9 * 10^-22).",
              "• B-vs-C Sensitivity: +0.178 Brier gain"],
             style=COLOR_PHASE3, badge="Primary Metrics")

    # ==================== BOTTOM: HPC INFRASTRUCTURE STACK (x: 5 - 155) ====================
    box_infra = FancyBboxPatch((5, 2), 150, 11, boxstyle="round,pad=0.5,rounding_size=1.2",
                               facecolor=COLOR_INFRA['fill'], edgecolor=COLOR_INFRA['border'], lw=1.5, zorder=2)
    ax.add_patch(box_infra)
    ax.text(7.5, 11, "AIR-GAPPED HPC SERVING INFRASTRUCTURE (Architecture v5.0 – v5.10)",
            ha='left', va='top', fontsize=9, fontweight='bold', color=COLOR_INFRA['text'])

    # Infra Sub-boxes
    draw_box(7, 3.5, 34, 6, "vLLM Inference Server", ["• Port 8000 (GPUs 0,1)", "• AWQ INT4 / FP16 continuous batching"], style=COLOR_INFRA)
    draw_box(44, 3.5, 34, 6, "Ollama Server", ["• Port 11434 (GPUs 2,3)", "• GGUF Q4_K_M & Embedding server"], style=COLOR_INFRA)
    draw_box(81, 3.5, 34, 6, "Neo4j Graph Database", ["• Port 7474 / 7687", "• NVMe Waves scratch drives for Graphiti"], style=COLOR_INFRA)
    draw_box(118, 3.5, 34, 6, "Apptainer Containerization", ["• Singularity (vllm-openai:v0.6.3)", "• Surgical Python 3.12 bind-mount"], style=COLOR_INFRA)

    # ==================== CONNECTIONS / ARROWS ====================
    # From Seed to Phase 1
    draw_arrow(38, 70, 46, 70, color='#2563EB', lw=1.8)
    
    # From Phase 1 to Phase 2
    draw_arrow(78, 64, 61, 58, color='#0D9488', lw=1.8)
    draw_arrow(78, 64, 95, 58, color='#0D9488', lw=1.8)

    # From Condition B/C to Round 30 Injection
    draw_arrow(38, 54, 65, 38.2, color='#10B981', lw=1.5, connectionstyle="arc3,rad=-0.1")
    draw_arrow(38, 38, 65, 38.2, color='#F59E0B', lw=1.5, connectionstyle="arc3,rad=0.1")

    # From Phase 2 to Phase 3
    draw_arrow(61, 42, 78, 32, color='#7C3AED', lw=1.8)
    draw_arrow(95, 42, 78, 32, color='#7C3AED', lw=1.8)

    # From Condition A to Evaluator
    draw_arrow(38, 22, 118, 65, color='#3B82F6', lw=1.5, connectionstyle="arc3,rad=-0.25")

    # From Phase 3 to Evaluator
    draw_arrow(110, 24, 118, 65, color='#059669', lw=1.8, connectionstyle="arc3,rad=0.15")

    # From Evaluator to Metrics
    draw_arrow(136.5, 54, 136.5, 50, color='#5B21B6', lw=1.8)

    # Save figure
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Successfully generated code-based architecture diagram: {output_path}")

if __name__ == "__main__":
    target_dir = r"C:\Users\TPGHien\.gemini\antigravity\brain\6fa29685-68fd-4ecc-b51e-74095eee9f1c"
    os.makedirs(target_dir, exist_ok=True)
    artifact_img_path = os.path.join(target_dir, "fig1_architecture_code_generated.png")
    create_architecture_diagram(artifact_img_path)
    create_architecture_diagram("fig1_architecture_code_generated.png")
