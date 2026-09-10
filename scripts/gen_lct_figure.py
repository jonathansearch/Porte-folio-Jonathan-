import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

C_DEEP="#0b1d3a"; C_CYAN="#22d3ee"; C_AMBER="#f59e0b"; C_RED="#ef4444"
C_GREEN="#22c55e"; C_VIOLET="#8b5cf6"; C_BG="#0a0f1f"

fig, ax = plt.subplots(figsize=(11, 6.5), facecolor=C_BG)
ax.set_facecolor(C_BG); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')

ax.text(0.5, 0.95, "Loi de Cohérence Topologique (LCT)", ha="center",
        color="white", fontsize=19, fontweight="bold")
ax.text(0.5, 0.88, "On certifie le MESSAGE (la forme), pas le COURANT (l'energie)",
        ha="center", color=C_CYAN, fontsize=12.5, style="italic")

ax.add_patch(FancyBboxPatch((0.04, 0.30), 0.40, 0.42, boxstyle="round,pad=0.02",
             fc=C_DEEP, ec=C_CYAN, lw=2.5))
ax.text(0.24, 0.66, "MESSAGE", ha="center", color=C_CYAN, fontsize=15, fontweight="bold")
ax.text(0.24, 0.59, "la forme topologique", ha="center", color="#dbe6f5", fontsize=10.5)
ax.text(0.24, 0.50, r"$R = P_{sig}$", ha="center", color=C_GREEN, fontsize=20)
ax.text(0.24, 0.42, r"$S_{vN}$", ha="center", color=C_GREEN, fontsize=13)
ax.text(0.24, 0.33, "INVARIANT", ha="center", color=C_GREEN, fontsize=11, fontweight="bold")
ax.text(0.24, 0.27, "ne depend pas de l'energie", ha="center", color="#9fb0c9", fontsize=8.5)

ax.add_patch(FancyBboxPatch((0.56, 0.30), 0.40, 0.42, boxstyle="round,pad=0.02",
             fc=C_DEEP, ec=C_AMBER, lw=2.5))
ax.text(0.76, 0.66, "COURANT", ha="center", color=C_AMBER, fontsize=15, fontweight="bold")
ax.text(0.76, 0.59, "l'energie qui porte le message", ha="center", color="#dbe6f5", fontsize=10.5)
ax.text(0.76, 0.50, r"$t, J, \rho$", ha="center", color=C_RED, fontsize=20)
ax.text(0.76, 0.42, r"$\nabla P_{sig}$  ($\Lambda_{LCT}$)", ha="center", color=C_VIOLET, fontsize=12)
ax.text(0.76, 0.33, "VARIABLE", ha="center", color=C_RED, fontsize=11, fontweight="bold")
ax.text(0.76, 0.27, "le courant change, pas le message", ha="center", color="#9fb0c9", fontsize=8.5)

ax.annotate("", xy=(0.56, 0.51), xytext=(0.44, 0.51),
            arrowprops=dict(arrowstyle="<->", lw=3, color=C_VIOLET))
ax.text(0.50, 0.56, "certifie", ha="center", color=C_VIOLET, fontsize=10, fontweight="bold")
ax.text(0.50, 0.46, "ne certifie pas", ha="center", color=C_VIOLET, fontsize=8.5, style="italic")

ax.add_patch(FancyBboxPatch((0.04, 0.05), 0.92, 0.14, boxstyle="round,pad=0.015",
             fc=C_DEEP, ec="#1e2c4a", lw=1.5))
xs = np.linspace(0.08, 0.40, 40)
C = np.linspace(0,1,40)
Psig = 0.06 + 0.10*C**1.3
ax.plot(xs, 0.075 + Psig*0.45, color=C_CYAN, lw=2)
ax.text(0.24, 0.165, "C up (intrication) => P_sig up", ha="center", color=C_CYAN, fontsize=9)
ax.annotate("", xy=(0.92, 0.12), xytext=(0.44, 0.12),
            arrowprops=dict(arrowstyle="->", lw=2, color=C_GREEN))
ax.text(0.68, 0.155, "applique au warp & trous noirs ($\\Lambda_{LCT}$)", ha="center", color=C_GREEN, fontsize=9)
ax.text(0.68, 0.085, "noyau universel $P_{sig}\\approx 1.80$", ha="center", color="#9fb0c9", fontsize=8)

ax.text(0.50, 0.005, "Loi figee - falsifiee (2 formulations sur 3 ont echoue, seule R=P_sig survit, Spearman +0.93)",
        ha="center", color="#7d8aa3", fontsize=8.5, style="italic")

fig.tight_layout()
fig.savefig("assets/lct_message_vs_courant.png", dpi=140, facecolor=C_BG)
print("ok assets/lct_message_vs_courant.png")
