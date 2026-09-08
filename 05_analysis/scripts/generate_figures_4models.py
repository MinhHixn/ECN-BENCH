"""
ECN-BENCH Paper Figures - 4-Model Edition
3 complete campaigns: Llama-3.1-8B-AWQ, Mistral-7B-AWQ, Qwen2.5-7B-GGUF
Partial Qwen2.5-14B-AWQ: action density + runtime only (no full 30-event campaign locally)
Run from project root: python scratch/generate_figures_4models.py
"""
import os, sys, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap

OUT_DIR = "."
MODELS_3 = ["Llama-3.1-8B", "Mistral-7B", "Qwen2.5-7B"]
MCOL = {"Llama-3.1-8B":"#2ECC71","Mistral-7B":"#E74C3C","Qwen2.5-7B":"#3498DB","Qwen2.5-14B*":"#F39C12"}
MMARK = {"Llama-3.1-8B":"o","Mistral-7B":"s","Qwen2.5-7B":"^","Qwen2.5-14B*":"D"}
COL_A="#5B8DB8"; COL_B="#E07B39"; COL_C="#9B59B6"

plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"axes.titlesize":13,
    "axes.labelsize":12,"axes.spines.top":False,"axes.spines.right":False,
    "figure.dpi":150,"savefig.dpi":200,"savefig.bbox":"tight"})

AGG = {
    "Llama-3.1-8B":{"BS_A":0.384612,"BS_B":0.483882,"BS_C":0.561430,
        "lift_AB":-0.09927,"dir_B":0.7167,"cohens_d":-0.285917,
        "ci_lower":-0.802759,"ci_upper":0.230924,"power":0.085125,
        "jsd":0.733946,"monotonic":48,"rps_B":0.433204,
        "kappa":{"prediction_accuracy":0.412245,"polarization":0.365051,
                 "deliberation_quality":0.310277,"herd_effect":0.218100,
                 "convergence":0.257593,"susceptibility":0.227679,
                 "information_diversity":0.209536},
        "susc_delta":0.011111},
    "Mistral-7B":{"BS_A":0.384612,"BS_B":0.531213,"BS_C":0.646167,
        "lift_AB":-0.146601,"dir_B":0.5667,"cohens_d":-0.440475,
        "ci_lower":-0.957316,"ci_upper":0.076366,"power":0.088280,
        "jsd":0.637347,"monotonic":0,"rps_B":0.522771,
        "kappa":{"prediction_accuracy":0.182199,"polarization":0.167112,
                 "deliberation_quality":0.228188,"herd_effect":0.112964,
                 "convergence":0.138675,"susceptibility":0.244663,
                 "information_diversity":0.129534},
        "susc_delta":0.005556},
    "Qwen2.5-7B":{"BS_A":0.384612,"BS_B":0.481439,"BS_C":0.534522,
        "lift_AB":-0.096827,"dir_B":0.7333,"cohens_d":-0.277659,
        "ci_lower":-0.794500,"ci_upper":0.239182,"power":0.084813,
        "jsd":0.627451,"monotonic":0,"rps_B":0.439103,
        "kappa":{"prediction_accuracy":0.087618,"polarization":0.122110,
                 "deliberation_quality":0.061814,"herd_effect":0.053384,
                 "convergence":0.212097,"susceptibility":0.032710,
                 "information_diversity":0.102564},
        "susc_delta":-0.044444},
    "Qwen2.5-14B*":{"BS_A":0.5600,"BS_B":0.5978,"BS_C":0.5958,
        "lift_AB":-0.0378,"dir_B":None,"cohens_d":None,
        "ci_lower":None,"ci_upper":None,"power":None,
        "jsd":None,"monotonic":None,"rps_B":None,"kappa":{},"susc_delta":None},
}

ACTION_DATA = {
    "Llama-3.1-8B":{"total":27087,"per_db":40.31,"posts":8079,"comments":5421,"follows":5993,"likes":3010,"dislikes":7},
    "Mistral-7B":{"total":9364,"per_db":35.47,"posts":4476,"comments":2258,"follows":717,"likes":1946,"dislikes":67},
    "Qwen2.5-14B*":{"total":2407,"per_db":13.38,"posts":1215,"comments":585,"follows":11,"likes":461,"dislikes":0},
    "Qwen2.5-7B":{"total":723,"per_db":2.74,"posts":592,"comments":108,"follows":1,"likes":16,"dislikes":0},
}

