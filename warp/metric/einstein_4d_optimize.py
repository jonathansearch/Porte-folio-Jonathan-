"""warp.metric.einstein_4d_optimize — Optimise le profil P(x) pour maximiser la compensation.

Problème de l'ansatz canonique (attractor) : P gaussien → ∇P = 0 au mur
r=R, pile là où l'exotic matter (df/dr)² est max. MAUVAIS alignement.

Solution : P(r) = P0·tanh((r-R)/σ). Alors dP/dr = (P0/σ)·sech²((r-R)/σ) → peak
à r=R, aligné avec le mur. La compensation Λ_00 = ½κ(1-v²f²)(∇P)² est alors
maximisée exactement là où l'exotic matter est maximale.

On optimise (κ, σ, P0) par differential_evolution pour maximiser la réduction
du creux négatif T_00.
"""
import math
import sys
import os

import numpy as np
from scipy.optimize import differential_evolution

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def exotic_and_compensation(params, n_samples=2000, R=1.0, eps=0.2, v=1.0, G=1.0, seed=42,
                           return_details=False):
    """Calcule T_std_00 et T_eff_00 (ansatz canonique) pour un profil P tanh.

    params = [kappa, sigma, P0]
    """
    kappa, sigma, P0 = params
    sigma = max(abs(sigma), 1e-3)
    rng = np.random.default_rng(seed)
    pts = rng.uniform(-2*R, 2*R, size=(n_samples, 3))
    T_std = []
    T_eff = []
    for px, py, pz in pts:
        r = math.sqrt(px*px + py*py + pz*pz) + 1e-9
        # profil f du mur
        f = 0.5 * (math.tanh((r-R)/eps) + 1)
        df_dr = 0.5 * (1/eps) * (1/math.cosh((r-R)/eps)**2)
        yz = py*py + pz*pz
        # exotic matter standard
        rho_std = -(v**2 / (8*math.pi*G)) * (df_dr**2) * yz / (r**2)
        # profil P tanh
        dP_dr = (P0 / sigma) * (1/math.cosh((r-R)/sigma)**2)
        # ansatz canonique : Λ_00 = ½κ(1-v²f²)(∇P)²
        Lambda_00 = 0.5 * kappa * (1 - v**2 * f**2) * (dP_dr**2)
        T_eff_00 = rho_std + Lambda_00 / (8*math.pi*G)
        T_std.append(rho_std)
        T_eff.append(T_eff_00)
    T_std = np.array(T_std)
    T_eff = np.array(T_eff)
    # objectif : réduire le creux négatif (le min). On veut T_eff.min le moins négatif possible.
    # Mais si κ trop grand, T_eff devient positif partout (sur-compensation) — on veut
    # que le min soit le plus proche de 0 possible, idéalement 0.
    min_std = np.min(T_std)
    min_eff = np.min(T_eff)
    # réduction du creux (positif = amélioration)
    reduction = (min_eff - min_std) / abs(min_std) * 100  # positif si min_eff > min_std
    if return_details:
        return {"T_std_min": float(min_std), "T_eff_min": float(min_eff),
                "reduction_pct": float(reduction), "kappa": float(kappa),
                "sigma": float(sigma), "P0": float(P0)}
    # objectif à minimiser : -réduction (on veut maximiser la réduction) + pénalité sur-compensation
    # pénalité : si T_eff min > 0 (sur-compensation), c'est moins idéal que T_eff min ≈ 0
    over = max(0.0, min_eff)  # sur-compensation positive
    return -(reduction) + 1000 * over  # minimiser


if __name__ == "__main__":
    print("=== Optimisation du profil P (tanh) pour maximiser la compensation ===")
    print("P(r) = P0·tanh((r-R)/σ), Λ_00 = ½κ(1-v²f²)(dP/dr)²\n")

    bounds = [(0.1, 200.0), (0.05, 1.0), (0.5, 5.0)]  # [kappa, sigma, P0]
    print("Optimisation par differential_evolution (peut prendre 1-2 min)...")
    res = differential_evolution(exotic_and_compensation, bounds, maxiter=25, popsize=8,
                                 seed=42, tol=1e-3, mutation=(0.5, 1.0), recombination=0.7,
                                 polish=False)
    best = res.x
    details = exotic_and_compensation(best, return_details=True)
    print(f"\nMeilleurs paramètres : κ={details['kappa']:.2f}, σ={details['sigma']:.3f}, P0={details['P0']:.2f}")
    print(f"T_00 min standard : {details['T_std_min']:.4f} (exotic matter)")
    print(f"T_00 min effectif : {details['T_eff_min']:.4f}")
    print(f"Réduction du creux négatif : {details['reduction_pct']:.1f}%")
    if details["reduction_pct"] > 90:
        print("\n🎯 ÉLIMINATION quasi-totale de l'exotic matter !")
    elif details["reduction_pct"] > 50:
        print("\n✅ Compensation forte (>50%) !")
    elif details["reduction_pct"] > 20:
        print("\n✅ Compensation significative (>20%).")
    else:
        print(f"\nRéduction : {details['reduction_pct']:.1f}%.")
