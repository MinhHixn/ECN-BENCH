"""
ECN-BENCH pipeline architecture diagram (Figure 1 in the compiled paper).

Redrawn to show the mechanism the paper's argument depends on:
  - Condition A is a single-pass bypass around the entire simulation (top lane).
  - Conditions B/C are the SAME mechanism (content injected mid-run at round 30)
    with different content -- drawn as one injection point, not two pipelines.
  - Phase 2 is one continuous R=60 run with a shared memory store, not two
    disconnected platforms.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

FIG_W, FIG_H = 19.0, 8.4
CANVAS_X, CANVAS_Y = 204, 92

INK = "#1E293B"
MUTED = "#64748B"
LINE = "#334155"

SLATE = dict(fill="#F8FAFC", border="#475569", text="#1E293B")
TEAL = dict(fill="#F0FDFA", border="#0F766E", text="#115E59")
INDIGO = dict(fill="#EEF2FF", border="#4F46E5", text="#3730A3")
AMBER = dict(fill="#FFFBEB", border="#D97706", text="#92400E")
INFRA = dict(fill="#F1F5F9", border="#94A3B8", text="#334155")

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=300)
fig.patch.set_facecolor("#FFFFFF")
ax.set_facecolor("#FFFFFF")
ax.axis("off")
ax.set_xlim(0, CANVAS_X)
ax.set_ylim(0, CANVAS_Y)
ax.set_aspect("equal")


def box(x, y, w, h, title, lines=None, style=SLATE, title_size=10.3, body_size=8.0, dashed=False, gap=2.8):
    b = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.35,rounding_size=1.1",
        facecolor=style["fill"], edgecolor=style["border"],
        linewidth=1.6, zorder=2,
        linestyle=(0, (4, 2)) if dashed else "solid",
    )
    ax.add_patch(b)
    ty = y + h - 2.1
    ax.text(x + w / 2, ty, title, ha="center", va="top",
             fontsize=title_size, fontweight="bold", color=style["text"], zorder=3)
    if lines:
        for i, ln in enumerate(lines):
            ax.text(x + w / 2, ty - gap - i * gap, ln, ha="center", va="top",
                     fontsize=body_size, color=MUTED, zorder=3)
    return (x, y, w, h)


def group_label(x, y, text, color=INK):
    ax.text(x, y, text, ha="left", va="bottom", fontsize=9.5, fontweight="bold", color=color, zorder=3)


def arrow(p1, p2, color=LINE, lw=1.5, dashed=False, rad=0.0, mutation=13, double=False):
    style = "<|-|>" if double else "-|>"
    a = FancyArrowPatch(
        p1, p2, arrowstyle=style, mutation_scale=mutation, color=color, linewidth=lw,
        connectionstyle=f"arc3,rad={rad}", zorder=1,
        linestyle=(0, (4, 2)) if dashed else "solid",
        shrinkA=0, shrinkB=0,
    )
    ax.add_patch(a)


def arrow_label(x, y, text, color=MUTED, size=7.6, style="italic", rot=0):
    ax.text(x, y, text, ha="center", va="center", fontsize=size, color=color,
             style=style, zorder=4, rotation=rot,
             bbox=dict(facecolor="white", edgecolor="none", pad=0.8))


# ---------------------------------------------------------------- title ----
ax.text(CANVAS_X / 2, 90.3, "ECN-BENCH Simulation → Evaluation Pipeline",
         ha="center", va="top", fontsize=15.5, fontweight="bold", color=INK)
ax.text(CANVAS_X / 2, 86.9,
         "N = 300 agents · R = 60 rounds per event · evaluated with a fixed DeepSeek-R1-14B judge",
         ha="center", va="top", fontsize=9.3, color=MUTED)

# ------------------------------------------------------- condition-A lane ---
bypass_y = 82.3
ax.plot([16, 16], [77.5, bypass_y], color=MUTED, linewidth=1.3, linestyle=(0, (4, 2)), zorder=1)
arrow((16, bypass_y), (187, bypass_y), color=MUTED, lw=1.3, dashed=True, mutation=11)
arrow((187, bypass_y), (187, 73), color=MUTED, lw=1.3, dashed=True, mutation=11)
ax.text(101, bypass_y + 1.4,
         "Condition A — single-pass direct query, no simulation, one shared record per event → straight to the evaluator",
         ha="center", va="bottom", fontsize=8.3, style="italic", color=MUTED)

# ============================================================ headers =====
group_label(4, 75.5, "INPUT")
group_label(33, 75.5, "PHASE 1")
group_label(63, 75.5, "PHASE 2 — SOCIAL SIMULATION, R = 60 ROUNDS")
group_label(139, 75.5, "PHASE 3")
group_label(165, 75.5, "EVALUATION")

# ============================================================ column A ====
box(4, 55, 24, 18, "Event Seed", ["30 resolved Polymarket markets", "context.md — zero-URL, cutoff-frozen"],
    style=SLATE, gap=3.0)

box(4, 30, 24, 18, "Condition A: Direct Elicitation",
    ["single-pass query,", "no simulation stage"], style=SLATE, dashed=True, title_size=9.6, gap=3.0)

# ============================================================ column B ====
box(33, 55, 24, 18, "Persona Generation", ["LLM → N = 300 agent DNA profiles", "worldview · motivation · bias"],
    style=TEAL, gap=3.0)

# ============================================================ column C ====
frame_x, frame_w = 63, 76
frame_y, frame_h = 34, 39
ax.add_patch(FancyBboxPatch((frame_x, frame_y), frame_w, frame_h,
             boxstyle="round,pad=0.5,rounding_size=1.3", facecolor="none",
             edgecolor="#CBD5E1", linewidth=1.2, linestyle=(0, (2, 2)), zorder=1))

box(66, 58, 30, 13, "Twitter Sim", ["OASIS open topology"], style=TEAL, title_size=9.8, body_size=7.8)
box(66, 39, 30, 13, "Reddit Sim", ["r/politics, r/finance threads"], style=TEAL, title_size=9.8, body_size=7.8)
box(100, 46, 26, 17, "Graphiti Memory\n(Neo4j)", ["temporal belief graph"], style=SLATE, title_size=9.4, body_size=7.6, gap=5.5)

arrow((96, 64.5), (100, 60), rad=-0.2, lw=1.3, double=True)
arrow((96, 45.5), (100, 54), rad=0.2, lw=1.3, double=True)
arrow_label(98, 53, "memory\nread/write", size=7.0)

ck_x = 130
ax.plot([ck_x, ck_x], [frame_y, frame_y + frame_h], color=AMBER["border"], linewidth=1.5,
         linestyle=(0, (3, 2)), zorder=2)
ax.text(ck_x, frame_y + frame_h + 1.3, "R = 30\ninject B / C", ha="center", va="bottom",
         fontsize=7.8, fontweight="bold", color=AMBER["text"])

box(115, 16, 30, 15, "Round-30 Interventions",
    ["B  real market intelligence", "C  structurally matched null noise"],
    style=AMBER, title_size=9.4, body_size=7.6, gap=3.0)
arrow((ck_x, 31), (ck_x, frame_y), color=AMBER["border"], lw=1.6)
arrow_label(ck_x + 12, 33.5, "injected\ncontent", color=AMBER["text"], size=7.2)

# ============================================================ column D ====
box(147, 55, 22, 18, "Belief Aggregation", ["ensemble vote → f = [f₁...fₖ]", "read out at R = 60"],
    style=TEAL, title_size=9.8, gap=3.0)

# ============================================================ column E ====
box(176, 55, 22, 18, "7-Dim Evaluator", ["DeepSeek-R1-14B, fixed", "Brier + 6 rubric dims"], style=INDIGO,
    title_size=9.8, gap=3.0)
box(176, 30, 22, 18, "Scoring", ["BS · RPS · BSS", "EPI (if κ ≥ 0.8)"], style=INDIGO, title_size=9.8, gap=3.0)

# ================================================================ arrows ====
arrow((28, 64), (33, 64))
arrow_label(30.5, 67, "context", size=7.2)

arrow((57, 64), (66, 65.5), rad=-0.08)
arrow_label(61.5, 69, "300 DNA profiles", size=7.2)

arrow((139, 65.5), (147, 64), rad=-0.1)
arrow((139, 47), (147, 61), rad=0.18)
arrow_label(141, 51, "final beliefs", size=7.2, rot=32)

arrow((169, 64), (176, 64))
arrow_label(172.5, 67, "transcripts", size=7.2)

arrow((187, 55), (187, 48))
arrow_label(190.6, 51.5, "labels", size=7.2, rot=90)

# condition-A bypass endpoints, connecting the top lane down to its boxes
arrow((16, 55), (16, 48), lw=1.3, dashed=True, color=MUTED, mutation=11)

# ============================================================== infra band ==
ax.add_patch(FancyBboxPatch((4, 2), CANVAS_X - 4 - 4, 10.5, boxstyle="round,pad=0.4,rounding_size=1.0",
             facecolor=INFRA["fill"], edgecolor=INFRA["border"], linewidth=1.4, zorder=2))
ax.text(7, 10.8, "HPC SERVING LAYER — air-gapped NVIDIA A100 nodes, Apptainer/Singularity",
         ha="left", va="top", fontsize=8.8, fontweight="bold", color=INFRA["text"])
ax.text(7, 7.2, "vLLM · AWQ-INT4 continuous batching      |      Ollama · GGUF Q4_K_M      |      Neo4j 7474/7687 · graph memory store",
         ha="left", va="top", fontsize=8.0, color=MUTED)

plt.tight_layout()
plt.savefig("fig8_architecture.png", dpi=300, bbox_inches="tight", facecolor="white")
plt.close()
print("wrote fig8_architecture.png")