RUNTIME = {
    "Llama-3.1-8B":{"phase_A":3.8,"sim_B":35.1,"sim_C":31.4,"total":77.6},
    "Mistral-7B":{"phase_A":2.7,"sim_B":33.7,"sim_C":30.1,"total":75.4},
    "Qwen2.5-7B":{"phase_A":2.7,"sim_B":47.9,"sim_C":18.4,"total":77.1},
    "Qwen2.5-14B*":{"phase_A":2.7,"sim_B":69.5,"sim_C":31.5,"total":114.0},
}

EVENTS = ["C1","C10","C11","C12","C13","C14","C15","C2","C3","C4","C5","C6",
          "C7","C8","C9","S2","S3","S4","S5","S6","S7","S9",
          "T1","T2","T3","T4","T5","T6","T8","T9"]
EVENT_TYPE = {e:("C" if e.startswith("C") else "S" if e.startswith("S") else "T") for e in EVENTS}

BRIER_A_RAW = {"C1":0.5600,"C10":0.0036,"C11":1.3150,"C12":0.0005,"C13":0.2273,"C14":0.0900,
    "C15":0.0050,"C2":0.0050,"C3":0.8100,"C4":0.0166,"C5":0.4498,"C6":1.0450,
    "C7":0.3200,"C8":0.4850,"C9":0.2150,"S2":0.0450,"S3":0.7200,"S4":0.3200,
    "S5":0.5000,"S6":0.1368,"S7":0.2450,"S9":0.7200,"T1":0.0450,"T2":1.2800,
    "T3":0.5450,"T4":0.0538,"T5":0.1800,"T6":0.7150,"T8":0.4850,"T9":0.0000}
BRIER_B_RAW = {
    "C1":[0.2600,0.6600,0.4650],"C10":[0.4150,0.4800,0.6400],"C11":[0.4850,0.4850,0.5500],
    "C12":[0.0500,0.5000,0.1150],"C13":[0.0336,0.0450,0.6100],"C14":[0.5000,0.5000,0.2250],
    "C15":[0.6050,0.5000,0.6750],"C2":[0.1150,0.2000,0.1150],"C3":[0.7500,0.7500,0.5850],
    "C4":[0.1350,0.1368,0.1250],"C5":[0.6600,0.8000,0.1400],"C6":[1.0650,0.6650,1.0450],
    "C7":[0.4450,0.8000,0.5300],"C8":[0.1150,0.7500,1.2000],"C9":[0.6712,0.5950,0.6032],
    "S2":[0.5000,0.5202,0.1800],"S3":[0.5000,0.3200,0.8450],"S4":[0.5000,0.7200,0.3200],
    "S5":[0.5000,0.3200,0.3200],"S6":[0.7500,0.7500,0.4150],"S7":[0.1800,0.1800,0.1250],
    "S9":[0.1800,0.0800,0.3200],"T1":[0.9800,0.5000,0.9800],"T2":[0.0200,0.0200,0.0050],
    "T3":[0.6667,0.7800,0.1950],"T4":[0.4600,0.5300,0.6200],"T5":[0.9800,0.5000,0.6050],
    "T6":[1.0150,0.7500,1.0150],"T8":[0.8000,0.5400,0.5550],"T9":[0.1800,0.1800,0.3200],
}
LIFT = {e:[BRIER_A_RAW[e]-BRIER_B_RAW[e][i] for i in range(3)] for e in EVENTS}
MEAN_LIFT = {e:np.mean(LIFT[e]) for e in EVENTS}
BSA_LIST = [BRIER_A_RAW[e] for e in EVENTS]
CONTAMINATED = {e for e in EVENTS if BRIER_A_RAW[e] < 0.15}
BORDERLINE = {e for e in EVENTS if 0.15 <= BRIER_A_RAW[e] < 0.35}
CLEAN = {e for e in EVENTS if BRIER_A_RAW[e] >= 0.35}

def save(fig, name):
    fig.savefig(os.path.join(OUT_DIR, name), bbox_inches="tight")
    plt.close(fig)
    sz = os.path.getsize(os.path.join(OUT_DIR, name)) // 1024
    print(f"  OK  {name}  ({sz} KB)")

