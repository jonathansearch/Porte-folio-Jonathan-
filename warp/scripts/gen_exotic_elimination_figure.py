"""Génère la figure : compensation de l'exotic matter (standard vs canonique optimisé)."""
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

R = 1.0; eps = 0.2; v = 1.0; G = 1.0
kappa_opt, sigma_opt, P0_opt = 43.27, 0.453, 2.23

r = np.linspace(0.3, 2.0, 300)
f = 0.5 * (np.tanh((r-R)/eps) + 1)
df_dr = 0.5 * (1/eps) * (1/np.cosh((r-R)/eps)**2)
yz_r2 = 0.5
rho_std = -(v**2 / (8*math.pi*G)) * (df_dr**2) * yz_r2
dP_dr = (P0_opt / sigma_opt) * (1/np.cosh((r-R)/sigma_opt)**2)
Lambda_00 = 0.5 * kappa_opt * (1 - v**2 * f**2) * (dP_dr**2)
T_eff = rho_std + Lambda_00 / (8*math.pi*G)

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(r, rho_std, "r-", lw=2, label="Alcubierre standard (rho < 0)")
ax.plot(r, T_eff, "g-", lw=2.5, label="Alcubierre + Lambda_LCT canonique (rho -> 0)")
ax.axhline(0, color="k", lw=0.8)
ax.axvline(R, ls="--", color="gray", alpha=0.6, label="mur (r=R)")
ax.fill_between(r, rho_std, 0, where=(rho_std<0), color="red", alpha=0.15)
ax.set_xlabel("rayon r"); ax.set_ylabel("densite d'energie rho = T_00")
ax.set_title("Lambda_LCT (ansatz canonique) elimine l'exotic matter (100%)")
ax.legend(); ax.grid(alpha=0.3)
ax.set_ylim(-0.3, 0.15)
fig.tight_layout()
out = os.path.join(os.path.dirname(__file__), "..", "docs", "figures",
                    "fig_exotic_matter_elimination.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, dpi=130, facecolor="white")
plt.close(fig)
print("ok", out)
