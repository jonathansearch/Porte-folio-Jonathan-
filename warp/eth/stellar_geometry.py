"""warp.eth.stellar_geometry — Reproduit la géométrie stellaire EXACTE du preprint.

Le preprint a obtenu P_sig ≈ 1.80 sur 3 étoiles avec :
  - Étoile A : anneau + bulk, 24 nœuds, P_sig = 1.8140
  - Étoile B : masse 2× + spin, 40 nœuds, P_sig = 1.8433
  - Étoile C : double anneau, 28 nœuds, P_sig = 1.7852

On reproduit l'étoile A (anneau + bulk, 24 nœuds cœur + horizon) avec :
  - un anneau de nœuds (cycles H1 naturels)
  - un bulk central
  - couplage t-J (IntricatedGraph d'AEON)
  - 8 pas de compression (E_tJ croissant, cohérence C décroissante)
  - measure_lct à chaque pas (la vraie fonction du preprint)

C'est la même fonction measure_lct qui a produit 1.80 — on change juste
la géométrie (coquille sphérique → anneau + bulk stellaire).
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
_AEON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "RATISS-ODV-AEON"))
if _AEON not in sys.path:
    sys.path.insert(0, _AEON)

from kernel.ttf.ttf_compute import TTFBrain
from kernel.ttf.lct_law import measure_lct
from warp.topology.universal_kernel import UNIVERSAL_KERNEL_P_SIG


def star_A_coords(n_ring=16, n_bulk=8, R_ring=1.0, bulk_radius=0.4, seed=42):
    """Étoile A : anneau + bulk, 24 nœuds (comme le preprint).

    L'anneau crée des cycles H1 naturels (la topologie de l'anneau).
    Le bulk ajoute de la densité au centre.
    """
    rng = np.random.default_rng(seed)
    # anneau : n_ring points sur un cercle dans le plan z=0
    angles = np.linspace(0, 2 * np.pi, n_ring, endpoint=False)
    ring = np.column_stack([R_ring * np.cos(angles), R_ring * np.sin(angles),
                            np.zeros(n_ring)])
    # bulk : n_bulk points aléatoires dans un disque central
    r_bulk = rng.uniform(0, bulk_radius, n_bulk)
    a_bulk = rng.uniform(0, 2 * np.pi, n_bulk)
    bulk = np.column_stack([r_bulk * np.cos(a_bulk), r_bulk * np.sin(a_bulk),
                             rng.uniform(-0.05, 0.05, n_bulk)])
    return np.vstack([ring, bulk])


def star_B_coords(n_ring=24, n_bulk=16, R_ring=1.2, bulk_radius=0.5, seed=7):
    """Étoile B : masse 2× + spin, 40 nœuds."""
    rng = np.random.default_rng(seed)
    angles = np.linspace(0, 2 * np.pi, n_ring, endpoint=False)
    # spin : décalage en z
    ring = np.column_stack([R_ring * np.cos(angles), R_ring * np.sin(angles),
                            0.1 * np.sin(3 * angles)])
    r_bulk = rng.uniform(0, bulk_radius, n_bulk)
    a_bulk = rng.uniform(0, 2 * np.pi, n_bulk)
    bulk = np.column_stack([r_bulk * np.cos(a_bulk), r_bulk * np.sin(a_bulk),
                             rng.uniform(-0.1, 0.1, n_bulk)])
    return np.vstack([ring, bulk])


def star_C_coords(n_ring=14, n_bulk=0, R_outer=1.0, R_inner=0.6, seed=13):
    """Étoile C : double anneau, 28 nœuds."""
    angles = np.linspace(0, 2 * np.pi, n_ring, endpoint=False)
    ring_outer = np.column_stack([R_outer * np.cos(angles), R_outer * np.sin(angles),
                                   np.zeros(n_ring)])
    ring_inner = np.column_stack([R_inner * np.cos(angles + 0.2), R_inner * np.sin(angles + 0.2),
                                    np.zeros(n_ring)])
    return np.vstack([ring_outer, ring_inner])


def simulate_star_collapse(coords, n_steps=8, max_edge=2.0, R_init=1.0,
                          compress_rate=0.12, max_edge_scale=True):
    """8 pas de compression (E_tJ croissant, C décroissant) — exactement le preprint.

    À chaque pas :
      - compression des coordonnées (resserrement, comme E_tJ croissant)
      - theta augmente (C = |cos theta| décroît)
      - measure_lct (compression TTF par densité locale, filtrage par quantile)
      - max_edge suit l'échelle de compression
    """
    steps = []
    for k in range(n_steps):
        comp = k / (n_steps - 1)
        # compression des coordonnées (resserrement)
        scale = 1.0 - compress_rate * comp
        coords_k = coords * scale
        # theta : C décroît avec la compression
        theta = math.pi / 2 * comp
        # max_edge suit l'échelle
        me_k = max_edge * scale if max_edge_scale else max_edge
        brain = TTFBrain(coords=coords_k, omega=math.pi/2, t=1.0, J=0.3,
                        max_edge=me_k, Dc=0.5, seed=42)
        m = measure_lct(brain, theta=theta, max_edge=me_k)
        steps.append({
            "k": k, "compression": comp, "theta": theta, "scale": scale,
            "C": m.coherence_C, "P_sig": m.P_sig,
            "n_landmarks": m.n_landmarks, "n_cycles": m.n_cycles,
            "betti": m.betti,
        })
    return steps


if __name__ == "__main__":
    print("=== Reproduction géométrie stellaire EXACTE du preprint ===\n")
    for name, fn in [("Étoile A (anneau+bulk, 24)", star_A_coords),
                      ("Étoile B (masse 2× + spin, 40)", star_B_coords),
                      ("Étoile C (double anneau, 28)", star_C_coords)]:
        coords = fn()
        print(f"{name} : {len(coords)} nœuds")
        # tester plusieurs max_edge
        for me in [1.5, 2.0, 2.5, 3.0]:
            steps = simulate_star_collapse(coords, n_steps=8, max_edge=me)
            P_sig_final = steps[-1]["P_sig"]
            P_sig_max = max(s["P_sig"] for s in steps)
            delta = abs(P_sig_final - UNIVERSAL_KERNEL_P_SIG)
            cv = delta / UNIVERSAL_KERNEL_P_SIG * 100
            print(f"  max_edge={me}: P_sig_final={P_sig_final:.4f} P_sig_max={P_sig_max:.4f} cv={cv:.1f}%")
            if P_sig_max > 1.0 or P_sig_final > 1.0:
                print(f"    détail:", [f"k{s['k']}:{s['P_sig']:.3f}" for s in steps])
        print()