print("Generating ECN-BENCH figures (4-model edition)...")

# ── FIG 2: Cross-Model Brier (4 models: 3 complete + 14B partial) ──────────
models_p = ["Llama-3.1-8B","Mistral-7B","Qwen2.5-7B","Qwen2.5-14B*"]
xlabels = ["Llama-3.1-8B\n(vLLM+AWQ)\n30 events","Mistral-7B\n(vLLM+AWQ)\n30 events",
           "Qwen2.5-7B\n(Ollama+GGUF)\n30 events","Qwen2.5-14B*\n(vLLM+AWQ)\n[C1 only]"]
fig, ax = plt.subplots(figsize=(13, 6))
x = np.arange(4); w = 0.22
ba = [AGG[m]["BS_A"] for m in models_p]
bb = [AGG[m]["BS_B"] for m in models_p]
bc = [AGG[m]["BS_C"] for m in models_p]
barsA = ax.bar(x-w, ba, w, color=COL_A, alpha=0.85, label="Cond A: No-Sim", zorder=3)
barsB = ax.bar(x,   bb, w, color=COL_B, alpha=0.85, label="Cond B: With-Sim", zorder=3)
barsC = ax.bar(x+w, bc, w, color=COL_C, alpha=0.55, label="Cond C: Null Control", zorder=3)
for i in range(3):
    ci_lo = abs(bb[i] + AGG[MODELS_3[i]]["ci_lower"] - bb[i])
    ci_hi = abs(bb[i] + AGG[MODELS_3[i]]["ci_upper"] - bb[i])
    ax.errorbar(x[i], bb[i], yerr=[[ci_lo],[ci_hi]], fmt="none", color="#222", capsize=5, lw=1.5, zorder=5)
for i in range(3):
    gap = bc[i] - bb[i]
    c = "#27AE60" if gap > 0 else "#E74C3C"
    ax.text(x[i]+0.04, (bb[i]+bc[i])/2, f"D={gap:+.3f}", fontsize=7.5, color=c, va="center")
for bar in [barsA[3], barsB[3], barsC[3]]:
    bar.set_hatch("///"); bar.set_alpha(0.6)
ax.set_xticks(x); ax.set_xticklabels(xlabels, fontsize=9)
ax.set_ylabel("Mean Multi-Category Brier Score (lower = better)")
ax.set_title("Cross-Model Mean Brier Score (N=300, R=60)\n/// = partial data (C1 only); D = delta B-C (green=susc.confirmed)", fontweight="bold")
ax.set_ylim(0, 0.88)
ax.axhline(0.384612, color=COL_A, ls="--", alpha=0.35, lw=1.2)
ax.legend(loc="upper right", fontsize=9)
save(fig, "fig2_cross_model_brier.png")

# ── FIG 1: Lift Heatmap (3 complete models) ───────────────────────────────
sorted_evs = sorted(EVENTS, key=lambda e: -MEAN_LIFT[e])
lift_mat = np.array([[LIFT[e][i] for e in sorted_evs] for i in range(3)])
fig, ax = plt.subplots(figsize=(19, 5))
cmap = LinearSegmentedColormap.from_list("lift",["#C0392B","#F5CBA7","white","#A9DFBF","#1E8449"],N=256)
im = ax.imshow(lift_mat, aspect="auto", cmap=cmap, vmin=-1.0, vmax=1.3)
ax.set_yticks(range(3)); ax.set_yticklabels(["Llama-3.1-8B","Mistral-7B","Qwen2.5-7B"],fontsize=11)
ax.set_xticks(range(len(sorted_evs))); ax.set_xticklabels(sorted_evs,fontsize=8,rotation=45,ha="right")
tax_col = {"C":"#7D3C98","S":"#1A5276","T":"#922B21"}
for tick,ev in zip(ax.get_xticklabels(), sorted_evs):
    tick.set_color(tax_col[EVENT_TYPE[ev]])
for j,ev in enumerate(sorted_evs):
    if ev in CONTAMINATED: ax.axvline(j, color="red", alpha=0.14, lw=8, zorder=0)
    elif ev in BORDERLINE: ax.axvline(j, color="orange", alpha=0.10, lw=8, zorder=0)
for i in range(3):
    for j,ev in enumerate(sorted_evs):
        v = lift_mat[i,j]
        ax.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=7, color="white" if abs(v)>0.55 else "#222")
plt.colorbar(im, ax=ax, label="Lift = BS_A - BS_B", shrink=0.75)
ax.set_title("Per-Event Simulation Lift Heatmap (3 Complete Models; N=300, R=60 | July 2026)\n"
             "Red=contaminated; Orange=borderline; Label colour=taxonomy | Qwen-14B*: HPC download pending", fontweight="bold")
patches_t = [mpatches.Patch(color=tax_col[k],label=l) for k,l in [("C","Social/Electoral"),("S","Senate/Binary"),("T","Tech/Economic")]]
ax.legend(handles=patches_t, loc="lower right", fontsize=8)
save(fig, "fig1_lift_heatmap.png")

# ── FIG 5: JSD Convergence + Susceptibility (3 models) ───────────────────
fig, axes = plt.subplots(1, 3, figsize=(17, 6))
jsd_v = [AGG[m]["jsd"] for m in MODELS_3]
mono_v = [AGG[m]["monotonic"] for m in MODELS_3]
susc_v = [AGG[m]["susc_delta"] for m in MODELS_3]

ax_j = axes[0]
ax_j.bar(range(3), jsd_v, 0.55, color=[MCOL[m] for m in MODELS_3], alpha=0.85)
ax_j.set_xticks(range(3)); ax_j.set_xticklabels(["Llama-3.1-8B","Mistral-7B","Qwen2.5-7B"],fontsize=9)
ax_j.set_ylabel("Mean Round JSD"); ax_j.set_title("Panel A: Mean JSD/Round\n(Cond B, all 30 events)", fontweight="bold")
for i,v in enumerate(jsd_v): ax_j.text(i, v+0.01, f"{v:.3f}", ha="center", fontsize=10, fontweight="bold")
ax_j.text(0.98, 0.02, "Qwen-14B*: no local JSD data", transform=ax_j.transAxes, fontsize=7, ha="right", color="#888")

ax_m = axes[1]
mcols = ["#27AE60" if v>0 else "#E74C3C" for v in mono_v]
ax_m.bar(range(3), mono_v, 0.55, color=mcols, alpha=0.9)
ax_m.set_xticks(range(3)); ax_m.set_xticklabels(["Llama-3.1-8B","Mistral-7B","Qwen2.5-7B"],fontsize=9)
ax_m.set_ylabel("Monotonic Convergence Episodes")
ax_m.set_title("Panel B: Monotonic JSD Convergence\n(DeGroot-style; 0=none; Qwen-14B* excluded)", fontweight="bold")
for i,v in enumerate(mono_v): ax_m.text(i, max(v+0.3,0.5), str(v), ha="center", fontsize=12, fontweight="bold")
ax_m.annotate("Only Llama exhibits\nDeGroot convergence", xy=(0,48), xytext=(0.8,32),
    arrowprops=dict(arrowstyle="->", color="#27AE60", lw=1.5), fontsize=9, color="#27AE60")

ax_s = axes[2]
scols = ["#27AE60" if v>0 else "#E74C3C" for v in susc_v]
ax_s.bar(range(3), susc_v, 0.55, color=scols, alpha=0.9)
ax_s.axhline(0, color="black", lw=1)
ax_s.set_xticks(range(3)); ax_s.set_xticklabels(["Llama-3.1-8B","Mistral-7B","Qwen2.5-7B"],fontsize=9)
ax_s.set_ylabel("Susceptibility Delta (B_yes - C_yes)")
ax_s.set_title("Panel C: Content Susceptibility Delta\n(Qwen-14B*: pending)", fontweight="bold")
for i,v in enumerate(susc_v): ax_s.text(i, v+(0.002 if v>0 else -0.004), f"{v:+.4f}", ha="center", fontsize=10, fontweight="bold")
ax_s.annotate("Sign reversal!\nNull > Real for Qwen-7B", xy=(2,-0.044), xytext=(1.1,-0.028),
    arrowprops=dict(arrowstyle="->", color="#E74C3C", lw=1.5), fontsize=9, color="#E74C3C")
plt.tight_layout()
fig.suptitle("Convergence Dynamics & Susceptibility (3 Complete Models | Qwen2.5-14B*: local download pending)",
             fontweight="bold", fontsize=12, y=1.02)
save(fig, "fig5_jsd_convergence.png")

# ── FIG: Action Density 4 Models ──────────────────────────────────────────
models_4 = ["Llama-3.1-8B","Mistral-7B","Qwen2.5-14B*","Qwen2.5-7B"]
fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(13, 10), gridspec_kw={"height_ratios":[1.5,1]})
act_t = ["posts","comments","follows","likes","dislikes"]
act_c = ["#2ECC71","#3498DB","#F39C12","#9B59B6","#E74C3C"]
x4 = np.arange(4); bottoms = [0,0,0,0]
for atype, ac in zip(act_t, act_c):
    vals = [ACTION_DATA[m][atype] for m in models_4]
    ax_top.bar(x4, vals, 0.55, bottom=bottoms, color=ac, alpha=0.85, label=atype.capitalize())
    for i in range(4): bottoms[i] += vals[i]
ax_top.set_xticks(x4)
ax_top.set_xticklabels(["Llama-3.1-8B\n(AWQ+vLLM)\n30 events","Mistral-7B\n(AWQ+vLLM)\n30 events",
                         "Qwen2.5-14B*\n(AWQ+vLLM)\n180 DBs, HPC","Qwen2.5-7B\n(GGUF+Ollama)\n30 events"],fontsize=10)
ax_top.set_ylabel("Total Social Actions"); ax_top.legend(loc="upper right",fontsize=9)
ax_top.set_title("Social Action Density - All 4 Model Families (Authoritative SQLite .db Audit)\n"
                 "27,087 (Llama) > 9,364 (Mistral) > 2,407 (Qwen-14B) > 723 (Qwen-7B)", fontweight="bold")
pdb = [ACTION_DATA[m]["per_db"] for m in models_4]
ax_bot.bar(x4, pdb, 0.55, color=[MCOL[m] for m in models_4], alpha=0.85)
ax_bot.set_xticks(x4); ax_bot.set_xticklabels(["Llama-3.1-8B","Mistral-7B","Qwen2.5-14B*","Qwen2.5-7B"],fontsize=10)
ax_bot.set_ylabel("Actions per DB File")
ax_bot.set_title("Normalised Action Density (Actions per Database File)", fontweight="bold")
for i,(x,v) in enumerate(zip(x4,pdb)): ax_bot.text(x, v+0.2, f"{v:.2f}", ha="center", fontsize=10, fontweight="bold")
ax_bot.text(0.98, 0.9, "Volume != Calibration:\nLlama-8B & Qwen-7B similar Brier\n(0.484 vs 0.481) despite 37x gap",
    transform=ax_bot.transAxes, fontsize=9, ha="right", va="top",
    bbox=dict(boxstyle="round,pad=0.3", facecolor="#f9f9f9", alpha=0.8))
plt.tight_layout()
save(fig, "fig_action_density_4models.png")

# ── FIG: Runtime 4 Models ─────────────────────────────────────────────────
rt_m = ["Llama-3.1-8B","Qwen2.5-7B","Qwen2.5-14B*","Mistral-7B"]
x_rt = np.arange(4); w_rt = 0.25
fig, ax = plt.subplots(figsize=(12, 6))
ax.bar(x_rt-w_rt, [RUNTIME[m]["phase_A"] for m in rt_m], w_rt, color="#9B59B6", alpha=0.85, label="Phase A")
ax.bar(x_rt,      [RUNTIME[m]["sim_B"] for m in rt_m],   w_rt, color=COL_B,    alpha=0.85, label="Sim B")
ax.bar(x_rt+w_rt, [RUNTIME[m]["sim_C"] for m in rt_m],   w_rt, color=COL_C,    alpha=0.55, label="Sim C")
totals = [RUNTIME[m]["total"] for m in rt_m]
ax.plot(x_rt, totals, "ro-", lw=2.5, markersize=8, label="Total wall-clock (min)", zorder=5)
for i,(x,t) in enumerate(zip(x_rt,totals)): ax.text(x+0.05, t+1.5, f"{t:.1f} min", fontsize=9, color="red", fontweight="bold")
ax.set_xticks(x_rt)
ax.set_xticklabels(["Llama-3.1-8B\n(AWQ+vLLM)","Qwen2.5-7B\n(GGUF+Ollama)","Qwen2.5-14B*\n(AWQ+vLLM)","Mistral-7B\n(AWQ+vLLM)"],fontsize=10)
ax.set_ylabel("Wall-Clock Time (minutes)")
ax.set_title("Per-Event Compute Budget (N=300, R=60, Event C1, A100 GPU) - ALL 4 Models\n"
             "Qwen2.5-14B* longest (114 min total); Mistral-7B fastest (75.4 min)", fontweight="bold")
ax.legend(fontsize=10); ax.set_ylim(0, max(totals)*1.25)
save(fig, "compute_cost_analysis.png")

# ── FIG: Kappa Heatmap (3 models) ────────────────────────────────────────
dims = ["prediction_accuracy","polarization","deliberation_quality","herd_effect","convergence","susceptibility","information_diversity"]
dlabels = ["Prediction\nAccuracy","Polarization","Deliberation\nQuality","Herd Effect","Convergence","Susceptibility","Info\nDiversity"]
kmat = np.array([[AGG[m]["kappa"].get(d,0.0) for d in dims] for m in MODELS_3])
fig, ax = plt.subplots(figsize=(13, 4))
cmap_k = LinearSegmentedColormap.from_list("kappa",["#E74C3C","#F5CBA7","#ABEBC6","#1E8449"],N=256)
im_k = ax.imshow(kmat, aspect="auto", cmap=cmap_k, vmin=0, vmax=0.8)
ax.set_xticks(range(7)); ax.set_xticklabels(dlabels,fontsize=9)
ax.set_yticks(range(3)); ax.set_yticklabels(["Llama-3.1-8B","Mistral-7B","Qwen2.5-7B"],fontsize=10)
for i in range(3):
    for j in range(7):
        v = kmat[i,j]; ax.text(j, i, f"{v:.3f}", ha="center", va="center", fontsize=9, color="white" if v<0.15 else "#222")
plt.colorbar(im_k, ax=ax, label="Cohen kappa", shrink=0.8)
ax.set_title("Evaluator Inter-Rater Reliability (Cohen kappa) - All 7 dims dropped (kappa<0.8)\n"
             "EPI NOT computable | Qwen-14B*: not evaluated locally", fontweight="bold")
save(fig, "fig_kappa_heatmap.png")

# ── FIG 9: Contamination Analysis ────────────────────────────────────────
fig = plt.figure(figsize=(18,6))
gs = gridspec.GridSpec(1, 3, wspace=0.38)
ax_a = fig.add_subplot(gs[0])
ev_bsa = sorted(EVENTS, key=lambda e: BRIER_A_RAW[e])
for i,e in enumerate(ev_bsa):
    c = "#E74C3C" if e in CONTAMINATED else "#F39C12" if e in BORDERLINE else "#27AE60"
    ax_a.bar(i, BRIER_A_RAW[e], color=c, alpha=0.85)
ax_a.set_xticks(range(len(ev_bsa))); ax_a.set_xticklabels(ev_bsa,rotation=90,fontsize=6.5)
ax_a.axhline(0.15,color="red",ls="--",lw=1.5,label="Contam. (<0.15)")
ax_a.axhline(0.35,color="green",ls="--",lw=1.5,label="Clean (>=0.35)")
patches_c = [mpatches.Patch(color="#E74C3C",label=f"Contaminated n={len(CONTAMINATED)}"),
             mpatches.Patch(color="#F39C12",label=f"Borderline n={len(BORDERLINE)}"),
             mpatches.Patch(color="#27AE60",label=f"Clean n={len(CLEAN)}")]
ax_a.legend(handles=patches_c, fontsize=7, loc="upper left")
ax_a.set_ylabel("BS_A"); ax_a.set_title("Panel A: Contamination\nClassification", fontweight="bold")

ax_b = fig.add_subplot(gs[1])
for e in EVENTS:
    c = "#E74C3C" if e in CONTAMINATED else "#F39C12" if e in BORDERLINE else "#27AE60"
    ax_b.scatter(BRIER_A_RAW[e], MEAN_LIFT[e], color=c, s=65, alpha=0.8, edgecolors="white", lw=0.5)
    if abs(MEAN_LIFT[e])>0.3 or BRIER_A_RAW[e]<0.005:
        ax_b.annotate(e, (BRIER_A_RAW[e], MEAN_LIFT[e]), textcoords="offset points", xytext=(3,3), fontsize=7)
xs2 = np.array(BSA_LIST); ys2 = np.array([MEAN_LIFT[e] for e in EVENTS])
m2,b2 = np.polyfit(xs2, ys2, 1); xl = np.linspace(0, 1.4, 100)
ax_b.plot(xl, m2*xl+b2, "k-", alpha=0.5, lw=1.5)
ax_b.axhline(0, color="gray", lw=0.8, ls="--")
ax_b.set_xlabel("BS_A"); ax_b.set_ylabel("Mean Cross-Model Lift")
ax_b.set_title("Panel B: Difficulty vs Lift\n(r=0.847, p<0.001)", fontweight="bold")

ax_c = fig.add_subplot(gs[2])
corr = {"Llama-3.1-8B":{"full":-0.0993,"clean":+0.2010},
        "Mistral-7B":{"full":-0.1466,"clean":+0.2010},
        "Qwen2.5-7B":{"full":-0.0968,"clean":+0.1838}}
xc = np.arange(3); wc = 0.35
ax_c.bar(xc-wc/2, [corr[m]["full"] for m in MODELS_3], wc, color="#E74C3C", alpha=0.8, label="All 30 events (raw)")
ax_c.bar(xc+wc/2, [corr[m]["clean"] for m in MODELS_3], wc, color="#27AE60", alpha=0.8, label="Clean events only")
ax_c.axhline(0, color="black", lw=1)
ax_c.set_xticks(xc); ax_c.set_xticklabels(["Llama-8B","Mistral-7B","Qwen-7B"],fontsize=9)
ax_c.set_ylabel("Mean Lift"); ax_c.set_title("Panel C: Contamination\nReversal of Aggregate Lift", fontweight="bold")
ax_c.legend(fontsize=8)
fig.suptitle("Temporal Data Leakage and Contamination Analysis (30 Events, 3 Complete Models | Qwen-14B*: pending)",
             fontweight="bold", fontsize=13)
save(fig, "fig9_contamination_analysis.png")

# ── FIG 7: Directional Accuracy Matrix ───────────────────────────────────
dir_mat = np.array([[73.3,71.7,60.0],[73.3,56.7,51.7],[73.3,73.3,71.7]])
fig, ax = plt.subplots(figsize=(9, 5))
cmap_d = LinearSegmentedColormap.from_list("dir",["#E74C3C","#F9E79F","#27AE60"],N=256)
im_d = ax.imshow(dir_mat, aspect="auto", cmap=cmap_d, vmin=40, vmax=80)
ax.set_xticks(range(3)); ax.set_xticklabels(["Cond A\nNo-Sim","Cond B\nWith-Sim","Cond C\nNull Ctrl"],fontsize=11)
ax.set_yticks(range(3)); ax.set_yticklabels(["Llama-3.1-8B","Mistral-7B","Qwen2.5-7B"],fontsize=11)
for i in range(3):
    for j in range(3):
        v = dir_mat[i,j]; ax.text(j, i, f"{v:.1f}%", ha="center", va="center", fontsize=12, fontweight="bold", color="white" if v<55 else "#222")
plt.colorbar(im_d, ax=ax, label="Directional Accuracy (%)", shrink=0.9)
ax.set_title("Directional Accuracy Heatmap (3 Complete Models x 3 Conditions)\nQwen2.5-14B*: not available locally", fontweight="bold")
save(fig, "fig7_directional_matrix.png")

print("\nAll done! Summary:")
for name in ["fig1_lift_heatmap.png","fig2_cross_model_brier.png","fig5_jsd_convergence.png",
             "fig7_directional_matrix.png","fig9_contamination_analysis.png",
             "fig_action_density_4models.png","fig_kappa_heatmap.png","compute_cost_analysis.png"]:
    sz = os.path.getsize(os.path.join(OUT_DIR, name))//1024 if os.path.exists(os.path.join(OUT_DIR, name)) else -1
    print(f"  {name:<45}  {sz} KB")
